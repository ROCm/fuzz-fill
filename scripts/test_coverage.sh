#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${REPO_ROOT}/../llvm-project" && pwd)}"
LLVM_BIN="${LLVM_BIN:-${LLVM_REPO}/build/bin}"
INSTRUMENTED_BIN_DIR="${INSTRUMENTED_BIN_DIR:-${LLVM_REPO}/build-amdgpu-bb/bin}"
OUTPUT_DIR="${REPO_ROOT}/data/coverage_output/bb_coverage_090626"
BASELINE_OUTPUT_DIR=$OUTPUT_DIR/baseline
CANDIDATE_TESTS_OUTPUT_DIR=$OUTPUT_DIR/candidate_tests
INCREMENTAL_OUTPUT_DIR=$OUTPUT_DIR/incremental
TESTS_DIR="${TESTS_DIR:-${REPO_ROOT}/../irtests/bitcode/amdgpu/all}"

#FILTER="CodeGen/AMDGPU/loop" # Small set of tests featuring both llc and opt for testing
FILTER="CodeGen/AMDGPU" # All tests

# Clear old output directories
rm -rf $TEST_SUITE_OUTPUT_DIR
rm -rf $NEW_TESTS_OUTPUT_DIR
rm -rf $DIFF_OUTPUT_DIR

cd "$REPO_ROOT"

python -m coverage baseline \
    --output-dir $BASELINE_OUTPUT_DIR \
    --sancov "$LLVM_BIN/sancov" \
    --llvm-lit "$INSTRUMENTED_BIN_DIR/llvm-lit" \
    --llc "$INSTRUMENTED_BIN_DIR/llc" \
    --opt "$INSTRUMENTED_BIN_DIR/opt" \
    --lit-filter $FILTER 

python -m coverage candidate-test \
    --output-dir $CANDIDATE_TESTS_OUTPUT_DIR \
    --llc "$INSTRUMENTED_BIN_DIR/llc" \
    --candidate-tests-dir $TESTS_DIR \
    --n 1000

python -m coverage incremental \
    --output-dir $INCREMENTAL_OUTPUT_DIR \
    --sancov "$LLVM_BIN/sancov" \
    --baseline-output-dir $BASELINE_OUTPUT_DIR \
    --candidate-tests-output-dir $CANDIDATE_TESTS_OUTPUT_DIR
