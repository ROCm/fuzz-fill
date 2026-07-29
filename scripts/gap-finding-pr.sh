#!/usr/bin/env bash
# Gap finding (PR-specific): added_lines -> baseline -> target-lines.
#
# Produces commit_lines_report/target_lines_uncovered.csv — added source lines
# the baseline still does not cover. Run from fuzz-fill repo root.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${REPO_ROOT}/../llvm-project" && pwd)}"
LLVM_BIN="${LLVM_BIN:-${LLVM_REPO}/build/bin}"
INSTRUMENTED_BIN_DIR="${INSTRUMENTED_BIN_DIR:-${LLVM_REPO}/build-amdgpu-bb/bin}"

OUTPUT_DIR="${REPO_ROOT}/data/coverage_output/bb_coverage_commit_lines_170626"
BASELINE_OUTPUT_DIR=$OUTPUT_DIR/baseline
ADDED_LINES_DIR=$OUTPUT_DIR/added-lines
TARGET_LINES_REPORT_DIR=$OUTPUT_DIR/commit_lines_report

# Faster CodeGen-only subset: FILTER=CodeGen/AMDGPU
FILTER="${FILTER:-AMDGPU}"

COMMIT=b01fe4e

cd "$REPO_ROOT"

mkdir -p "$ADDED_LINES_DIR" "$TARGET_LINES_REPORT_DIR"

python -m added_lines \
    --llvm-repo "$LLVM_REPO" \
    --commit "$COMMIT" \
    --output-dir "$ADDED_LINES_DIR"

python -m coverage baseline \
    --output-dir "$BASELINE_OUTPUT_DIR" \
    --sancov "$LLVM_BIN/sancov" \
    --llvm-lit "$INSTRUMENTED_BIN_DIR/llvm-lit" \
    --llc "$INSTRUMENTED_BIN_DIR/llc" \
    --opt "$INSTRUMENTED_BIN_DIR/opt" \
    --lit-filter "$FILTER"

python -m coverage target-lines \
    --output-dir "$TARGET_LINES_REPORT_DIR" \
    --line-coverage-uncovered-csv "$BASELINE_OUTPUT_DIR/line_coverage_uncovered.csv" \
    --llvm-repo "$LLVM_REPO" \
    --target-lines-csv "$ADDED_LINES_DIR/added-lines.csv"

echo "Uncovered PR target lines: $TARGET_LINES_REPORT_DIR/target_lines_uncovered.csv"
