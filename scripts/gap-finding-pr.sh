#!/usr/bin/env bash
# Gap finding (PR-specific): baseline -> added_lines -> target-lines.
#
# Produces commit_lines_report/target_lines_uncovered.csv — added source lines
# the baseline still does not cover.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=scripts/lib/gap-finding-local.sh
source "${SCRIPT_DIR}/lib/gap-finding-local.sh"
gap_finding_local_source_libs

# shellcheck source=scripts/lib/gap-finding-pr.sh
source "${SCRIPT_DIR}/lib/gap-finding-pr.sh"

# shellcheck source=scripts/lib/prepare-pr-llvm.sh
source "${SCRIPT_DIR}/lib/prepare-pr-llvm.sh"

commit_rev=""
pr_id=""
github_repo="llvm/llvm-project"
reference_repo=""

gap_finding_local_try_parse_extra() {
    GAP_FINDING_LOCAL_EXTRA_SHIFT=0

    case "$1" in
        --commit)
            [[ $# -ge 2 ]] || { echo "error: --commit requires a value" >&2; exit 2; }
            commit_rev="$2"
            GAP_FINDING_LOCAL_EXTRA_SHIFT=2
            return 0
            ;;
        --pr-id)
            [[ $# -ge 2 ]] || { echo "error: --pr-id requires a value" >&2; exit 2; }
            pr_id="$2"
            GAP_FINDING_LOCAL_EXTRA_SHIFT=2
            return 0
            ;;
        --github-repo)
            [[ $# -ge 2 ]] || { echo "error: --github-repo requires a value" >&2; exit 2; }
            github_repo="$2"
            GAP_FINDING_LOCAL_EXTRA_SHIFT=2
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

usage() {
    cat <<EOF
Usage: $(basename "$0") --output-dir <path> --llvm-repo <path> --llvm-bin <path> \\
    --instrumented-bin-dir <path> (--commit <rev> | --pr-id <n>) [options]

Run PR gap finding locally (no Docker): baseline, added_lines, target-lines.
Artifacts are written under --output-dir/.

Required:
  --output-dir <path>             Output directory (created if missing)
  One of:
    --commit <rev>                Revision for added_lines (HEAD, hash, main~3, ...)
    --pr-id <n>                   GitHub PR number (squashes PR into worktree)
$(gap_finding_local_usage_llvm_options)

Options:
  --github-repo <owner/repo>      With --pr-id (default: llvm/llvm-project)
$(gap_finding_local_usage_common_options)

Examples:
  $(basename "$0") \\
      --output-dir ./data/gap-finding-pr \\
      --llvm-repo /path/llvm-project \\
      --llvm-bin /path/llvm-project/build-sancov/bin \\
      --instrumented-bin-dir /path/llvm-project/build-sancov/bin \\
      --commit HEAD \\
      --backend-tests amdgpu -j "\$(nproc)"

  $(basename "$0") \\
      --output-dir ./data/gap-finding-pr-214457 \\
      --llvm-repo /path/llvm-project \\
      --llvm-bin /path/to/pr-tree/build-sancov/bin \\
      --instrumented-bin-dir /path/to/pr-tree/build-sancov/bin \\
      --pr-id 214457 \\
      --backend-tests amdgpu -j "\$(nproc)"
EOF
}

if ! gap_finding_local_parse_args "$@"; then
    usage >&2
    exit 2
fi

if [[ -n "$commit_rev" && -n "$pr_id" ]]; then
    echo "error: pass only one of --commit or --pr-id" >&2
    usage >&2
    exit 1
fi

if [[ -z "$commit_rev" && -z "$pr_id" ]]; then
    echo "error: one of --commit or --pr-id is required" >&2
    usage >&2
    exit 1
fi

if [[ -n "$pr_id" ]]; then
    if [[ ! "$pr_id" =~ ^[0-9]+$ ]] || [[ "$pr_id" -eq 0 ]]; then
        echo "error: --pr-id must be a positive integer: ${pr_id}" >&2
        exit 1
    fi

    reference_repo="$llvm_repo"
    worktree_root="${REPO_ROOT}/.fuzz-fill-llvm-pr-worktrees/pr-${pr_id}"
    pr_llvm="${worktree_root}/llvm-project"
    squash_commit_file="${worktree_root}/squash-commit"

    prepare_pr_llvm_worktree \
        --pr-id "$pr_id" \
        --dest "$pr_llvm" \
        --github-repo "$github_repo" \
        --reference "$reference_repo" \
        --squash-commit-file "$squash_commit_file" \
        --reuse

    llvm_repo="$PREPARE_PR_REPO_DIR"
    commit_rev="$PREPARE_PR_SQUASH_OID"
fi

if ! gap_finding_local_validate_required_paths; then
    usage >&2
    exit 1
fi

if ! gap_finding_local_default_lit_filters multi; then
    usage >&2
    exit 1
fi

gap_finding_local_prepare_output_dir
gap_finding_local_setup_llvm_env
require_local_coverage_bins

cd "$REPO_ROOT"
activate_venv_if_present "$REPO_ROOT"

run_gap_finding_pr "$output_dir" "$commit_rev" "$LLVM_REPO" "${lit_filters[@]}"

report="${output_dir}/commit_lines_report/target_lines_uncovered.csv"
echo "Uncovered PR target lines: ${report}"
emit_lit_failures_warning "$output_dir" "target_lines_uncovered.csv"
