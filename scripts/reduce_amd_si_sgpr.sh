#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${REPO_ROOT}/../llvm-project" && pwd)}"
LLVM_BIN="${LLVM_BIN:-${LLVM_REPO}/build/bin}"

cd "$REPO_ROOT"

python3 -m reduce \
    --config "$REPO_ROOT/example/amd/si-sgpr-spills/config.json" \
    --llc "$LLVM_BIN/llc" \
    --llvm-reduce "$LLVM_BIN/llvm-reduce"
