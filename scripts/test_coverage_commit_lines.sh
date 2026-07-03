#!/bin/bash
set -euo pipefail

# End-to-end: added-lines -> LIT baseline symcov -> target-lines uncovered list.
# Run from fuzz-fill repo root (same layout as scripts/test_coverage.sh).

HOME=/home/agorzyns/local/dev
FUZZ=$HOME/fuzz-fill
LLVM=$HOME/llvm-project
INSTRUMENTED_BIN_DIR=$LLVM/build-amdgpu-bb/bin
LLVM_BIN=$LLVM/build/bin

OUTPUT_DIR=$FUZZ/data/coverage_output/bb_coverage_commit_lines_170626
BASELINE_OUTPUT_DIR=$OUTPUT_DIR/baseline
ADDED_LINES_DIR=$OUTPUT_DIR/added-lines
COMMIT_LINES_REPORT_DIR=$OUTPUT_DIR/commit_lines_report

#FILTER="CodeGen/AMDGPU/loop"
FILTER="CodeGen/AMDGPU"

COMMIT=b01fe4e

cd "$FUZZ"

#rm -rf "$BASELINE_OUTPUT_DIR"
mkdir -p "$ADDED_LINES_DIR" "$COMMIT_LINES_REPORT_DIR"

# 1) Lines added in COMMIT (same tree as --llvm-repo)
python -m added_lines \
    --llvm-repo "$LLVM" \
    --commit "$COMMIT" \
    --output-dir "$ADDED_LINES_DIR"

# 2) Baseline suite coverage (required symcov under BASELINE_OUTPUT_DIR/processed_sancov/)
python -m coverage baseline \
    --output-dir "$BASELINE_OUTPUT_DIR" \
    --llvm-bin "$LLVM_BIN" \
    --instrumented-bin "$INSTRUMENTED_BIN_DIR" \
    --lit-filter "$FILTER"

# 3) Target lines not fully covered by the suite (commit_lines_uncovered.csv)
python -m coverage target-lines \
    --output-dir "$COMMIT_LINES_REPORT_DIR" \
    --baseline-output-dir "$BASELINE_OUTPUT_DIR" \
    --llvm-repo "$LLVM" \
    --target-lines-csv "$ADDED_LINES_DIR/added-lines.csv"

echo "Uncovered added lines: $COMMIT_LINES_REPORT_DIR/commit_lines_uncovered.csv"
