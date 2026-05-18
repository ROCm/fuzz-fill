#!/bin/bash
set -euo pipefail

BASE=/work/agorzyns/local/dev
FUZZFILL=$BASE/fuzz-fill
COVERAGE_OUTPUT=$FUZZFILL/data/coverage_output/bb_coverage_180526

TESTS_TO_REDUCE=$COVERAGE_OUTPUT/diff/new_coverage.csv
NEW_TESTS_DIR=$COVERAGE_OUTPUT/new_tests
OUTPUT_DIR=$FUZZFILL/data/output/reduce_using_coverage_00
LLVM_BIN=$BASE/llvm-project/build-amdgpu-bb/bin

mkdir -p "$OUTPUT_DIR"
cd "$FUZZFILL"

python3 scripts/batch_reduce_using_coverage.py \
  --csv "$TESTS_TO_REDUCE" \
  --new-tests "$NEW_TESTS_DIR" \
  --output "$OUTPUT_DIR" \
  --llvm-bin "$LLVM_BIN"
