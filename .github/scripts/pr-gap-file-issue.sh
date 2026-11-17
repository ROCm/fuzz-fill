#!/usr/bin/env bash
# File (or dry-run) a fuzz-fill tracking issue / comment from a staged PR
# gap-finding results artifact. One open issue per PR; later runs comment.
# Always posts, including zero uncovered lines. Links Actions artifacts.
#
# Usage:
#   pr-gap-file-issue.sh [--dry-run] --actor LOGIN --repo OWNER/NAME \
#     --artifact-dir DIR [--run-id ID] [--server-url URL]
#
# Env (optional; GITHUB_* set in Actions):
#   GITHUB_REPOSITORY, GITHUB_RUN_ID, GITHUB_SERVER_URL, GH_TOKEN

set -euo pipefail

DRY_RUN=0
ACTOR=""
REPO="${GITHUB_REPOSITORY:-}"
ARTIFACT_DIR="${ARTIFACT_DIR:-}"
RUN_ID="${GITHUB_RUN_ID:-}"
SERVER_URL="${GITHUB_SERVER_URL:-https://github.com}"
ISSUES_PY="$(dirname "${BASH_SOURCE[0]}")/pr_gap_github.py"
CONTAINER_BUILD_PREFIX="/work/pr-llvm/"
BODY_SOFT_LIMIT=60000
MAX_ATTEMPTS=3

usage() {
    cat <<EOF
Usage: $(basename "$0") [--dry-run] --actor LOGIN --repo OWNER/NAME \\
  --artifact-dir DIR [--run-id ID] [--server-url URL]
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --actor) ACTOR="$2"; shift 2 ;;
        --repo) REPO="$2"; shift 2 ;;
        --artifact-dir) ARTIFACT_DIR="$2"; shift 2 ;;
        --run-id) RUN_ID="$2"; shift 2 ;;
        --server-url) SERVER_URL="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "error: unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ -z "$ACTOR" || -z "$REPO" || -z "$ARTIFACT_DIR" ]]; then
    echo "error: --actor, --repo, and --artifact-dir are required" >&2
    usage >&2
    exit 2
fi
if [[ -z "$RUN_ID" && "$DRY_RUN" -eq 0 ]]; then
    echo "error: --run-id or GITHUB_RUN_ID is required (unless --dry-run)" >&2
    exit 2
fi
RUN_ID="${RUN_ID:-0}"

README="${ARTIFACT_DIR}/README-finding.txt"
CSV="${ARTIFACT_DIR}/out/commit_lines_report/target_lines_uncovered_pruned.csv"

if [[ ! -f "$README" ]]; then
    echo "error: missing ${README}" >&2
    exit 1
fi
if [[ ! -f "$CSV" ]]; then
    echo "error: missing ${CSV}" >&2
    exit 1
fi

readme_get() {
    local key="$1"
    awk -F': ' -v k="$key" '$1 == k { v=$2; for (i=3;i<=NF;i++) v=v FS $i; found=v }
         END { if (found != "") print found }' "$README"
}

pr_id="$(readme_get pr_id)"
github_repo="$(readme_get github_repo)"
pr_head="$(readme_get pr_head)"
generate_html="$(readme_get generate_html)"
gap_scope_action="$(readme_get gap_scope_action)"

if [[ -z "$pr_id" || -z "$github_repo" || -z "$pr_head" ]]; then
    echo "error: README-finding.txt missing pr_id, github_repo, or pr_head" >&2
    exit 1
fi

# Label and key lines come from pr_gap_github.py, which also matches them.
mapfile -t issue_keys < <(
    python3 "$ISSUES_PY" keys --llvm-repo "$github_repo" --pr "$pr_id" \
        --run-id "$RUN_ID" --head "$pr_head"
)
if [[ "${#issue_keys[@]}" -ne 5 ]]; then
    echo "error: ${ISSUES_PY} keys failed" >&2
    exit 1
fi
LABEL="${issue_keys[0]}"
tracking_key="${issue_keys[1]}"
workflow_run_key="${issue_keys[2]}"
analyzed_head_line="${issue_keys[3]}"
analyzed_head_key="${issue_keys[4]}"
issue_title="PR Analysis: ${github_repo} pull ${pr_id}"

