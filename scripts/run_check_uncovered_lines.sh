#!/usr/bin/env bash
# Optional $1 = coverage output root (parent of new-tests/). Default:
#   <repo>/data/coverage_output/test_suite_full_coverage
#
# Override: LLVM, BUILD_DIR

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORK_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

LLVM="${LLVM:-$WORK_ROOT/llvm-project}"
BUILD_DIR="${BUILD_DIR:-$LLVM/build}"

DEFAULT_COV_PARENT="$REPO_ROOT/data/coverage_output/test_suite_full_coverage"
COV_PARENT="${1:-$DEFAULT_COV_PARENT}"
COV_DIR="$COV_PARENT/new-tests"
ENRICHED_CSV=$COV_DIR/llc_test_novel_source_lines/analyse_stacked_novel_lines/all_novel_source_lines_original_and_replacement.csv

python -m coverage check-uncovered \
    "$ENRICHED_CSV" \
    "$BUILD_DIR" \
    --resume
