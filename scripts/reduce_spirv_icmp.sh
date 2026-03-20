#!/bin/bash

BASE=/work/agorzyns/local/dev
FUZZFILL=$BASE/fuzz-fill

python3 -m reduce \
    example/config.json \
    $BASE/llvm-project/build-spirv/bin/llc