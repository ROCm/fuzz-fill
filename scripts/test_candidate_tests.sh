#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${REPO_ROOT}/../llvm-project" && pwd)}"
INSTRUMENTED_BIN_DIR="${INSTRUMENTED_BIN_DIR:-${LLVM_REPO}/build-amdgpu-bb/bin}"
OUTPUT_DIR="${REPO_ROOT}/data/coverage_output/bb_coverage_110526"
CANDIDATE_TESTS_OUTPUT_DIR=$OUTPUT_DIR/candidate_tests
TESTS_DIR="${TESTS_DIR:-${REPO_ROOT}/../irtests/bitcode/amdgpu/all}"

# Clear old output directories
rm -rf $CANDIDATE_TESTS_OUTPUT_DIR

cd "$REPO_ROOT"

python -m coverage candidate-test \
    --output-dir $CANDIDATE_TESTS_OUTPUT_DIR \
    --instrumented-bin $INSTRUMENTED_BIN_DIR \
    --candidate-tests-dir $TESTS_DIR \
    --n 100
