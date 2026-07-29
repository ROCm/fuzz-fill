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

if [[ ! "$reduce_row" =~ ^[0-9]+$ ]] || [[ "$reduce_row" -eq 0 ]]; then
    echo "error: --row must be a positive integer: ${reduce_row}" >&2
    exit 1
fi

coverage_csv="$output_dir/incremental/new_coverage.csv"
candidate_tests_dir="$output_dir/candidate_tests"
reduced_dir="$output_dir/reduced"

if [[ ! -f "$coverage_csv" ]]; then
    echo "error: gap-fill CSV not found: ${coverage_csv}" >&2
    echo "hint: run gap-filling first (e.g. scripts/gap-filling-amdgpu.sh)" >&2
    exit 1
fi
if [[ ! -d "$candidate_tests_dir" ]]; then
    echo "error: candidate_tests directory not found: ${candidate_tests_dir}" >&2
    exit 1
fi

if [[ -f "$REPO_ROOT/venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "$REPO_ROOT/venv/bin/activate"
fi

extra_args=(--pipeline "$pipeline")
if [[ -n "${WITH_CREDUCE:-}" ]]; then
    extra_args+=(--with-creduce)
fi
if [[ -n "${CREDUCE_N:-}" ]]; then
    extra_args+=(--creduce-n "$CREDUCE_N")
fi
if [[ -n "${PASS_UNDER_TEST:-}" ]]; then
    extra_args+=(--pass-under-test "$PASS_UNDER_TEST")
fi
if [[ -n "${MTRIPLE:-}" ]]; then
    extra_args+=(--mtriple "$MTRIPLE")
fi
if [[ -n "${EXTRACT_MIR_OUTPUT:-}" ]]; then
    extra_args+=(--extract-mir-output "$EXTRACT_MIR_OUTPUT")
fi
if [[ -n "${MIR_CODEGEN_ONLY:-}" ]]; then
    extra_args+=(--mir-codegen-only)
fi

batch_args=(
    python3 "${SCRIPT_DIR}/batch_reduce_using_coverage.py"
    --csv "$coverage_csv"
    --candidate-tests "$candidate_tests_dir"
    --output "$reduced_dir"
    --n "$reduce_row"
    "${extra_args[@]}"
)

if [[ "$prepare_only" -eq 0 ]]; then
    if [[ ! -x "$INSTRUMENTED_BIN_DIR/llc" ]]; then
        echo "error: missing $INSTRUMENTED_BIN_DIR/llc" >&2
        exit 1
    fi
    if [[ ! -x "$LLVM_BIN/llvm-reduce" ]]; then
        echo "error: missing $LLVM_BIN/llvm-reduce" >&2
        exit 1
    fi
    batch_args+=(--llc "$INSTRUMENTED_BIN_DIR/llc" --llvm-reduce "$LLVM_BIN/llvm-reduce")
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

"${batch_args[@]}"
