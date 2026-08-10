#!/usr/bin/env bash
# Gap filling: candidate-test -> incremental against a precomputed gap list.
#
# Requires a gap list from gap finding (baseline or PR):
#   baseline/line_coverage_uncovered.csv  or  commit_lines_report/target_lines_uncovered.csv
#   plus baseline/llc_address_line_map.csv from the same baseline run.
#
# Produces <output-dir>/incremental/new_coverage.csv — candidate tests that fill gaps.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=scripts/lib/gap-filling-local.sh
source "${SCRIPT_DIR}/lib/gap-filling-local.sh"
gap_filling_local_source_libs

# shellcheck source=scripts/lib/gap-filling.sh
source "${SCRIPT_DIR}/lib/gap-filling.sh"

usage() {
    cat <<EOF
Usage: $(basename "$0") --output-dir <path> \\
    --line-coverage-uncovered-csv <path> --llc-address-line-map-csv <path> \\
    --candidate-tests-dir <path> -n <N> \\
    --llvm-repo <path> --llvm-bin <path> --instrumented-bin-dir <path> [options]

Run candidate-test and incremental locally (no Docker).
Artifacts are written under --output-dir/candidate_tests/ and --output-dir/incremental/.

Required:
  --output-dir <path>                   Output directory (created if missing)
  --line-coverage-uncovered-csv <path>  Uncovered-lines CSV (\`file\`, \`line\` columns)
  --llc-address-line-map-csv <path>     LLC address-to-line map from the same baseline run
  --candidate-tests-dir <path>          Fuzz corpus root
  -n <N>, --n <N>                       Run only the first N candidate tests (.ll/.bc, sorted)
$(gap_filling_local_usage_llvm_options)

Options:
$(gap_filling_local_usage_common_options)

Examples:
  $(basename "$0") \\
      --output-dir ./data/gap-fill \\
      --line-coverage-uncovered-csv ./data/gap-finding/baseline/line_coverage_uncovered.csv \\
      --llc-address-line-map-csv ./data/gap-finding/baseline/llc_address_line_map.csv \\
      --candidate-tests-dir /path/to/corpus \\
      -n 100 \\
      --llvm-repo /path/llvm-project \\
      --llvm-bin /path/llvm-project/build-sancov/bin \\
      --instrumented-bin-dir /path/llvm-project/build-sancov/bin \\
      -j "\$(nproc)"

  $(basename "$0") \\
      --output-dir ./data/gap-fill-pr \\
      --line-coverage-uncovered-csv ./data/gap-finding-pr/commit_lines_report/target_lines_uncovered.csv \\
      --llc-address-line-map-csv ./data/gap-finding-pr/baseline/llc_address_line_map.csv \\
      --candidate-tests-dir /path/to/corpus \\
      -n 100 \\
      --llvm-repo /path/llvm-project \\
      --llvm-bin /path/llvm-project/build-sancov/bin \\
      --instrumented-bin-dir /path/llvm-project/build-sancov/bin \\
      -j "\$(nproc)"
EOF
}

if ! gap_filling_local_parse_args "$@"; then
    usage >&2
    exit 2
fi

if ! gap_filling_local_validate_required_paths; then
    usage >&2
    exit 1
fi

gap_filling_local_prepare_output_dir
gap_filling_local_setup_llvm_env
require_local_gap_fill_bins

cd "$REPO_ROOT"
activate_venv_if_present "$REPO_ROOT"

candidate_tests_output_dir="$(gap_fill_candidate_tests_dir "$output_dir")"
incremental_output_dir="${output_dir}/incremental"

echo "Using coverage profile:"
echo "  uncovered lines: ${line_coverage_uncovered_csv}"
echo "  address map:     ${llc_address_line_map_csv}"
echo "  candidate dir:   ${candidate_tests_dir} (n=${candidate_n})"
echo

rm -rf "$candidate_tests_output_dir" "$incremental_output_dir"

run_candidate_test "$candidate_tests_output_dir" "$candidate_tests_dir" "$candidate_n"

run_incremental \
    "$incremental_output_dir" \
    "$line_coverage_uncovered_csv" \
    "$llc_address_line_map_csv" \
    "$candidate_tests_output_dir"

report="$(gap_fill_coverage_csv "$output_dir")"
echo "Gap-fill report: ${report}"
