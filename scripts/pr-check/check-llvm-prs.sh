#!/usr/bin/env bash
# Periodic orchestrator for LLVM AMDGPU/SPIR-V PR coverage-gap detection.
#
# Discovers open target PRs, plans work against state.json, and runs
# pr-cov-gaps-detection.sh for PR/backend pairs whose head SHA changed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

LLVM_REPO="${LLVM_REPO:-}"
PR_CHECK_JOBS="${PR_CHECK_JOBS:-$(nproc)}"
PR_CHECK_MAX_PER_RUN="${PR_CHECK_MAX_PER_RUN:-1}"
PR_CHECK_SEARCH_LIMIT="${PR_CHECK_SEARCH_LIMIT:-100}"
PR_CHECK_MAX_AGE_DAYS="${PR_CHECK_MAX_AGE_DAYS:-14}"
PR_CHECK_BACKENDS="${PR_CHECK_BACKENDS:-}"
PR_CHECK_OUTPUT_ROOT="${PR_CHECK_OUTPUT_ROOT:-${REPO_ROOT}/data/pr-check/runs}"
PR_CHECK_STATE_FILE="${PR_CHECK_STATE_FILE:-${REPO_ROOT}/data/pr-check/state.json}"
PR_CHECK_REPORT_DIR="${PR_CHECK_REPORT_DIR:-${REPO_ROOT}/data/pr-check/reports}"
PR_CHECK_LOG_LEVEL="${PR_CHECK_LOG_LEVEL:-info}"
GITHUB_REPO="${GITHUB_REPO:-llvm/llvm-project}"
IMAGE_NAME="${IMAGE_NAME:-fuzz-fill-test}"

CONFIG_FILE="${PR_CHECK_CONFIG:-${SCRIPT_DIR}/config.env}"

discover_only=0
plan_only=0
report_only=0
drain_queue=0

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Discover open AMDGPU/SPIR-V PRs on ${GITHUB_REPO}, plan work from state, and
run coverage-gap detection for PR/backend pairs with new or changed head SHAs.

Options:
  --discover-only          List matching PRs and exit
  --plan-only              Print planned work items and exit
  --report-only            Regenerate latest.json/latest.md from state and exit
  --config <path>          Load environment overrides from a file
                           (default: ${SCRIPT_DIR}/config.env if present)
  --llvm-repo <path>       Local llvm-project clone (required unless set in config)
  --state-file <path>      State file (default: ${PR_CHECK_STATE_FILE})
  --output-root <path>     Per-run artifact root (default: ${PR_CHECK_OUTPUT_ROOT})
  --report-dir <path>      Report output directory (default: ${PR_CHECK_REPORT_DIR})
  --max-per-run <n>        Max PR/backend checks per invocation (default: ${PR_CHECK_MAX_PER_RUN})
  --drain-queue            Process all pending checks (one at a time until queue empty)
  --max-age-days <n>       Only PRs opened in the last N days (default: ${PR_CHECK_MAX_AGE_DAYS})
  --backends <list>        Comma-separated backends to check (default: amdgpu,spirv)
  --jobs <n>               Parallel jobs for Docker build and LIT (default: ${PR_CHECK_JOBS})
  --log-level <level>        Python log level: debug, info, warning, error
                             (default: ${PR_CHECK_LOG_LEVEL})
  -v, --verbose             Shorthand for --log-level debug
  --github-repo <owner/repo>
                           GitHub repo hosting PRs (default: ${GITHUB_REPO})
  --help, -h               Show this help

Configuration:
  Copy ${SCRIPT_DIR}/config.example.env to ${SCRIPT_DIR}/config.env and set
  LLVM_REPO before running under cron.

Examples:
  $(basename "$0") --discover-only
  $(basename "$0") --plan-only
  $(basename "$0") --llvm-repo /path/to/llvm-project
EOF
}

load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        # shellcheck source=/dev/null
        source "$CONFIG_FILE"
    fi
}

run_pr_check() {
    PYTHONPATH="${REPO_ROOT}/scripts" python3 -m pr_check \
        "$@" \
        --log-level "$PR_CHECK_LOG_LEVEL"
}

generate_report() {
    echo "=== coverage gap report ==="
    run_pr_check report \
        --github-repo "$GITHUB_REPO" \
        --state-file "$PR_CHECK_STATE_FILE" \
        --report-dir "$PR_CHECK_REPORT_DIR"
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "error: required command not found: $1" >&2
        exit 1
    fi
}

validate_positive_int() {
    local name="$1"
    local value="$2"
    if [[ ! "$value" =~ ^[0-9]+$ ]] || [[ "$value" -eq 0 ]]; then
        echo "error: ${name} must be a positive integer: ${value}" >&2
        exit 1
    fi
}

