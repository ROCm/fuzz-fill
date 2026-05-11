#!/bin/bash
set -euo pipefail

HOME=/home/agorzyns/local/dev
LLVM=$HOME/llvm-project
INSTRUMENTED_BIN_DIR=$LLVM/build-amdgpu-bb/bin
OUTPUT_DIR=$HOME/fuzz-fill/data/coverage_output/bb_coverage_110526
NEW_TESTS_OUTPUT_DIR=$OUTPUT_DIR/new_tests
TESTS_DIR=$HOME/irtests/bitcode/amdgpu/all

# Clear old output directories
rm -rf $NEW_TESTS_OUTPUT_DIR

python -m coverage new-tests \
    --output-dir $NEW_TESTS_OUTPUT_DIR \
    --instrumented-bin $INSTRUMENTED_BIN_DIR \
    --new-tests-dir $TESTS_DIR \
    --n 100
