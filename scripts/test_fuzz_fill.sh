#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${REPO_ROOT}/../llvm-project" && pwd)}"
LLVM_BUILD_DIR="${LLVM_BIN:-${LLVM_REPO}/build/bin}/"
LLVM_SANCOV_BUILD_DIR="${INSTRUMENTED_BIN_DIR:-${LLVM_REPO}/build-amdgpu-bb/bin}/"

cd "$REPO_ROOT"

./integration-tests/test.sh \
  --venv ./venv/ \
  --llvm-build $LLVM_BUILD_DIR \
  --llvm-sancov-build $LLVM_SANCOV_BUILD_DIR \
  --llvm-src $LLVM_REPO \
  integration-tests/
