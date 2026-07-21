#!/bin/bash
set -euo pipefail

# End-to-end: added-lines -> LIT baseline symcov -> target-lines uncovered list.
# Run from fuzz-fill repo root (same layout as scripts/test_coverage.sh).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${REPO_ROOT}/../llvm-project" && pwd)}"
LLVM_BIN="${LLVM_BIN:-${LLVM_REPO}/build/bin}"
INSTRUMENTED_BIN_DIR="${INSTRUMENTED_BIN_DIR:-${LLVM_REPO}/build-amdgpu-bb/bin}"

OUTPUT_DIR="${REPO_ROOT}/data/coverage_output/bb_coverage_commit_lines_170626"
BASELINE_OUTPUT_DIR=$OUTPUT_DIR/baseline
ADDED_LINES_DIR=$OUTPUT_DIR/added-lines
TARGET_LINES_REPORT_DIR=$OUTPUT_DIR/target_lines_report

PATH_FILTER="${PATH_FILTER:-llvm/lib/Target/AMDGPU}"
#FILTER="CodeGen/AMDGPU/loop"
# Faster CodeGen-only subset: FILTER=CodeGen/AMDGPU
FILTER="${FILTER:-(^|/)AMDGPU/}"

COMMIT=b01fe4e

cd "$REPO_ROOT"

#rm -rf "$BASELINE_OUTPUT_DIR"
mkdir -p "$ADDED_LINES_DIR" "$TARGET_LINES_REPORT_DIR"

# 1) Lines added in COMMIT (same tree as --llvm-repo)
python -m added_lines \
    --llvm-repo "$LLVM_REPO" \
    --commit "$COMMIT" \
    --output-dir "$ADDED_LINES_DIR"

# 2) Baseline suite coverage (required symcov under BASELINE_OUTPUT_DIR/processed_sancov/)
python -m coverage baseline \
    --output-dir "$BASELINE_OUTPUT_DIR" \
    --sancov "$LLVM_BIN/sancov" \
    --llvm-lit "$INSTRUMENTED_BIN_DIR/llvm-lit" \
    --llc "$INSTRUMENTED_BIN_DIR/llc" \
    --opt "$INSTRUMENTED_BIN_DIR/opt" \
    --lit-filter "$FILTER" \
    --path-filter "$PATH_FILTER"

# 3) Target lines not fully covered by the suite (target_lines_uncovered.csv)
python -m coverage target-lines \
    --output-dir "$TARGET_LINES_REPORT_DIR" \
    --line-coverage-uncovered-csv "$BASELINE_OUTPUT_DIR/line_coverage_uncovered.csv" \
    --llvm-repo "$LLVM_REPO" \
    --target-lines-csv "$ADDED_LINES_DIR/added-lines.csv"

echo "Uncovered target lines: $TARGET_LINES_REPORT_DIR/target_lines_uncovered.csv"
