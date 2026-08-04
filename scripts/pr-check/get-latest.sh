#!/usr/bin/env bash
# Regenerate latest.json / latest.md from data/pr-check/state.json.
#
# Does not run PR checks or require LLVM_REPO — only refreshes the report
# summary from whatever is already recorded in state.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_FILE="${PR_CHECK_CONFIG:-${SCRIPT_DIR}/config.env}"
ORCHESTRATOR="${SCRIPT_DIR}/check-llvm-prs.sh"
REPORT_DIR="${PR_CHECK_REPORT_DIR:-${REPO_ROOT}/data/pr-check/reports}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Regenerate data/pr-check/reports/latest.json and latest.md from state.json.
Does not run PR checks or require LLVM_REPO.

Options:
  --config <path>   Load path overrides from a config file
                    (default: ${CONFIG_FILE} if present)
  --help, -h        Show this help

Environment:
  PR_CHECK_CONFIG       Override config file path (default: ${CONFIG_FILE})
  PR_CHECK_REPORT_DIR   Report output directory (default: data/pr-check/reports)

Examples:
  $(basename "$0")
  $(basename "$0") --config /path/to/config.env
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --config)
            [[ $# -ge 2 ]] || { echo "error: --config requires a value" >&2; exit 2; }
            CONFIG_FILE="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        -*)
            echo "error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            echo "error: unexpected argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ ! -x "$ORCHESTRATOR" ]]; then
    echo "error: orchestrator not found or not executable: ${ORCHESTRATOR}" >&2
    exit 1
fi

orchestrator_args=(--report-only)
if [[ -f "$CONFIG_FILE" ]]; then
    orchestrator_args+=(--config "$CONFIG_FILE")
    # shellcheck source=/dev/null
    source "$CONFIG_FILE"
    REPORT_DIR="${PR_CHECK_REPORT_DIR:-${REPO_ROOT}/data/pr-check/reports}"
fi

cd "$REPO_ROOT"
"${ORCHESTRATOR}" "${orchestrator_args[@]}"

echo
echo "Report updated:"
echo "  ${REPORT_DIR}/latest.md"
echo "  ${REPORT_DIR}/latest.json"
