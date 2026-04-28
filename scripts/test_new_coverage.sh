#!/bin/bash
set -euo pipefail

HOME=/home/agorzyns/local/dev
LLVM=$HOME/llvm-project
INSTRUMENTED_BIN_DIR=$LLVM/build-amdgpu-bb/bin
LLVM_BIN=$LLVM/build/bin
OUTPUT_DIR=$HOME/fuzz-fill/data/coverage_output/bb_coverage_270426
TEST_SUITE_OUTPUT_DIR=$OUTPUT_DIR/test_suite
NEW_TESTS_OUTPUT_DIR=$OUTPUT_DIR/new_tests
DIFF_OUTPUT_DIR=$OUTPUT_DIR/diff
TESTS_DIR=$HOME/irtests/bitcode/amdgpu/all

FILTER="CodeGen/AMDGPU/loop" # Small set of tests featuring both llc and opt for testing
#FILTER="CodeGen/AMDGPU" # All tests

# Clear old output directories
#rm -rf $TEST_SUITE_OUTPUT_DIR
rm -rf $NEW_TESTS_OUTPUT_DIR
rm -rf $DIFF_OUTPUT_DIR

python -m cov_new test-suite \
    --output-dir $TEST_SUITE_OUTPUT_DIR \
    --llvm-bin $LLVM_BIN \
    --instrumented-bin $INSTRUMENTED_BIN_DIR \
    --filter $FILTER 
exit 0
python -m cov_new new-tests \
    --output-dir $NEW_TESTS_OUTPUT_DIR \
    --instrumented-bin $INSTRUMENTED_BIN_DIR \
    --new-tests-dir $TESTS_DIR \
    --n 3

python -m cov_new diff \
    --output-dir $DIFF_OUTPUT_DIR \
    --llvm-bin $LLVM_BIN \
    --test-suite-output-dir $TEST_SUITE_OUTPUT_DIR \
    --new-tests-output-dir $NEW_TESTS_OUTPUT_DIR

