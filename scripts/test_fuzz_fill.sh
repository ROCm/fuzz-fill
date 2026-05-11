#!/bin/bash
set -euo pipefail

HOME=/home/agorzyns/local/dev
LLVM_BUILD_DIR=$HOME/llvm-project/build/bin/
LLVM_SANCOV_BUILD_DIR=$HOME/llvm-project/build-amdgpu-bb/bin/

./integration-tests/test.sh \
  --venv ./venv/ \
  --llvm-build $LLVM_BUILD_DIR \
  --llvm-sancov-build $LLVM_SANCOV_BUILD_DIR \
  integration-tests/