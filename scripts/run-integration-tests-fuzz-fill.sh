#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

LLVM_REPO="${REPO_ROOT}/llvm-project-22.1.8"
LLVM_COVERAGE_BUILD="${LLVM_REPO}/build-coverage"
LLVM_SANCOV_BUILD_BIN="${LLVM_REPO}/build-sancov/bin"
HOST_BIN="/COD/LATEST/trunk/bin"

cd "$REPO_ROOT"

./integration-tests/test.sh \
  --venv "${REPO_ROOT}/venv" \
  --llvm-build "${LLVM_SANCOV_BUILD_BIN}" \
  --llvm-coverage-build "${LLVM_COVERAGE_BUILD}" \
  --llvm-sancov-build "${LLVM_SANCOV_BUILD_BIN}" \
  --host-bin "${HOST_BIN}" \
  --llvm-src "${LLVM_REPO}" \
  integration-tests/ \
  "$@"
