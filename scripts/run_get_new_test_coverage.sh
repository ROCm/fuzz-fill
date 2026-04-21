#!/bin/bash
set -euo pipefail

BASE=/work/agorzyns/local/dev
LLVM=$BASE/llvm-project
BUILD_DIR=$LLVM/build-amdgpu-bb
TESTS_DIR=$BASE/irtests/bitcode/amdgpu/all
COV_DIR=$BASE/fuzz-fill/data/coverage_output/test_suite_full_bb_coverage_200426
PREFIX=$LLVM/llvm/lib/Target/AMDGPU

# Runs new llc inputs; per-test addresses via sancov --print (no merge/symbolize)
python -m coverage new-tests \
      --build-dir "$BUILD_DIR" \
      --tests-dir "$TESTS_DIR" \
      --limit 1000 \
      --baseline-csv "$COV_DIR/covered_either.csv" \
      --line-address-map "$COV_DIR/llc.0.point_symbol_info.json" \
      --source-path-prefix "$PREFIX" \
      --novel-line-coverage-level full