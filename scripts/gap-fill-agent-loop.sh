#!/usr/bin/env bash
# Time-bounded Claude CLI loop to ideate gap-filling LLVM IR tests.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

MAX_WALL_SEC="${MAX_WALL_SEC:-7200}"
MAX_ROUNDS="${MAX_ROUNDS:-30}"
MAX_BUDGET_USD="${MAX_BUDGET_USD:-1.50}"
MAX_ATTEMPTS_PER_GAP="${MAX_ATTEMPTS_PER_GAP:-5}"
SLEEP_SEC="${SLEEP_SEC:-0}"

# Claude CLI expects Anthropic-style model ids (e.g. claude-sonnet-4-6, sonnet).
# AMD proxy env names like Claude-Sonnet-4.6 map to retired "Sonnet 4" and warn.
normalize_claude_model() {
    local raw="${1:-}"
    case "${raw,,}" in
        "" | sonnet | claude-sonnet-4-6) printf '%s\n' "claude-sonnet-4-6" ;;
        claude-sonnet-4.6) printf '%s\n' "claude-sonnet-4-6" ;;
        opus | claude-opus-4-6) printf '%s\n' "claude-opus-4-6" ;;
        claude-opus-4.8) printf '%s\n' "claude-opus-4-6" ;;
        haiku | claude-haiku-4-5) printf '%s\n' "claude-haiku-4-5" ;;
        claude-haiku-4.5) printf '%s\n' "claude-haiku-4-5" ;;
        *) printf '%s\n' "$raw" ;;
    esac
}

CLAUDE_MODEL="$(normalize_claude_model "${CLAUDE_MODEL:-${ANTHROPIC_MODEL:-claude-sonnet-4-6}}")"

AGENT_DIR="${REPO_ROOT}/data/gap-fill/agent"
QUEUE_CSV="${AGENT_DIR}/gap-queue.csv"
JOURNAL="${AGENT_DIR}/journal.jsonl"
WINS_DIR="${AGENT_DIR}/wins"
CTX_ROOT="${AGENT_DIR}/context"
PROMPT_FILE="${REPO_ROOT}/prompts/gap-fill-agent.md"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Environment (defaults shown):
  MAX_WALL_SEC=${MAX_WALL_SEC}       Total wall-clock budget
  MAX_ROUNDS=${MAX_ROUNDS}             Max Claude -p invocations
  MAX_BUDGET_USD=${MAX_BUDGET_USD}     Per-round API budget for claude
  MAX_ATTEMPTS_PER_GAP=${MAX_ATTEMPTS_PER_GAP}
  SLEEP_SEC=${SLEEP_SEC}
  CLAUDE_MODEL=${CLAUDE_MODEL}   (also respects ANTHROPIC_MODEL)

Examples:
  MAX_WALL_SEC=7200 MAX_ROUNDS=20 ./scripts/gap-fill-agent-loop.sh
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if ! command -v claude >/dev/null 2>&1; then
    echo "error: claude CLI not found in PATH" >&2
    exit 2
fi

mkdir -p "$AGENT_DIR" "$WINS_DIR" "$CTX_ROOT"
cd "$REPO_ROOT"

if [[ ! -f "$QUEUE_CSV" ]]; then
    echo "=== generating gap queue ==="
    python3 "${SCRIPT_DIR}/gap_fill_agent.py" generate-queue
fi

update_gap() {
    local pr="$1"
    local line="$2"
    local status="$3"
    local increment="${4:-0}"
    local -a args=(update-queue --pr "$pr" --line "$line" --status "$status")
    if [[ "$increment" -eq 1 ]]; then
        args+=(--increment-attempts)
    fi
    python3 "${SCRIPT_DIR}/gap_fill_agent.py" "${args[@]}"
}

start_ts=$(date +%s)
round=0
filled=0
misses=0

append_journal() {
    local result="$1"
    local pr="$2"
    local line="$3"
    local ctx="$4"
    local detail="${5:-}"
    printf '{"ts":"%s","round":%d,"pr":"%s","line":%s,"result":"%s","ctx":"%s","detail":"%s"}\n' \
        "$(date -Iseconds)" "$round" "$pr" "$line" "$result" "$ctx" "$detail" >>"$JOURNAL"
}

