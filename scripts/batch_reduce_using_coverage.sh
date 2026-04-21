#!/bin/bash
set -euo pipefail

BASE=/work/agorzyns/local/dev
FUZZFILL=$BASE/fuzz-fill
NEW_TESTS_COV=$FUZZFILL/data/coverage_output/new_tests_1776687848_bb_coverage_200426
TEST_SUITE_COV=$FUZZFILL/data/coverage_output/test_suite_full_bb_coverage_200426

TESTS_TO_REDUCE=$NEW_TESTS_COV/llc_test_novel_source_lines/analyse_stacked_novel_lines/all_novel_source_lines.csv
SYMBOL_JSON=$TEST_SUITE_COV/llc.0.point_symbol_info.json

TESTS_DIR=$BASE/irtests/bitcode/amdgpu/all
OUTPUT_DIR=$FUZZFILL/data/output/reduce_using_coverage_00
LLVM_BIN=$BASE/llvm-project/build/bin

mkdir -p "$OUTPUT_DIR"
cd "$FUZZFILL"

python3 scripts/batch_reduce_using_coverage.py \
  --csv "$TESTS_TO_REDUCE" \
  --tests-base "$TESTS_DIR" \
  --symbol-json "$SYMBOL_JSON" \
  --output "$OUTPUT_DIR" \
  --llvm-bin "$LLVM_BIN"