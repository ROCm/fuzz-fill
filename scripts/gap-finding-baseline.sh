#!/usr/bin/env bash
# Gap finding (baseline): run coverage baseline over a filtered LIT slice.
#
# Produces line_coverage_uncovered.csv and llc_address_line_map.csv under
# <output-dir>/baseline/. Use scripts/gap-filling-amdgpu.sh (or gap-filling Docker)
# to find fuzz tests that cover those gaps.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${REPO_ROOT}/../llvm-project" && pwd)}"
LLVM_BIN="${LLVM_BIN:-${LLVM_REPO}/build/bin}"
INSTRUMENTED_BIN_DIR="${INSTRUMENTED_BIN_DIR:-${LLVM_REPO}/build-amdgpu-bb/bin}"
OUTPUT_DIR="${REPO_ROOT}/data/coverage_output/bb_coverage_amdgpu_230726_full_filter"
BASELINE_OUTPUT_DIR=$OUTPUT_DIR/baseline

FILTER="${FILTER:-AMDGPU}"

rm -rf "$BASELINE_OUTPUT_DIR"

cd "$REPO_ROOT"

python -m coverage baseline \
    --output-dir "$BASELINE_OUTPUT_DIR" \
    --sancov "$LLVM_BIN/sancov" \
    --llvm-lit "$INSTRUMENTED_BIN_DIR/llvm-lit" \
    --llc "$INSTRUMENTED_BIN_DIR/llc" \
    --opt "$INSTRUMENTED_BIN_DIR/opt" \
    --lit-filter "$FILTER" \
    --lit-allow-failures

echo "Uncovered baseline lines: $BASELINE_OUTPUT_DIR/line_coverage_uncovered.csv"
