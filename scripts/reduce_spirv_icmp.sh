#!/bin/bash

BASE=/work/agorzyns/local/dev
FUZZFILL=$BASE/fuzz-fill

# Reduce the test that covers line 2360 of SPIRVInstructionSelector.cpp
python3 -m reduce \
    fuzzer-tests/spirv/llc.real.37.ll \
    $BASE/llvm-project/build-spirv/bin/llc \
    --interesting $FUZZFILL/fuzzer-tests/spirv/interesting.py \
    --output_dir $FUZZFILL/data/output/spirv_icmp_37 \
    --file llvm/lib/Target/SPIRV/SPIRVInstructionSelector.cpp \
    --line 2360 