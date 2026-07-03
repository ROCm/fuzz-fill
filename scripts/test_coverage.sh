#!/bin/bash
set -euo pipefail

HOME=/home/agorzyns/local/dev
LLVM=$HOME/llvm-project
INSTRUMENTED_BIN_DIR=$LLVM/build-amdgpu-bb/bin
LLVM_BIN=$LLVM/build/bin
OUTPUT_DIR=$HOME/fuzz-fill/data/coverage_output/bb_coverage_090626
BASELINE_OUTPUT_DIR=$OUTPUT_DIR/baseline
CANDIDATE_TESTS_OUTPUT_DIR=$OUTPUT_DIR/candidate_tests
INCREMENTAL_OUTPUT_DIR=$OUTPUT_DIR/incremental
TESTS_DIR=$HOME/irtests/bitcode/amdgpu/all

#FILTER="CodeGen/AMDGPU/loop" # Small set of tests featuring both llc and opt for testing
FILTER="CodeGen/AMDGPU" # All tests

# Clear old output directories
rm -rf $BASELINE_OUTPUT_DIR
#rm -rf $CANDIDATE_TESTS_OUTPUT_DIR
#rm -rf $INCREMENTAL_OUTPUT_DIR

python -m coverage baseline \
    --output-dir $BASELINE_OUTPUT_DIR \
    --llvm-bin $LLVM_BIN \
    --instrumented-bin $INSTRUMENTED_BIN_DIR \
    --lit-filter $FILTER 

#python -m coverage candidate-test \
#    --output-dir $CANDIDATE_TESTS_OUTPUT_DIR \
#    --instrumented-bin $INSTRUMENTED_BIN_DIR \
#    --candidate-tests-dir $TESTS_DIR \
#    --n 1000

# python -m coverage incremental \
#    --output-dir $INCREMENTAL_OUTPUT_DIR \
#    --llvm-bin $LLVM_BIN \
#    --baseline-output-dir $BASELINE_OUTPUT_DIR \
#    --candidate-tests-output-dir $CANDIDATE_TESTS_OUTPUT_DIR

