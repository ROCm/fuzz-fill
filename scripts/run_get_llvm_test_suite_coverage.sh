#!/bin/bash
set -euo pipefail

LLVM=/home/agorzyns/local/dev/llvm-project
BUILD_DIR=$LLVM/build-amdgpu

# Tests: ./bin/llvm-lit ../llvm/test/ --filter=CodeGen/AMDGPU (default in script).
# UBSAN_OPTIONS for coverage is set inside get_llvm_test_suite_coverage.py.

python3 scripts/get_llvm_test_suite_coverage.py \
  --cwd "$BUILD_DIR" \
  --build-dir "$BUILD_DIR"
