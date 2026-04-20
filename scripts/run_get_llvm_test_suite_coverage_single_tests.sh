#!/usr/bin/env bash
# Single lit filter run. Optional $1 = --coverage-dir (see run_get_llvm_test_suite_coverage.sh).
# With no arguments, --coverage-dir is omitted (timestamped default folder).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORK_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

LLVM="${LLVM:-$WORK_ROOT/llvm-project}"
BUILD_DIR="${BUILD_DIR:-$LLVM/build-amdgpu}"

COV_DIR_ARG="${1:-}"

if [[ -n "$COV_DIR_ARG" ]]; then
  python -m coverage run \
        --cwd "$BUILD_DIR" \
        --build-dir "$BUILD_DIR" \
        --filter "CodeGen/AMDGPU/lro-phi-samebb-nonlookthrough-store" \
        --coverage-dir "$COV_DIR_ARG"
else
  python -m coverage run \
        --cwd "$BUILD_DIR" \
        --build-dir "$BUILD_DIR" \
        --filter "CodeGen/AMDGPU/lro-phi-samebb-nonlookthrough-store"
fi
