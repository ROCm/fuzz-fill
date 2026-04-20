#!/usr/bin/env bash
# coverage analyse on per-test novel-line CSVs.
#
# Optional $1 = coverage output root (same directory passed to new-tests as --coverage-dir).
# The script analyses: $1/new-tests/llc_test_novel_source_lines
#
# Default $1:
#   <repo>/data/coverage_output/test_suite_full_coverage

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

DEFAULT_COV_DIR="$REPO_ROOT/data/coverage_output/test_suite_full_coverage"
COV_PARENT="${1:-$DEFAULT_COV_DIR}"
TEST_DIR="$COV_PARENT/new-tests/llc_test_novel_source_lines"

python -m coverage analyse "$TEST_DIR"
