#!/bin/bash
set -euo pipefail

HOME=/home/agorzyns/local/dev
LLVM=$HOME/llvm-project
INSTRUMENTED_BIN_DIR=$LLVM/build-amdgpu-bb/bin
OUTPUT_DIR=$HOME/fuzz-fill/data/coverage_output/bb_coverage_110526
CANDIDATE_TESTS_OUTPUT_DIR=$OUTPUT_DIR/candidate_tests
TESTS_DIR=$HOME/irtests/bitcode/amdgpu/all

# Clear old output directories
rm -rf $CANDIDATE_TESTS_OUTPUT_DIR

python -m coverage candidate-test \
    --output-dir $CANDIDATE_TESTS_OUTPUT_DIR \
    --instrumented-bin $INSTRUMENTED_BIN_DIR \
    --candidate-tests-dir $TESTS_DIR \
    --n 100