run_loop() {
    while [[ "$round" -lt "$MAX_ROUNDS" ]]; do
        now=$(date +%s)
        elapsed=$((now - start_ts))
        if [[ "$elapsed" -ge "$MAX_WALL_SEC" ]]; then
            echo "wall-clock budget reached (${elapsed}s >= ${MAX_WALL_SEC}s)"
            break
        fi

        next_line="$(python3 "${SCRIPT_DIR}/gap_fill_agent.py" pick-next \
            --queue "$QUEUE_CSV" --max-attempts "$MAX_ATTEMPTS_PER_GAP" || true)"
        if [[ -z "$next_line" ]]; then
            echo "no open gaps remaining (or all exceeded max attempts)"
            break
        fi

        IFS=$'\t' read -r pr backend file line attempts <<<"$next_line"
        round=$((round + 1))
        ctx="${CTX_ROOT}/${pr}-${line}"
        rm -rf "$ctx"
        mkdir -p "$ctx"

        echo ""
        echo "=== round ${round}/${MAX_ROUNDS} pr=${pr} line=${line} attempts=${attempts} elapsed=${elapsed}s ==="
        echo "[$(date -Iseconds)] preparing context..."

        "${SCRIPT_DIR}/prepare-gap-context.sh" --pr "$pr" --line "$line" --out "$ctx"

        prior=""
        if [[ -f "$JOURNAL" ]]; then
            prior="$(grep "\"pr\":\"${pr}\"" "$JOURNAL" | grep "\"line\":${line}" | tail -3 || true)"
        fi

        prompt_body="$(cat "${ctx}/prompt.txt")"
        if [[ -n "$prior" ]]; then
            prompt_body="${prompt_body}

Prior attempts for this gap (avoid repeating):
${prior}"
        fi

        echo "[$(date -Iseconds)] calling claude (model=${CLAUDE_MODEL}, budget=\$${MAX_BUDGET_USD}) — no output until this round finishes; watch ${ctx}/ or tail -f ${JOURNAL} in another pane"

        claude_args=(
            -p
            --model "$CLAUDE_MODEL"
            --max-budget-usd "$MAX_BUDGET_USD"
            --allowed-tools "Bash,Read,Write,Edit,Glob,Grep"
            --add-dir "$REPO_ROOT"
            --add-dir "$ctx"
            --append-system-prompt-file "$PROMPT_FILE"
        )
        if [[ "${CLAUDE_VERBOSE:-0}" == 1 ]]; then
            claude_args+=(--verbose)
        fi

        if ! claude "${claude_args[@]}" "$prompt_body"; then
            echo "warning: claude exited non-zero for pr=${pr} line=${line}" >&2
            update_gap "$pr" "$line" "open" 1
            append_journal "claude_error" "$pr" "$line" "$ctx" "claude failed"
            misses=$((misses + 1))
            [[ "$SLEEP_SEC" -gt 0 ]] && sleep "$SLEEP_SEC"
            continue
        fi

        echo "[$(date -Iseconds)] claude finished; checking outputs..."

        if [[ ! -f "${ctx}/candidate.ll" || ! -f "${ctx}/llc_flags.txt" ]]; then
            echo "MISS: Claude did not write candidate.ll and/or llc_flags.txt" >&2
            update_gap "$pr" "$line" "open" 1
            append_journal "missing_outputs" "$pr" "$line" "$ctx" ""
            misses=$((misses + 1))
            [[ "$SLEEP_SEC" -gt 0 ]] && sleep "$SLEEP_SEC"
            continue
        fi

        llc_map="$(python3 -c "import json; print(json.load(open('${ctx}/gap.json'))['llc_map_csv'])")"
        echo "[$(date -Iseconds)] running sancov verify (docker pr=${pr})..."
        if "${SCRIPT_DIR}/verify-gap-candidate.sh" \
            --pr-id "$pr" \
            --file "$file" \
            --line "$line" \
            --llc-map-csv "$llc_map" \
            --test "${ctx}/candidate.ll" \
            --llc-flags "$(tr -d '\n' < "${ctx}/llc_flags.txt")"; then
            win_dir="${WINS_DIR}/${pr}-${line}"
            rm -rf "$win_dir"
            mkdir -p "$win_dir"
            cp "${ctx}/candidate.ll" "${ctx}/llc_flags.txt" "$win_dir/"
            [[ -f "${ctx}/idea.md" ]] && cp "${ctx}/idea.md" "$win_dir/"
            cp "${ctx}/gap.json" "$win_dir/"
            update_gap "$pr" "$line" "filled" 0
            append_journal "fill" "$pr" "$line" "$ctx" "saved to ${win_dir}"
            filled=$((filled + 1))
            echo "FILLED pr=${pr} line=${line} -> ${win_dir}"
        else
            update_gap "$pr" "$line" "open" 1
            append_journal "miss" "$pr" "$line" "$ctx" ""
            misses=$((misses + 1))
            attempts=$((attempts + 1))
            if [[ "$attempts" -ge "$MAX_ATTEMPTS_PER_GAP" ]]; then
                update_gap "$pr" "$line" "blocked" 0
                echo "blocked pr=${pr} line=${line} after ${MAX_ATTEMPTS_PER_GAP} attempts"
            fi
        fi

        [[ "$SLEEP_SEC" -gt 0 ]] && sleep "$SLEEP_SEC"
    done
}

run_loop

echo ""
echo "=== summary ==="
echo "rounds=${round} filled=${filled} misses=${misses} journal=${JOURNAL}"
echo "wins under ${WINS_DIR}/"
