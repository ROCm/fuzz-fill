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

commit_rev=""

gap_finding_local_try_parse_extra() {
    GAP_FINDING_LOCAL_EXTRA_SHIFT=0

    case "$1" in
        --commit)
            [[ $# -ge 2 ]] || { echo "error: --commit requires a value" >&2; exit 2; }
            commit_rev="$2"
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
    --instrumented-bin-dir <path> --commit <rev> [options]

Run PR gap finding locally (no Docker): baseline, added_lines, target-lines.
Artifacts are written under --output-dir/.

Required:
  --output-dir <path>             Output directory (created if missing)
  --commit <rev>                  Revision for added_lines (HEAD, hash, main~3, ...)
$(gap_finding_local_usage_llvm_options)

Options:
$(gap_finding_local_usage_common_options)

Examples:
  $(basename "$0") \\
      --output-dir ./data/gap-finding-pr \\
      --llvm-repo /path/llvm-project \\
      --llvm-bin /path/llvm-project/build/bin \\
      --instrumented-bin-dir /path/llvm-project/build-sancov/bin \\
      --commit HEAD \\
      --backend-tests amdgpu -j "\$(nproc)"

  $(basename "$0") \\
      --output-dir ./data/gap-finding-pr \\
      --llvm-repo /path/llvm-project \\
      --llvm-bin /path/llvm-project/build/bin \\
      --instrumented-bin-dir /path/llvm-project/build-sancov/bin \\
      --commit b01fe4e \\
      --lit-filter CodeGen/AMDGPU -j "\$(nproc)"
EOF
}

if ! gap_finding_local_parse_args "$@"; then
    usage >&2
    exit 2
fi

if [[ -z "$commit_rev" ]]; then
    echo "error: --commit is required" >&2
    usage >&2
    exit 1
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
