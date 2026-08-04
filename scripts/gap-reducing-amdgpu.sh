#!/usr/bin/env bash
# Gap reducing (AMDGPU): reduce one row from gap-filling output.
#
# Requires gap-filling artifacts under --output-dir:
#   incremental/new_coverage.csv
#   candidate_tests/
#
# Usage:
#   ./scripts/gap-reducing-amdgpu.sh --output-dir ./data/my_run
#   ./scripts/gap-reducing-amdgpu.sh --output-dir ./data/my_run --row 2
#   ./scripts/gap-reducing-amdgpu.sh --output-dir ./data/my_run --prepare-only
#   WITH_CREDUCE=1 ./scripts/gap-reducing-amdgpu.sh --output-dir ./data/my_run
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${REPO_ROOT}/../llvm-project" && pwd)}"
LLVM_BIN="${LLVM_BIN:-${LLVM_REPO}/build/bin}"
INSTRUMENTED_BIN_DIR="${INSTRUMENTED_BIN_DIR:-${LLVM_REPO}/build-sancov/bin}"

output_dir=""
reduce_row="${REDUCE_ROW:-1}"
pipeline="${PIPELINE:-llvm_reduce_ir}"
prepare_only=0

usage() {
    cat <<EOF
Usage: $(basename "$0") --output-dir <path> [options]

Reduce one row from gap-filling output (new_coverage.csv + candidate_tests/).

Required:
  --output-dir <path>     Gap-fill output root (incremental/ and candidate_tests/ below)

Options:
  --row <n>               CSV row to reduce (default: 1, or \$REDUCE_ROW)
  --prepare-only          Create harness under reduced/ without running reduce
  --pipeline <ids>        Reduce pipeline pass ids (default: llvm_reduce_ir)
  --help, -h              Show this help

Environment (optional):
  OUTPUT_DIR              Default for --output-dir when omitted
  REDUCE_ROW              Default for --row
  PIPELINE                Default pipeline (default: llvm_reduce_ir)
  WITH_CREDUCE=1          Append creduce to the pipeline
  CREDUCE_N               Parallelism for creduce steps
  PASS_UNDER_TEST, MTRIPLE, EXTRACT_MIR_OUTPUT, MIR_CODEGEN_ONLY
                          Forwarded for MIR pipelines (see batch_reduce_using_coverage.sh)

Examples:
  $(basename "$0") --output-dir ./data/my_run
  $(basename "$0") --output-dir ./data/my_run --prepare-only
  PIPELINE=llvm_reduce_ir,creduce $(basename "$0") --output-dir ./data/my_run
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir)
            [[ $# -ge 2 ]] || { echo "error: --output-dir requires a value" >&2; exit 2; }
            output_dir="$2"
            shift 2
            ;;
        --row)
            [[ $# -ge 2 ]] || { echo "error: --row requires a value" >&2; exit 2; }
            reduce_row="$2"
            shift 2
            ;;
        --prepare-only)
            prepare_only=1
            shift
            ;;
        --pipeline)
            [[ $# -ge 2 ]] || { echo "error: --pipeline requires a value" >&2; exit 2; }
            pipeline="$2"
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

if [[ -z "$output_dir" ]]; then
    output_dir="${OUTPUT_DIR:-}"
fi
if [[ -z "$output_dir" ]]; then
    echo "error: --output-dir is required" >&2
    usage >&2
    exit 1
fi

# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
# shellcheck source=scripts/lib/gap-artifacts.sh
source "${SCRIPT_DIR}/lib/gap-artifacts.sh"
# shellcheck source=scripts/lib/gap-reducing-cli.sh
source "${SCRIPT_DIR}/lib/gap-reducing-cli.sh"

gap_reducing_validate_row "$reduce_row"

coverage_csv="$(gap_fill_coverage_csv "$output_dir")"
candidate_tests_dir="$(gap_fill_candidate_tests_dir "$output_dir")"
reduced_dir="$(gap_fill_reduced_dir "$output_dir")"
validate_gap_fill_artifacts "$coverage_csv" "$candidate_tests_dir" \
    "run gap-filling first (e.g. scripts/gap-filling-amdgpu.sh)"
# shellcheck source=scripts/lib/gap-reducing.sh
source "${SCRIPT_DIR}/lib/gap-reducing.sh"

activate_venv_if_present "$REPO_ROOT"

gap_reducing_apply_env "$prepare_only"

if [[ "$prepare_only" -eq 0 ]]; then
    require_bin "$INSTRUMENTED_BIN_DIR" llc
    require_bin "$LLVM_BIN" llvm-reduce
    export COVERAGE_LLC="${INSTRUMENTED_BIN_DIR}/llc"
    export COVERAGE_LLVM_REDUCE="${LLVM_BIN}/llvm-reduce"
fi

cd "$REPO_ROOT"

echo "=== AMDGPU gap reducing (row ${reduce_row}) ==="
echo "coverage csv:   $coverage_csv"
echo "candidate dir:  $candidate_tests_dir"
echo "output:         $reduced_dir"
echo "pipeline:       $pipeline"
if [[ "$prepare_only" -eq 1 ]]; then
    echo "mode:           prepare-only"
fi
echo

run_gap_reducing "$coverage_csv" "$candidate_tests_dir" "$reduced_dir" "$reduce_row" "$pipeline"
