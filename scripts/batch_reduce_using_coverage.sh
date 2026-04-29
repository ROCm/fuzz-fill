#!/bin/bash
set -euo pipefail

BASE=/work/agorzyns/local/dev
FUZZFILL=$BASE/fuzz-fill
COVERAGE_OUTPUT=$FUZZFILL/data/coverage_output/bb_coverage_270426

TESTS_TO_REDUCE=$COVERAGE_OUTPUT/diff/new_coverage.csv

TESTS_DIR=$BASE/irtests/bitcode/amdgpu/all
OUTPUT_DIR=$FUZZFILL/data/output/reduce_using_coverage_00
LLVM_BIN=$BASE/llvm-project/build/bin

mkdir -p "$OUTPUT_DIR"
cd "$FUZZFILL"

python3 scripts/batch_reduce_using_coverage.py \
  --csv "$TESTS_TO_REDUCE" \
  --tests-base "$TESTS_DIR" \
  --output "$OUTPUT_DIR" \
  --llvm-bin "$LLVM_BIN"