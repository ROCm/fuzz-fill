#!/bin/bash
set -euo pipefail

# End-to-end: added-lines -> LIT baseline symcov -> target-lines uncovered list.
# Run from fuzz-fill repo root (same layout as scripts/test_coverage.sh).

HOME=/home/agorzyns/local/dev
FUZZ=$HOME/fuzz-fill
LLVM=$HOME/llvm-project
INSTRUMENTED_BIN_DIR=$LLVM/build-amdgpu-bb/bin
LLVM_BIN=$LLVM/build/bin

OUTPUT_DIR=$FUZZ/data/coverage_output/bb_coverage_target_lines_170626
TEST_SUITE_OUTPUT_DIR=$OUTPUT_DIR/test_suite
ADDED_LINES_DIR=$OUTPUT_DIR/added-lines
TARGET_LINES_REPORT_DIR=$OUTPUT_DIR/target_lines_report

#FILTER="CodeGen/AMDGPU/loop"
FILTER="CodeGen/AMDGPU"

COMMIT=b01fe4e

cd "$FUZZ"

#rm -rf "$TEST_SUITE_OUTPUT_DIR"
mkdir -p "$ADDED_LINES_DIR" "$TARGET_LINES_REPORT_DIR"

# 1) Lines added in COMMIT (same tree as --llvm-repo)
python -m added_lines \
    --llvm-repo "$LLVM" \
    --commit "$COMMIT" \
    --output-dir "$ADDED_LINES_DIR"

# 2) Baseline suite coverage (required symcov under TEST_SUITE_OUTPUT_DIR/processed_sancov/)
python -m coverage test-suite \
    --output-dir "$TEST_SUITE_OUTPUT_DIR" \
    --llvm-bin "$LLVM_BIN" \
    --instrumented-bin "$INSTRUMENTED_BIN_DIR" \
    --lit-filter "$FILTER"

# 3) Target lines not fully covered by the suite (target_lines_uncovered.csv)
python -m coverage target-lines \
    --output-dir "$TARGET_LINES_REPORT_DIR" \
    --test-suite-output-dir "$TEST_SUITE_OUTPUT_DIR" \
    --llvm-repo "$LLVM" \
    --target-lines-csv "$ADDED_LINES_DIR/added-lines.csv"

echo "Uncovered target lines: $TARGET_LINES_REPORT_DIR/target_lines_uncovered.csv"
