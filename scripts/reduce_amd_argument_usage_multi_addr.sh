#!/bin/bash

BASE=/work/agorzyns/local/dev
FUZZFILL=$BASE/fuzz-fill
OUTPUT_DIR=$FUZZFILL/data/output/amd_argument_usage_multi_addr

mkdir -p "$OUTPUT_DIR"

python3 -m reduce \
    --config $FUZZFILL/example/amd/argument-usage-multi-addr/config.json \
    --llvm-bin $BASE/llvm-project/build/bin \
    --output-dir $OUTPUT_DIR
