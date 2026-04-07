#!/bin/bash
set -euo pipefail

BASE=/home/agorzyns/local/dev
LLVM=$BASE/llvm-project
BUILD_DIR=$LLVM/build-amdgpu
TESTS_DIR=$BASE/irtests/bitcode/amdgpu/all

# Tests: ./bin/llvm-lit ../llvm/test/ --filter=CodeGen/AMDGPU (default in script).
# Logic lives in src/coverage/; UBSAN_OPTIONS is set in coverage.runner.TestCommandRunner.
python -m coverage run \
      --cwd "$BUILD_DIR" \
      --build-dir "$BUILD_DIR" \
      --llc-tests-dir "$TESTS_DIR" \
      --llc-test-limit 1