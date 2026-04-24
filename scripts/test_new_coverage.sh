#!/bin/bash
set -euo pipefail

HOME=/home/agorzyns/local/dev
LLVM=$HOME/llvm-project
BUILD_DIR=$LLVM/build-amdgpu-bb
COVERAGE_DIR=$HOME/fuzz-fill/data/coverage_output/test_suite_full_bb_coverage_240426
TESTS_DIR=$HOME/irtests/bitcode/amdgpu/all

python -m cov_new test-suite \
    --output-dir $COVERAGE_DIR \
    --llvm-project $LLVM \
    --build-dir "$BUILD_DIR" \
    --filter "CodeGen/AMDGPU" \

python -m cov_new new-tests \
    --output-dir $COVERAGE_DIR \
    --llvm-project $LLVM \
    --build-dir "$BUILD_DIR" \
    --filter "CodeGen/AMDGPU" \
    --new-tests-dir $TESTS_DIR \
    --n 1

python -m cov_new diff \
    --output-dir $COVERAGE_DIR
