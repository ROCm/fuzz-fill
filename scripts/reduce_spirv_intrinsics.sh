#!/bin/bash

BASE=/work/agorzyns/local/dev
FUZZFILL=$BASE/fuzz-fill

python3 -m reduce \
    --config $FUZZFILL/example/spirv/emit-intrinsics/config.json \
    --llvm-bin $BASE/llvm-project/build/bin