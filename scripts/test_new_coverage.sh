#!/bin/bash
set -euo pipefail

HOME=/home/agorzyns/local/dev
LLVM=$HOME/llvm-project
BUILD_DIR=$LLVM/build-amdgpu-bb
COVERAGE_DIR=$HOME/fuzz-fill/data/coverage_output/test_suite_full_bb_coverage_240426

python -m cov_new test-suite 

python -m cov_new new-tests

python -m cov_new diff 