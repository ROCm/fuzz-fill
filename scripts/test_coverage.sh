#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${REPO_ROOT}/../llvm-project" && pwd)}"
LLVM_BIN="${LLVM_BIN:-${LLVM_REPO}/build/bin}"
INSTRUMENTED_BIN_DIR="${INSTRUMENTED_BIN_DIR:-${LLVM_REPO}/build-amdgpu-bb/bin}"
OUTPUT_DIR="${REPO_ROOT}/data/coverage_output/bb_coverage_080726_no_prune"
BASELINE_OUTPUT_DIR=$OUTPUT_DIR/baseline
CANDIDATE_TESTS_OUTPUT_DIR=$OUTPUT_DIR/candidate_tests
INCREMENTAL_OUTPUT_DIR=$OUTPUT_DIR/incremental
TESTS_DIR="${TESTS_DIR:-${REPO_ROOT}/../irtests/bitcode/amdgpu/all}"

PATH_FILTER="${PATH_FILTER:-llvm/lib/Target/AMDGPU}"
# FILTER: llvm-lit --filter= regex or path prefix (default: all AMDGPU/ folders).
# Faster CodeGen-only subset: FILTER=CodeGen/AMDGPU
FILTER="${FILTER:-(^|/)AMDGPU/}"

# Clear old output directories
rm -rf $BASELINE_OUTPUT_DIR
rm -rf $CANDIDATE_TESTS_OUTPUT_DIR
rm -rf $INCREMENTAL_OUTPUT_DIR

cd "$REPO_ROOT"

python -m coverage baseline \
    --output-dir $BASELINE_OUTPUT_DIR \
    --sancov "$LLVM_BIN/sancov" \
    --llvm-lit "$INSTRUMENTED_BIN_DIR/llvm-lit" \
    --llc "$INSTRUMENTED_BIN_DIR/llc" \
    --opt "$INSTRUMENTED_BIN_DIR/opt" \
    --lit-filter "$FILTER" \
    --path-filter "$PATH_FILTER"

python -m coverage candidate-test \
    --output-dir $CANDIDATE_TESTS_OUTPUT_DIR \
    --llc "$INSTRUMENTED_BIN_DIR/llc" \
    --candidate-tests-dir $TESTS_DIR \
    --n 100

python -m coverage incremental \
    --output-dir $INCREMENTAL_OUTPUT_DIR \
    --sancov "$LLVM_BIN/sancov" \
    --line-coverage-uncovered-csv $BASELINE_OUTPUT_DIR/line_coverage_uncovered.csv \
    --llc-address-line-map-csv $BASELINE_OUTPUT_DIR/llc_address_line_map.csv \
    --candidate-tests-output-dir $CANDIDATE_TESTS_OUTPUT_DIR
