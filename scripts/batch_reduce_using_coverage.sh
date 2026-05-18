#!/bin/bash
set -euo pipefail

BASE=/work/agorzyns/local/dev
FUZZFILL=$BASE/fuzz-fill
COVERAGE_OUTPUT=$FUZZFILL/data/coverage_output/bb_coverage_180526

TESTS_TO_REDUCE=$COVERAGE_OUTPUT/diff/new_coverage_filtered_cpp_sample.csv
NEW_TESTS_DIR=$COVERAGE_OUTPUT/new_tests
OUTPUT_DIR=$FUZZFILL/data/output/reduced_180526_AMDGPUMCInstLower
LLVM_BIN=$BASE/llvm-project/build/bin

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
cd "$FUZZFILL"

python3 scripts/batch_reduce_using_coverage.py \
  --csv "$TESTS_TO_REDUCE" \
  --new-tests "$NEW_TESTS_DIR" \
  --output "$OUTPUT_DIR" \
  --llvm-bin "$LLVM_BIN" \
  --n 42
