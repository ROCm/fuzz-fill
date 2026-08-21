#!/usr/bin/env bash
# Build a per-gap context directory for the Claude gap-fill agent.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

pr=""
line=""
out=""
image=""

usage() {
    cat <<EOF
Usage: $(basename "$0") --pr <n> --line <n> --out <dir> [--image <docker-ref>]

Writes gap.json, snippets, candidate_test_settings.csv, verify.sh, prompt.txt
under --out (default queue: data/gap-fill/agent/gap-queue.csv).
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr)
            pr="$2"
            shift 2
            ;;
        --line)
            line="$2"
            shift 2
            ;;
        --out)
            out="$2"
            shift 2
            ;;
        --image)
            image="$2"
            shift 2
            ;;
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

if [[ -z "$pr" || -z "$line" || -z "$out" ]]; then
    echo "error: --pr, --line, and --out are required" >&2
    usage >&2
    exit 1
fi

queue="${REPO_ROOT}/data/gap-fill/agent/gap-queue.csv"
if [[ ! -f "$queue" ]]; then
    echo "=== generating gap queue ==="
    python3 "${SCRIPT_DIR}/gap_fill_agent.py" generate-queue
fi

args=(--pr "$pr" --line "$line" --out "$out")
if [[ -n "$image" ]]; then
    args+=(--image "$image")
fi

cd "$REPO_ROOT"
python3 "${SCRIPT_DIR}/gap_fill_agent.py" build-context "${args[@]}"
