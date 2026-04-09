#!/bin/bash
set -euo pipefail

BASE=/work/agorzyns/local/dev
LLVM=$BASE/llvm-project
BUILD_DIR=$LLVM/build-amdgpu
TESTS_DIR=$BASE/irtests/bitcode/amdgpu/all
COV_DIR=$BASE/fuzz-fill/data/coverage_output/test_suite_full_coverage_010426
SANCOV_DIR=$BASE/fuzz-fill/data/coverage_output/new_tests_1775642180
PREFIX=$LLVM/llvm/lib/Target/AMDGPU

# Runs new llc inputs; per-test addresses via sancov --print (no merge/symbolize)
python -m coverage new-tests \
      --build-dir "$BUILD_DIR" \
      --tests-dir "$TESTS_DIR" \
      --limit 998 \
      --baseline-csv "$COV_DIR/covered_either.csv" \
      --line-address-map "$COV_DIR/llc.0.point_symbol_info.json" \
      --source-path-prefix "$PREFIX" \
      --existing-sancov-dir "$SANCOV_DIR" \
      --novel-line-coverage-level full