mapfile -t entries < <(
    awk -F',' -v prefix="$CONTAINER_BUILD_PREFIX" '
        NR == 1 { next }
        NF < 2 { next }
        {
            file = $1
            line = $2
            if (index(file, prefix) == 1)
                file = substr(file, length(prefix) + 1)
            key = file SUBSEP line
            if (!(key in seen)) {
                seen[key] = 1
                print file "\t" line
            }
        }
    ' "$CSV" | LC_ALL=C sort
)
count="${#entries[@]}"

gh_retry() {
    local attempt=1 delay=2
    local out status
    while true; do
        status=0
        out="$("$@" 2>&1)" || status=$?
        if [[ "$status" -eq 0 ]]; then
            printf '%s' "$out"
            return 0
        fi
        if [[ "$attempt" -ge "$MAX_ATTEMPTS" ]]; then
            echo "$out" >&2
            return "$status"
        fi
        # Retry transient failures only (5xx / rate limit / network).
        if printf '%s' "$out" | grep -Eqi 'HTTP 5[0-9][0-9]|rate.?limit|timed out|connection|EOF|temporary'; then
            echo "warning: attempt ${attempt}/${MAX_ATTEMPTS} failed; retrying in ${delay}s" >&2
            echo "$out" >&2
            sleep "$delay"
            attempt=$((attempt + 1))
            delay=$((delay * 2))
            continue
        fi
        echo "$out" >&2
        return "$status"
    done
}

ensure_label() {
    gh_retry gh label create "$LABEL" --repo "$REPO" \
        --description "Automated PR gap analysis report from pr-gap-analysis.yml" \
        --color "0E8A16" || true
}

find_open_issue() {
    python3 "$ISSUES_PY" find-open --repo "$REPO" \
        --llvm-repo "$github_repo" --pr "$pr_id"
}

# Prints the issue number when this run already posted there, else nothing.
posted_for_run() {
    python3 "$ISSUES_PY" mentions --repo "$REPO" \
        --issue "$1" --text "$workflow_run_key"
}

resolve_artifact_id() {
    local name="$1" ids
    ids="$(
        gh_retry gh api --paginate \
            "repos/${REPO}/actions/runs/${RUN_ID}/artifacts" \
            --jq ".artifacts[] | select(.name == \"${name}\" and .expired == false) | .id"
    )"
    # One id. Avoid piping to head: the producer can die with SIGPIPE.
    printf '%s' "${ids%%$'\n'*}"
}

fetch_pr_title() {
    local title
    if title="$(gh api "repos/${github_repo}/pulls/${pr_id}" --jq '.title // empty' 2>/dev/null)"; then
        # Inline code: neutralize backticks so the fence stays intact.
        printf '%s' "$title" | tr '`' ' '
    fi
}