validate_runtime_config() {
    if [[ -z "$LLVM_REPO" ]]; then
        echo "error: LLVM_REPO is required (set in config.env or pass --llvm-repo)" >&2
        exit 1
    fi
    if [[ ! -d "$LLVM_REPO" ]]; then
        echo "error: LLVM_REPO is not a directory: ${LLVM_REPO}" >&2
        exit 1
    fi
    validate_positive_int "PR_CHECK_JOBS" "$PR_CHECK_JOBS"
    validate_positive_int "PR_CHECK_MAX_PER_RUN" "$PR_CHECK_MAX_PER_RUN"
    validate_positive_int "PR_CHECK_SEARCH_LIMIT" "$PR_CHECK_SEARCH_LIMIT"
    validate_positive_int "PR_CHECK_MAX_AGE_DAYS" "$PR_CHECK_MAX_AGE_DAYS"
}

record_failed_run() {
    local pr_number="$1"
    local backend="$2"
    local title="$3"
    local head_sha="$4"
    local output_dir="$5"
    local error_message="$6"

    run_pr_check record \
        --state-file "$PR_CHECK_STATE_FILE" \
        --pr-number "$pr_number" \
        --backend "$backend" \
        --title "$title" \
        --head-sha "$head_sha" \
        --status failed \
        --gap-count 0 \
        --lit-failure-count 0 \
        --output-dir "$output_dir" \
        --error "$error_message"
}

run_one_work_item() {
    local pr_number="$1"
    local backend="$2"
    local title="$3"
    local head_sha="$4"

    local output_dir="${PR_CHECK_OUTPUT_ROOT}/${pr_number}-${backend}"
    local image_tag="llvm-pr-${pr_number}-${backend}"
    local image_ref="${IMAGE_NAME}:${image_tag}"

    mkdir -p "$output_dir"
    output_dir="$(realpath "$output_dir")"

    echo "=== PR #${pr_number} (${backend}) ==="
    echo "Title: ${title}"
    echo "Head:  ${head_sha}"
    echo "Output: ${output_dir}"

    set +e
    "${REPO_ROOT}/scripts/docker/build-image-pr.sh" \
        --llvm-repo "$LLVM_REPO" \
        --pr-id "$pr_number" \
        --allowlist "$backend" \
        --github-repo "$GITHUB_REPO" \
        --tag "$image_tag" \
        -j "$PR_CHECK_JOBS"
    build_status=$?

    if [[ "$build_status" -ne 0 ]]; then
        set -e
        record_failed_run "$pr_number" "$backend" "$title" "$head_sha" "$output_dir" "docker image build failed"
        return "$build_status"
    fi

    "${REPO_ROOT}/scripts/docker/pr-cov-gaps-detection.sh" \
        --image "$image_ref" \
        --output-dir "$output_dir" \
        --keep-image \
        -j "$PR_CHECK_JOBS"
    detect_status=$?
    set -e

    if [[ "$detect_status" -ne 0 ]]; then
        record_failed_run "$pr_number" "$backend" "$title" "$head_sha" "$output_dir" "coverage-gap detection failed"
        return "$detect_status"
    fi

    local evaluation
    evaluation="$(run_pr_check evaluate-output --output-dir "$output_dir")"
    local gap_count lit_failure_count status
    gap_count="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["gap_count"])' <<<"$evaluation")"
    lit_failure_count="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["lit_failure_count"])' <<<"$evaluation")"
    status="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' <<<"$evaluation")"

    run_pr_check record \
        --state-file "$PR_CHECK_STATE_FILE" \
        --pr-number "$pr_number" \
        --backend "$backend" \
        --title "$title" \
        --head-sha "$head_sha" \
        --status "$status" \
        --gap-count "$gap_count" \
        --lit-failure-count "$lit_failure_count" \
        --output-dir "$output_dir"

    echo "Result: status=${status} gap_count=${gap_count} lit_failures=${lit_failure_count}"
}

plan_work_json() {
    local max_items="$1"
    local plan_args=(
        "${common_args[@]}"
        --state-file "$PR_CHECK_STATE_FILE"
        --limit "$PR_CHECK_SEARCH_LIMIT"
    )
    if [[ -n "$max_items" ]]; then
        plan_args+=(--max-items "$max_items")
    fi
    run_pr_check plan "${plan_args[@]}"
}

work_count_from_json() {
    local work_json="$1"
    python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' <<<"$work_json"
}

