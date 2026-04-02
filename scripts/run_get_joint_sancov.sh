#!/bin/bash

set -euo pipefail

LLVM=/home/agorzyns/local/dev/llvm-project
BUILD_DIR=$LLVM/build-amdgpu
COV_DIR=/home/agorzyns/fuzz-fill/data/coverage_output/test_suite_full_coverage_010426

# Tests: ./bin/llvm-lit ../llvm/test/ --filter=CodeGen/AMDGPU (default in script).
# Logic lives in src/coverage/; UBSAN_OPTIONS is set in coverage.runner.TestCommandRunner.
python -m coverage map \
      $COV_DIR/llc.0.symcov $COV_DIR/llc.0.sancov $COV_DIR/opt.0.symcov $COV_DIR/opt.0.sancov \
      --create-joint-sancov