build_body() {
    local body pr_title results_name html_name results_id html_id results_url html_url
    local i file line link truncated=0 candidate

    pr_title="$(fetch_pr_title || true)"
    results_name="gap-finding-results-pr${pr_id}-${RUN_ID}"
    html_name="html-coverage-pr${pr_id}-${RUN_ID}"

    body=""
    # Scheduled / bot-dispatched runs use github-actions[bot]; leave the
    # leading @mention off so the issue does not tag the Actions bot.
    if [[ "$ACTOR" != "github-actions[bot]" ]]; then
        body="@${ACTOR}"$'\n\n'
    fi
    body+="[Pull request](https://redirect.github.com/${github_repo}/pull/${pr_id})"$'\n'
    if [[ -n "$pr_title" ]]; then
        body+="\`${pr_title}\`"$'\n'
    fi
    body+=$'\n'
    body+="${analyzed_head_line}"$'\n'
    body+=$'\n'

    if [[ "$DRY_RUN" -eq 1 ]]; then
        results_url="${SERVER_URL}/${REPO}/actions/runs/${RUN_ID}/artifacts/<results-id>"
        if [[ "${generate_html}" == "true" && "${gap_scope_action}" == "run" ]]; then
            html_url="${SERVER_URL}/${REPO}/actions/runs/${RUN_ID}/artifacts/<html-id>"
        fi
    else
        results_id="$(resolve_artifact_id "$results_name")"
        if [[ -z "$results_id" ]]; then
            echo "error: results artifact ${results_name} not found for run ${RUN_ID}" >&2
            exit 1
        fi
        results_url="${SERVER_URL}/${REPO}/actions/runs/${RUN_ID}/artifacts/${results_id}"
        html_id="$(resolve_artifact_id "$html_name")"
        if [[ -n "$html_id" ]]; then
            html_url="${SERVER_URL}/${REPO}/actions/runs/${RUN_ID}/artifacts/${html_id}"
        fi
    fi

    body+="Artifacts expire after 7 days:"$'\n'
    body+=$'\n'
    body+="- [Results](${results_url}) (\`${results_name}\`)"$'\n'
    if [[ -n "${html_url:-}" ]]; then
        body+="- [HTML report](${html_url}) (\`${html_name}\`)"$'\n'
    else
        if [[ "${generate_html}" == "true" && "${gap_scope_action}" == "run" && "$DRY_RUN" -eq 0 ]]; then
            body+="- HTML report was expected but not found among this run's artifacts."$'\n'
        else
            body+="- HTML report was not produced for this run."$'\n'
        fi
    fi
    body+=$'\n'

    body+="Uncovered lines: ${count}"$'\n'
    body+=$'\n'
    if [[ "$count" -eq 0 ]]; then
        body+="None"$'\n'
    else
        i=0
        for entry in "${entries[@]}"; do
            file="${entry%%$'\t'*}"
            line="${entry#*$'\t'}"
            link="https://github.com/${github_repo}/blob/${pr_head}/${file}#L${line}"
            i=$((i + 1))
            candidate="${body}${i}. ${link}"$'\n'
            # Reserve room for the banner + tracking keys (~4k).
            if [[ ${#candidate} -gt $((BODY_SOFT_LIMIT - 4000)) ]]; then
                truncated=1
                break
            fi
            body="$candidate"
        done
        if [[ "$truncated" -eq 1 ]]; then
            body+=$'\n'
            body+="*(List truncated at ${i} of ${count} lines. Full CSV is in the Results artifact as \`out/commit_lines_report/target_lines_uncovered_pruned.csv\`.)*"$'\n'
        fi
    fi
    body+=$'\n'

    body+="> [!IMPORTANT]"$'\n'
    body+="> We encourage you to review and assess whether these findings are worth sharing. Keep a human in the loop before posting anything to LLVM, and follow the LLVM contribution guidelines."$'\n'
    body+=">"$'\n'
    body+="> fuzz-fill finds coverage gaps in the analyzed change using SanitizerCoverage instrumentation and it may not report every uncovered line. Failures in the LLVM test suite could potentially also leave the coverage analysis incomplete."$'\n'
    body+=">"$'\n'
    body+="> Some reported gaps are covered only by a build setting we may leave off, such as an extra runtime. That is uncommon for typical PRs: we usually build all backends (and Clang when necessary) and run the full test suite. Broader build support is possible — tell us if that would help."$'\n'
    body+=$'\n'

    body+="${tracking_key}"$'\n'
    body+="${workflow_run_key}"$'\n'
    body+="${analyzed_head_key}"$'\n'
    printf '%s' "$body"
}

body="$(build_body)"

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "=== dry-run ==="
    echo "repo: ${REPO}"
    echo "actor: ${ACTOR}"
    echo "title: ${issue_title}"
    echo "label: ${LABEL}"
    echo "${tracking_key}"
    echo "${workflow_run_key}"
    echo "=== body ==="
    printf '%s\n' "$body"
    exit 0
fi

ensure_label

existing="$(find_open_issue)"
if [[ -n "${existing:-}" ]]; then
    posted="$(posted_for_run "$existing")"
    if [[ -n "$posted" ]]; then
        echo "already posted for ${workflow_run_key} on issue #${existing}; skipping"
        echo "${SERVER_URL}/${REPO}/issues/${existing}"
        exit 0
    fi
    gh_retry gh issue comment "$existing" --repo "$REPO" --body "$body" >/dev/null
    echo "commented on ${SERVER_URL}/${REPO}/issues/${existing}"
    echo "${SERVER_URL}/${REPO}/issues/${existing}"
    exit 0
fi

url="$(
    gh_retry gh issue create --repo "$REPO" --title "$issue_title" \
        --label "$LABEL" --body "$body"
)"
echo "filed ${url}"
printf '%s\n' "$url"
