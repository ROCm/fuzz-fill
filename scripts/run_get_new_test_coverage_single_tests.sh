#!/usr/bin/env bash
# new-tests with --limit 1. Optional $1 = --coverage-dir parent (default: test_suite_full_coverage).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORK_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

LLVM="${LLVM:-$WORK_ROOT/llvm-project}"
BUILD_DIR="${BUILD_DIR:-$LLVM/build-amdgpu}"
TESTS_DIR="${TESTS_DIR:-$REPO_ROOT/data/coverage_output/row8_check}"
PREFIX="${PREFIX:-$LLVM/llvm/lib/Target/AMDGPU}"

DEFAULT_COV_DIR="$REPO_ROOT/data/coverage_output/test_suite_full_coverage"
COV_DIR="${1:-$DEFAULT_COV_DIR}"

python -m coverage new-tests \
      --coverage-dir "$COV_DIR" \
      --build-dir "$BUILD_DIR" \
      --tests-dir "$TESTS_DIR" \
      --limit 1 \
      --source-path-prefix "$PREFIX" \
      --novel-line-coverage-level full
