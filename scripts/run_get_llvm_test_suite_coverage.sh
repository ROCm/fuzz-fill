#!/usr/bin/env bash
# llvm-lit + merge/symbolize. Optional $1 = absolute path for --coverage-dir (directory is created).
# With no arguments, --coverage-dir is omitted and the CLI picks data/coverage_output/test_suite_<timestamp>/.
#
# Override defaults: LLVM, BUILD_DIR (see below).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORK_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

LLVM="${LLVM:-$WORK_ROOT/llvm-project}"
BUILD_DIR="${BUILD_DIR:-$LLVM/build-amdgpu}"

COV_DIR_ARG="${1:-}"

# Tests: ./bin/llvm-lit ../llvm/test/ --filter=CodeGen/AMDGPU (default in script).
# UBSAN raw .sancov: <coverage-dir>/raw_sancov/ (see src/coverage/session.py).
if [[ -n "$COV_DIR_ARG" ]]; then
  python -m coverage run \
        --cwd "$BUILD_DIR" \
        --build-dir "$BUILD_DIR" \
        --filter "CodeGen/AMDGPU" \
        --coverage-dir "$COV_DIR_ARG"
else
  python -m coverage run \
        --cwd "$BUILD_DIR" \
        --build-dir "$BUILD_DIR" \
        --filter "CodeGen/AMDGPU"
fi
