#!/bin/bash

set -euo pipefail

HOME=/work/agorzyns/local/dev
LLVM=$HOME/llvm-project
BUILD_DIR=$LLVM/build-amdgpu
COV_DIR=$HOME/fuzz-fill/data/coverage_output/test_suite_full_bb_coverage_200426

# Tests: ./bin/llvm-lit ../llvm/test/ --filter=CodeGen/AMDGPU (default in script).
# Logic lives in src/coverage/; UBSAN_OPTIONS is set in coverage.runner.TestCommandRunner.
python -m coverage map \
      "$COV_DIR/llc.0.symcov" \
      "$COV_DIR/llc.0.sancov" \
      "$COV_DIR/opt.0.symcov" \
      "$COV_DIR/opt.0.sancov" \
      --create-joint-sancov \
      --joint-file-prefix "$LLVM/llvm/lib/Target/AMDGPU" \
      --joint-csv "$COV_DIR/covered_either.csv"