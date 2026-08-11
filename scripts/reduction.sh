#!/usr/bin/env bash
# Reduction: scaffold and optionally run batch-from-coverage for the first N gap-fill hits.
#
# Requires gap-fill output:
#   incremental/new_coverage.csv
#   candidate_tests/
#
# Produces t-00001-*/ directories under --output-dir (default: <gap-fill-dir>/reduced/).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=scripts/lib/reduction-local.sh
source "${SCRIPT_DIR}/lib/reduction-local.sh"
reduction_local_source_libs

# shellcheck source=scripts/lib/reduction.sh
source "${SCRIPT_DIR}/lib/reduction.sh"

usage() {
    cat <<EOF
Usage: $(basename "$0") --gap-fill-dir <path> -n <N> [options]

Scaffold (and optionally run) reduction for the first N rows of
incremental/new_coverage.csv from a gap-fill output directory.

Required:
  --gap-fill-dir <path>           Gap-fill output directory
  -n <N>, --n <N>                 Reduce the first N gap-fill hits

$(reduction_local_usage_llvm_options)

Options:
$(reduction_local_usage_common_options)

Examples:
  $(basename "$0") \\
      --gap-fill-dir ./data/gap-fill-out \\
      -n 1 \\
      --llvm-repo ./llvm-project \\
      --llvm-bin ./llvm-project/build/bin \\
      --instrumented-bin-dir ./llvm-project/build-sancov/bin

  $(basename "$0") \\
      --gap-fill-dir ./data/gap-fill-out \\
      -n 3 \\
      --scaffold-only \\
      --pipeline llvm_reduce_ir
EOF
}

if ! reduction_local_parse_args "$@"; then
    usage >&2
    exit 2
fi

if ! reduction_local_validate_required_paths; then
    usage >&2
    exit 1
fi

reduction_local_prepare_paths
reduction_local_setup_llvm_env

cd "$REPO_ROOT"
activate_venv_if_present "$REPO_ROOT"

echo "Using gap-fill output:"
echo "  gap-fill dir:    ${gap_fill_dir:-"(explicit paths)"}"
echo "  new coverage:    ${new_coverage_csv}"
echo "  candidate tests: ${candidate_tests_dir}"
echo "  output dir:      ${output_dir} (n=${reduction_n})"
if [[ "$scaffold_only" -eq 1 ]]; then
    echo "  mode:            scaffold-only"
fi
echo

rm -rf "${output_dir:?}"/*
mkdir -p "$output_dir"

reduction_local_batch_extra_args

run_batch_from_coverage \
    "$new_coverage_csv" \
    "$candidate_tests_dir" \
    "$output_dir" \
    "$reduction_n" \
    "${REDUCTION_BATCH_EXTRA_ARGS[@]}"

echo "Reduction output: ${output_dir}"
