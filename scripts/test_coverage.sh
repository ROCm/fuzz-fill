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
<<<<<<< HEAD
rm -rf $BASELINE_OUTPUT_DIR
#rm -rf $CANDIDATE_TESTS_OUTPUT_DIR
#rm -rf $INCREMENTAL_OUTPUT_DIR
=======
rm -rf $TEST_SUITE_OUTPUT_DIR
rm -rf $NEW_TESTS_OUTPUT_DIR
rm -rf $DIFF_OUTPUT_DIR
>>>>>>> 7096b54 (Uncomment test lines)

cd "$REPO_ROOT"

python -m coverage baseline \
    --output-dir $BASELINE_OUTPUT_DIR \
    --llvm-bin $LLVM_BIN \
    --instrumented-bin $INSTRUMENTED_BIN_DIR \
    --lit-filter $FILTER 

<<<<<<< HEAD
#python -m coverage candidate-test \
#    --output-dir $CANDIDATE_TESTS_OUTPUT_DIR \
#    --instrumented-bin $INSTRUMENTED_BIN_DIR \
#    --candidate-tests-dir $TESTS_DIR \
#    --n 1000

# python -m coverage incremental \
#    --output-dir $INCREMENTAL_OUTPUT_DIR \
#    --llvm-bin $LLVM_BIN \
#    --baseline-output-dir $BASELINE_OUTPUT_DIR \
#    --candidate-tests-output-dir $CANDIDATE_TESTS_OUTPUT_DIR}
=======
python -m coverage new-tests \
    --output-dir $NEW_TESTS_OUTPUT_DIR \
    --instrumented-bin $INSTRUMENTED_BIN_DIR \
    --new-tests-dir $TESTS_DIR \
    --n 10

python -m coverage diff \
    --output-dir $DIFF_OUTPUT_DIR \
    --llvm-bin $LLVM_BIN \
    --test-suite-output-dir $TEST_SUITE_OUTPUT_DIR \
    --new-tests-output-dir $NEW_TESTS_OUTPUT_DIR
>>>>>>> 7096b54 (Uncomment test lines)

