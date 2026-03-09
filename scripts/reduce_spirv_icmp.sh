#!/bin/bash

BASE=/homes/agorzyns/local/dev
FUZZFILL=$BASE/fuzz-fill

# Reduce the test that covers line 2360 of SPIRVInstructionSelector.cpp
python3 -m reduce \
    fuzzer-tests/spirv/llc.real.37.ll \
    $BASE/llvm-project/build-spirv/bin/llc \
    --interesting $FUZZFILL/fuzzer-tests/spirv/interesting.py \
    --output_dir $FUZZFILL/data/output/spirv_icmp_37 \
    --line 2360 \
    --symcov $FUZZFILL/data/coverage_output/spirv_170309-120000/llc.real.37.ll.symcov