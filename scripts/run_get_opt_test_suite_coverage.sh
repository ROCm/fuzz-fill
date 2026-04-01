#!/bin/bash

HOME=/home/agorzyns/local/dev
LLVM=$HOME/llvm-project
BUILD_DIR=$LLVM/build-amdgpu
COVERAGE_DIR=/$HOME/fuzz-fill/data/coverage_output/test_suite_full_coverage_010426

# Get opt coverage from already executed tests
  python3 scripts/get_llvm_test_suite_coverage.py \
  --skip-run \
  --binary opt \
  --coverage-dir $COVERAGE_DIR \
  --build-dir "$BUILD_DIR" \
  --cwd "$BUILD_DIR"