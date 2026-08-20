#!/usr/bin/env bash
# Rebuild data/pr-check/state.json from on-disk run artifacts.
#
# Scans data/pr-check/runs/<pr>-<backend>/, re-evaluates gap/LIT counts, and
# fills title/head_sha from saved reports (latest.json, runs/*.json) or GitHub.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PR_CHECK_STATE_FILE="${PR_CHECK_STATE_FILE:-${REPO_ROOT}/data/pr-check/state.json}"
PR_CHECK_OUTPUT_ROOT="${PR_CHECK_OUTPUT_ROOT:-${REPO_ROOT}/data/pr-check/runs}"
PR_CHECK_REPORT_DIR="${PR_CHECK_REPORT_DIR:-${REPO_ROOT}/data/pr-check/reports}"
PR_CHECK_LOG_LEVEL="${PR_CHECK_LOG_LEVEL:-info}"
GITHUB_REPO="${GITHUB_REPO:-llvm/llvm-project}"

CONFIG_FILE="${PR_CHECK_CONFIG:-${SCRIPT_DIR}/config.env}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Rebuild state.json from completed run directories under data/pr-check/runs/.
Uses saved report snapshots for historical head SHAs when available; otherwise
queries GitHub (current head SHA — see scripts/pr-check/README.md).

Options:
  --dry-run              Print rebuild stats without writing state.json
  --no-fetch-pr-metadata Skip gh lookups for runs missing report metadata
  --state-file <path>    Output state file (default: ${PR_CHECK_STATE_FILE})
  --output-root <path>   Run artifact root (default: ${PR_CHECK_OUTPUT_ROOT})
  --report-dir <path>    Report directory (default: ${PR_CHECK_REPORT_DIR})
  --config <path>        Load environment overrides from a file
  --help, -h             Show this help

Examples:
  $(basename "$0") --dry-run
  $(basename "$0")
  $(basename "$0") && ./scripts/pr-check/get-latest.sh
EOF
}

load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        # shellcheck source=/dev/null
        source "$CONFIG_FILE"
    fi
}

dry_run=0
extra_args=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            dry_run=1
            extra_args+=(--dry-run)
            shift
            ;;
        --no-fetch-pr-metadata)
            extra_args+=(--no-fetch-pr-metadata)
            shift
            ;;
        --state-file)
            [[ $# -ge 2 ]] || { echo "error: --state-file requires a value" >&2; exit 2; }
            PR_CHECK_STATE_FILE="$2"
            shift 2
            ;;
        --output-root)
            [[ $# -ge 2 ]] || { echo "error: --output-root requires a value" >&2; exit 2; }
            PR_CHECK_OUTPUT_ROOT="$2"
            shift 2
            ;;
        --report-dir)
            [[ $# -ge 2 ]] || { echo "error: --report-dir requires a value" >&2; exit 2; }
            PR_CHECK_REPORT_DIR="$2"
            shift 2
            ;;
        --config)
            [[ $# -ge 2 ]] || { echo "error: --config requires a value" >&2; exit 2; }
            CONFIG_FILE="$2"
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

load_config
require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "error: required command not found: $1" >&2
        exit 1
    fi
}

require_command python3
if [[ "${extra_args[*]}" != *"--no-fetch-pr-metadata"* ]]; then
    require_command gh
fi

mkdir -p "$(dirname "$PR_CHECK_STATE_FILE")"

PYTHONPATH="${REPO_ROOT}/src" python3 -m pr_check rebuild-state \
    --state-file "$PR_CHECK_STATE_FILE" \
    --output-root "$PR_CHECK_OUTPUT_ROOT" \
    --report-dir "$PR_CHECK_REPORT_DIR" \
    --github-repo "$GITHUB_REPO" \
    --log-level "$PR_CHECK_LOG_LEVEL" \
    "${extra_args[@]}"
