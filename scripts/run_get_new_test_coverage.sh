#!/usr/bin/env bash
# coverage new-tests: writes under <coverage-dir>/new-tests/ (raw sancov in new-tests/raw_sancov/).
# Baseline CSV and line map default to covered_either.csv and llc.0.point_symbol_info.json in the
# coverage parent directory when those flags are omitted.
#
# Optional $1 = --coverage-dir (parent of new-tests/, same as llvm-lit output root). Default:
#   <repo>/data/coverage_output/test_suite_full_coverage
#
# Override: LLVM, BUILD_DIR, TESTS_DIR, PREFIX, etc.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORK_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

LLVM="${LLVM:-$WORK_ROOT/llvm-project}"
BUILD_DIR="${BUILD_DIR:-$LLVM/build-amdgpu}"
TESTS_DIR="${TESTS_DIR:-$WORK_ROOT/irtests/bitcode/amdgpu/all}"
PREFIX="${PREFIX:-$LLVM/llvm/lib/Target/AMDGPU}"

DEFAULT_COV_DIR="$REPO_ROOT/data/coverage_output/test_suite_full_coverage"
COV_DIR="${1:-$DEFAULT_COV_DIR}"

python -m coverage new-tests \
      --coverage-dir "$COV_DIR" \
      --build-dir "$BUILD_DIR" \
      --tests-dir "$TESTS_DIR" \
      --limit 1000 \
      --source-path-prefix "$PREFIX" \
      --novel-line-coverage-level full
