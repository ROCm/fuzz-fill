#!/bin/bash
set -euo pipefail

HOME=/home/agorzyns/local/dev
LLVM=$HOME/llvm-project
BUILD_DIR=$LLVM/build-amdgpu-bb
COVERAGE_DIR=$HOME/fuzz-fill/data/coverage_output/test_suite_full_bb_coverage_200426

# Tests: ./bin/llvm-lit ../llvm/test/ --filter=CodeGen/AMDGPU (default in script).
# Logic lives in src/coverage/; UBSAN_OPTIONS is set in coverage.runner.TestCommandRunner.
python -m coverage run \
      --cwd "$BUILD_DIR" \
      --build-dir "$BUILD_DIR" \
      --filter "CodeGen/AMDGPU" \
      --coverage-dir $COVERAGE_DIR