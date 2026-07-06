#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${REPO_ROOT}/../llvm-project" && pwd)}"
LLVM_BIN="${LLVM_BIN:-${LLVM_REPO}/build/bin}"
OUTPUT_DIR="${REPO_ROOT}/data/output/amd_argument_usage_multi_addr"

mkdir -p "$OUTPUT_DIR"

cd "$REPO_ROOT"

python3 -m reduce \
    --config "$REPO_ROOT/example/amd/argument-usage-multi-addr/config.json" \
    --llvm-bin "$LLVM_BIN" \
    --output-dir "$OUTPUT_DIR"
