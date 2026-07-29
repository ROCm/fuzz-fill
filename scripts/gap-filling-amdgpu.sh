#!/usr/bin/env bash
# Gap filling (AMDGPU): candidate-test -> incremental for a fuzz corpus.
#
# Requires a gap list from gap finding (baseline or PR):
#   baseline/line_coverage_uncovered.csv  or  commit_lines_report/target_lines_uncovered.csv
#   plus baseline/llc_address_line_map.csv from the same baseline run.
#
# Usage:
#   ./scripts/gap-filling-amdgpu.sh
#   OUTPUT_DIR=./data/my_run ./scripts/gap-filling-amdgpu.sh
#   JOBS="$(nproc)" ./scripts/gap-filling-amdgpu.sh
#   SKIP_BASELINE=1 ./scripts/gap-filling-amdgpu.sh   # reuse existing gap list under output/baseline/
#   REFRESH=all ./scripts/gap-filling-amdgpu.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${REPO_ROOT}/../llvm-project" && pwd)}"
LLVM_BIN="${LLVM_BIN:-${LLVM_REPO}/build/bin}"
INSTRUMENTED_BIN_DIR="${INSTRUMENTED_BIN_DIR:-${LLVM_REPO}/build-sancov/bin}"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/data/coverage_output/bb_coverage_amdgpu_$(date +%y%m%d)}"
BASELINE_OUTPUT_DIR="$OUTPUT_DIR/baseline"
CANDIDATE_TESTS_OUTPUT_DIR="$OUTPUT_DIR/candidate_tests"
INCREMENTAL_OUTPUT_DIR="$OUTPUT_DIR/incremental"
TESTS_DIR="${TESTS_DIR:-${REPO_ROOT}/../irtests/bitcode/amdgpu/all}"
CORPUS_N="${CORPUS_N:-100}"

# shellcheck source=scripts/lit-filters-amdgpu.sh
source "${SCRIPT_DIR}/lit-filters-amdgpu.sh"
LIT_FILTERS=("${AMDGPU_LIT_FILTERS[@]}")

require_bin() {
    local dir="$1" tool="$2"
    if [[ ! -x "$dir/$tool" ]]; then
        echo "error: missing $dir/$tool" >&2
        exit 1
    fi
}

if [[ -f "$REPO_ROOT/venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "$REPO_ROOT/venv/bin/activate"
fi

require_bin "$LLVM_BIN" sancov
require_bin "$INSTRUMENTED_BIN_DIR" llvm-lit
require_bin "$INSTRUMENTED_BIN_DIR" llc
require_bin "$INSTRUMENTED_BIN_DIR" opt

case "${REFRESH:-}" in
    all)
        rm -rf "$BASELINE_OUTPUT_DIR" "$CANDIDATE_TESTS_OUTPUT_DIR" "$INCREMENTAL_OUTPUT_DIR"
        ;;
    baseline)
        rm -rf "$BASELINE_OUTPUT_DIR"
        ;;
    candidate)
        rm -rf "$CANDIDATE_TESTS_OUTPUT_DIR"
        ;;
    incremental)
        rm -rf "$INCREMENTAL_OUTPUT_DIR"
        ;;
    "")
        ;;
    *)
        echo "error: unknown REFRESH=$REFRESH (use all, baseline, candidate, or incremental)" >&2
        exit 1
        ;;
esac

mkdir -p "$OUTPUT_DIR"
cd "$REPO_ROOT"

echo "=== AMDGPU gap filling ==="
echo "output:         $OUTPUT_DIR"
echo "llvm-bin:       $LLVM_BIN"
echo "instrumented:   $INSTRUMENTED_BIN_DIR"
echo "candidate dir:  $TESTS_DIR (n=$CORPUS_N)"
echo "lit filters:    ${LIT_FILTERS[*]}"
echo

if [[ -z "${SKIP_BASELINE:-}" ]]; then
    echo ">>> Step 1/3: gap finding — baseline (LIT)"
    baseline_args=(
        python -m coverage baseline
        --output-dir "$BASELINE_OUTPUT_DIR"
        --sancov "$LLVM_BIN/sancov"
        --llvm-lit "$INSTRUMENTED_BIN_DIR/llvm-lit"
        --llc "$INSTRUMENTED_BIN_DIR/llc"
        --opt "$INSTRUMENTED_BIN_DIR/opt"
    )
    for lit_filter in "${LIT_FILTERS[@]}"; do
        baseline_args+=(--lit-filter "$lit_filter")
    done
    if [[ -n "${JOBS:-}" ]]; then
        baseline_args+=(-j "$JOBS")
    fi
    "${baseline_args[@]}"
else
    echo ">>> Step 1/3: skipped (SKIP_BASELINE=1; using existing gap list under $BASELINE_OUTPUT_DIR)"
fi

if [[ -z "${SKIP_CANDIDATE:-}" ]]; then
    echo ">>> Step 2/3: candidate-test"
    python -m coverage candidate-test \
        --output-dir "$CANDIDATE_TESTS_OUTPUT_DIR" \
        --llc "$INSTRUMENTED_BIN_DIR/llc" \
        --candidate-tests-dir "$TESTS_DIR" \
        --n "$CORPUS_N"
else
    echo ">>> Step 2/3: skipped (SKIP_CANDIDATE=1)"
fi

if [[ -z "${SKIP_INCREMENTAL:-}" ]]; then
    echo ">>> Step 3/3: incremental"
    python -m coverage incremental \
        --output-dir "$INCREMENTAL_OUTPUT_DIR" \
        --sancov "$LLVM_BIN/sancov" \
        --line-coverage-uncovered-csv "$BASELINE_OUTPUT_DIR/line_coverage_uncovered.csv" \
        --llc-address-line-map-csv "$BASELINE_OUTPUT_DIR/llc_address_line_map.csv" \
        --candidate-tests-output-dir "$CANDIDATE_TESTS_OUTPUT_DIR"
else
    echo ">>> Step 3/3: skipped (SKIP_INCREMENTAL=1)"
fi

echo
echo "Gap-fill report: $INCREMENTAL_OUTPUT_DIR/new_coverage.csv"
