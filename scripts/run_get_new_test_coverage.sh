#!/bin/bash
set -euo pipefail

BASE=/home/agorzyns/local/dev
LLVM=$BASE/llvm-project
BUILD_DIR=$LLVM/build-amdgpu
TESTS_DIR=$BASE/irtests/bitcode/amdgpu/all
COV_DIR=$BASE/fuzz-fill/data/coverage_output/test_suite_full_coverage_010426

# Runs tests and records incremental coverage over a baseline
python -m coverage run \
      --cwd "$BUILD_DIR" \
      --build-dir "$BUILD_DIR" \
      --llc-tests-dir "$TESTS_DIR" \
      --llc-test-limit 1 \
      --llc-baseline-csv "$COV_DIR/covered_either.csv" \
      --llc-line-address-map "$COV_DIR/llc.0.point_symbol_info.json"