run_work_items() {
    local work_json="$1"

    while IFS= read -r item; do
        local pr_number backend title head_sha reason
        pr_number="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["pr_number"])' "$item")"
        backend="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["backend"])' "$item")"
        title="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["title"])' "$item")"
        head_sha="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["head_sha"])' "$item")"
        reason="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["reason"])' "$item")"

        echo
        echo ">>> Running check (${reason}): #${pr_number} ${backend}"
        if ! run_one_work_item "$pr_number" "$backend" "$title" "$head_sha"; then
            failures=$((failures + 1))
        fi
    done < <(python3 -c 'import json,sys; print("\n".join(json.dumps(x) for x in json.load(sys.stdin)))' <<<"$work_json")
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --discover-only)
            discover_only=1
            shift
            ;;
        --plan-only)
            plan_only=1
            shift
            ;;
        --report-only)
            report_only=1
            shift
            ;;
        --config)
            [[ $# -ge 2 ]] || { echo "error: --config requires a value" >&2; exit 2; }
            CONFIG_FILE="$2"
            shift 2
            ;;
        --llvm-repo)
            [[ $# -ge 2 ]] || { echo "error: --llvm-repo requires a value" >&2; exit 2; }
            LLVM_REPO="$2"
            shift 2
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
        --max-per-run)
            [[ $# -ge 2 ]] || { echo "error: --max-per-run requires a value" >&2; exit 2; }
            PR_CHECK_MAX_PER_RUN="$2"
            shift 2
            ;;
        --drain-queue)
            drain_queue=1
            shift
            ;;
        --max-age-days)
            [[ $# -ge 2 ]] || { echo "error: --max-age-days requires a value" >&2; exit 2; }
            PR_CHECK_MAX_AGE_DAYS="$2"
            shift 2
            ;;
        --backends)
            [[ $# -ge 2 ]] || { echo "error: --backends requires a value" >&2; exit 2; }
            PR_CHECK_BACKENDS="$2"
            shift 2
            ;;
        --jobs)
            [[ $# -ge 2 ]] || { echo "error: --jobs requires a value" >&2; exit 2; }
            PR_CHECK_JOBS="$2"
            shift 2
            ;;
        --log-level)
            [[ $# -ge 2 ]] || { echo "error: --log-level requires a value" >&2; exit 2; }
            PR_CHECK_LOG_LEVEL="$2"
            shift 2
            ;;
        -v|--verbose)
            PR_CHECK_LOG_LEVEL="debug"
            shift
            ;;
        --github-repo)
            [[ $# -ge 2 ]] || { echo "error: --github-repo requires a value" >&2; exit 2; }
            GITHUB_REPO="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --)
            shift
            break
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

if [[ $# -gt 0 ]]; then
    echo "error: unexpected argument: $1" >&2
    usage >&2
    exit 2
fi

load_config
require_command python3
require_command docker
require_command gh
require_command git

mkdir -p "$(dirname "$PR_CHECK_STATE_FILE")" "$PR_CHECK_OUTPUT_ROOT" "$PR_CHECK_REPORT_DIR"

common_args=(
    --github-repo "$GITHUB_REPO"
    --max-age-days "$PR_CHECK_MAX_AGE_DAYS"
)
if [[ -n "$PR_CHECK_BACKENDS" ]]; then
    common_args+=(--backends "$PR_CHECK_BACKENDS")
fi

if [[ "$report_only" -eq 1 ]]; then
    generate_report
    exit 0
fi

if [[ "$discover_only" -eq 1 ]]; then
    echo "=== discover open PRs (log-level=${PR_CHECK_LOG_LEVEL}) ===" >&2
    run_pr_check discover "${common_args[@]}" --limit "$PR_CHECK_SEARCH_LIMIT"
    exit 0
fi

if [[ "$plan_only" -eq 1 ]]; then
    echo "=== plan PR checks (log-level=${PR_CHECK_LOG_LEVEL}) ===" >&2
    run_pr_check plan \
        "${common_args[@]}" \
        --state-file "$PR_CHECK_STATE_FILE" \
        --limit "$PR_CHECK_SEARCH_LIMIT" \
        --max-items "$PR_CHECK_MAX_PER_RUN"
    exit 0
fi

validate_runtime_config

echo "=== automated PR check run (log-level=${PR_CHECK_LOG_LEVEL}) ===" >&2

failures=0
total_checks=0

if [[ "$drain_queue" -eq 1 ]]; then
    echo "Draining queue (one check at a time until empty)..." >&2
    while true; do
        work_json="$(plan_work_json 1)"
        work_count="$(work_count_from_json "$work_json")"
        if [[ "$work_count" -eq 0 ]]; then
            break
        fi

        total_checks=$((total_checks + work_count))
        echo "Planned check ${total_checks} (draining queue)..." >&2
        run_work_items "$work_json"
    done

    if [[ "$total_checks" -eq 0 ]]; then
        echo "No PR/backend pairs need checking."
    else
        echo
        echo "Completed ${total_checks} check(s) while draining queue."
    fi
else
    echo "Discovering and planning work (max ${PR_CHECK_MAX_PER_RUN} check(s) this run)..." >&2

    work_json="$(plan_work_json "$PR_CHECK_MAX_PER_RUN")"
    work_count="$(work_count_from_json "$work_json")"
    if [[ "$work_count" -eq 0 ]]; then
        echo "No PR/backend pairs need checking."
        generate_report
        exit 0
    fi

    echo "Planned ${work_count} PR/backend check(s)."
    total_checks=$work_count
    run_work_items "$work_json"
fi

if [[ "$total_checks" -eq 0 ]]; then
    generate_report
    exit 0
fi

if [[ "$failures" -gt 0 ]]; then
    echo
    echo "${failures} check(s) failed (see state file for details)."
    generate_report
    exit 1
fi

echo
echo "All planned checks completed successfully."
generate_report
