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

# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
# shellcheck source=scripts/lib/coverage-baseline.sh
source "${SCRIPT_DIR}/lib/coverage-baseline.sh"
# shellcheck source=scripts/lib/gap-filling.sh
source "${SCRIPT_DIR}/lib/gap-filling.sh"

activate_venv_if_present "$REPO_ROOT"

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

export COVERAGE_SANCOV="${LLVM_BIN}/sancov"
export COVERAGE_LLVM_LIT="${INSTRUMENTED_BIN_DIR}/llvm-lit"
export COVERAGE_LLC="${INSTRUMENTED_BIN_DIR}/llc"
export COVERAGE_OPT="${INSTRUMENTED_BIN_DIR}/opt"

echo "=== AMDGPU gap filling ==="
echo "output:         $OUTPUT_DIR"
echo "llvm-bin:       $LLVM_BIN"
echo "instrumented:   $INSTRUMENTED_BIN_DIR"
echo "candidate dir:  $TESTS_DIR (n=$CORPUS_N)"
echo "lit filters:    ${LIT_FILTERS[*]}"
echo

if [[ -z "${SKIP_BASELINE:-}" ]]; then
    echo ">>> Step 1/3: gap finding — baseline (LIT)"
    run_coverage_baseline "$BASELINE_OUTPUT_DIR" "${LIT_FILTERS[@]}"
else
    echo ">>> Step 1/3: skipped (SKIP_BASELINE=1; using existing gap list under $BASELINE_OUTPUT_DIR)"
fi

if [[ -z "${SKIP_CANDIDATE:-}" ]]; then
    echo ">>> Step 2/3: candidate-test"
    run_candidate_test "$CANDIDATE_TESTS_OUTPUT_DIR" "$TESTS_DIR" "$CORPUS_N"
else
    echo ">>> Step 2/3: skipped (SKIP_CANDIDATE=1)"
fi

if [[ -z "${SKIP_INCREMENTAL:-}" ]]; then
    echo ">>> Step 3/3: incremental"
    run_incremental \
        "$INCREMENTAL_OUTPUT_DIR" \
        "$BASELINE_OUTPUT_DIR/line_coverage_uncovered.csv" \
        "$BASELINE_OUTPUT_DIR/llc_address_line_map.csv" \
        "$CANDIDATE_TESTS_OUTPUT_DIR"
else
    echo ">>> Step 3/3: skipped (SKIP_INCREMENTAL=1)"
fi

echo
echo "Gap-fill report: $INCREMENTAL_OUTPUT_DIR/new_coverage.csv"
