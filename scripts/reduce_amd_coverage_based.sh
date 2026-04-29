#!/bin/bash

BASE=/work/agorzyns/local/dev
FUZZFILL=$BASE/fuzz-fill
OUTPUT_DIR=$FUZZFILL/data/output/amd_new_test_1
mkdir -p "$OUTPUT_DIR"

python3 -m reduce \
    --config $FUZZFILL/example/amd/new-test-1/config.json \
    --llvm-bin $BASE/llvm-project/build/bin \
    --output-dir $OUTPUT_DIR