#!/bin/bash
set -euo pipefail

LLVM=/home/agorzyns/local/dev/llvm-project
BUILD_DIR=$LLVM/build-amdgpu

# Tests: ./bin/llvm-lit ../llvm/test/ --filter=CodeGen/AMDGPU (default in script).
# Logic lives in src/coverage/; UBSAN_OPTIONS is set in coverage.runner.TestCommandRunner.
python -m coverage run \
      --cwd "$BUILD_DIR" \
      --build-dir "$BUILD_DIR" \
      --filter "CodeGen/AMDGPU"