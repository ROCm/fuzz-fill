#!/usr/bin/env bash
# Gap finding (baseline): run coverage baseline over a filtered LIT slice.
#
# Produces line_coverage_uncovered.csv and llc_address_line_map.csv under
# <output-dir>/baseline/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=scripts/lib/gap-finding-local.sh
source "${SCRIPT_DIR}/lib/gap-finding-local.sh"
gap_finding_local_source_libs

# shellcheck source=scripts/lib/coverage-baseline.sh
source "${SCRIPT_DIR}/lib/coverage-baseline.sh"

usage() {
    cat <<EOF
Usage: $(basename "$0") --output-dir <path> --llvm-repo <path> --llvm-bin <path> \\
    --instrumented-bin-dir <path> [options]

Run coverage baseline locally (no Docker).
Artifacts are written under --output-dir/baseline/.

Required:
  --output-dir <path>             Output directory (created if missing)
$(gap_finding_local_usage_llvm_options)

Options:
$(gap_finding_local_usage_common_options)

Examples:
  $(basename "$0") \\
      --output-dir ./data/baseline-run \\
      --llvm-repo /path/llvm-project \\
      --llvm-bin /path/llvm-project/build/bin \\
      --instrumented-bin-dir /path/llvm-project/build-sancov/bin \\
      --backend-tests amdgpu -j "\$(nproc)"

  $(basename "$0") \\
      --output-dir ./data/baseline-codegen \\
      --llvm-repo /path/llvm-project \\
      --llvm-bin /path/llvm-project/build/bin \\
      --instrumented-bin-dir /path/llvm-project/build-sancov/bin \\
      --lit-filter CodeGen/AMDGPU -j "\$(nproc)"
EOF
}

if ! gap_finding_local_parse_args "$@"; then
    usage >&2
    exit 2
fi

if ! gap_finding_local_validate_required_paths; then
    usage >&2
    exit 1
fi

if ! gap_finding_local_default_lit_filters; then
    usage >&2
    exit 1
fi

gap_finding_local_prepare_output_dir
gap_finding_local_setup_llvm_env
require_local_coverage_bins

cd "$REPO_ROOT"
activate_venv_if_present "$REPO_ROOT"

baseline_output_dir="${output_dir}/baseline"
rm -rf "$baseline_output_dir"

run_coverage_baseline "$baseline_output_dir" "${lit_filters[@]}"

echo "Uncovered baseline lines: ${baseline_output_dir}/line_coverage_uncovered.csv"
echo "Uncovered baseline lines (pruned): ${baseline_output_dir}/line_coverage_uncovered_pruned.csv"
emit_lit_failures_warning "$output_dir" "downstream gap lists"
