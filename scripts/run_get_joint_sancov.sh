#!/usr/bin/env bash
# Joint llc/opt CSV from merged symcov/sancov under the coverage output root.
#
# Optional $1 = coverage output directory (parent of llc.0.symcov, etc.). Default:
#   <repo>/data/coverage_output/test_suite_full_coverage
#
# Override: LLVM (for --joint-file-prefix), BUILD_DIR unused here.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORK_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

LLVM="${LLVM:-$WORK_ROOT/llvm-project}"
DEFAULT_COV_DIR="$REPO_ROOT/data/coverage_output/test_suite_full_coverage"
COV_DIR="${1:-$DEFAULT_COV_DIR}"

python -m coverage map \
      "$COV_DIR/llc.0.symcov" \
      "$COV_DIR/llc.0.sancov" \
      "$COV_DIR/opt.0.symcov" \
      "$COV_DIR/opt.0.sancov" \
      --create-joint-sancov \
      --joint-file-prefix "$LLVM/llvm/lib/Target/AMDGPU" \
      --joint-csv "$COV_DIR/covered_either.csv"
