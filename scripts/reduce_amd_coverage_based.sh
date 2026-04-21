#!/bin/bash

BASE=/work/agorzyns/local/dev
FUZZFILL=$BASE/fuzz-fill

python3 -m reduce \
    --config $FUZZFILL/example/amd/new-test-1/config.json \
    --llvm-bin $BASE/llvm-project/build/bin