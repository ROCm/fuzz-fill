#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${REPO_ROOT}/../llvm-project" && pwd)}"
LLVM_BIN="${LLVM_BIN:-${LLVM_REPO}/build/bin}"
DATA_DIR="${REPO_ROOT}/data"

TESTS_TO_REDUCE=$DATA_DIR/siinstrinfo/siinstrinfo_new_coverage.csv
CANDIDATE_TESTS_DIR=$DATA_DIR/siinstrinfo
OUTPUT_DIR=$DATA_DIR/output/reduced_090626_siinstrinfo

N_FILES=4

# IR coverage reduction, then creduce on the llvm-reduce .ll output:
# PIPELINE=llvm_reduce_ir,creduce
# Or append creduce without listing it in PIPELINE:
# PIPELINE=llvm_reduce_ir
# WITH_CREDUCE=1
# CREDUCE_N=8

# MIR extract / reduce (llvm-reduce -x=mir fails on pre-isel MIR; use creduce on .mir
# after extract if needed, or skip MIR steps):
PIPELINE=extract_mir_before_pass,llvm_reduce_mir,creduce
PASS_UNDER_TEST=si-fix-sgpr-copies
MTRIPLE=amdgcn-amd-amdhsa
EXTRACT_MIR_OUTPUT=before-si-fix-sgpr-copies.mir
#MIR_CODEGEN_ONLY=1

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
cd "$REPO_ROOT"

EXTRA_ARGS=()
if [[ -n "${PIPELINE:-}" ]]; then
  EXTRA_ARGS+=(--pipeline "$PIPELINE")
fi
if [[ -n "${WITH_CREDUCE:-}" ]]; then
  EXTRA_ARGS+=(--with-creduce)
fi
if [[ -n "${CREDUCE_N:-}" ]]; then
  EXTRA_ARGS+=(--creduce-n "$CREDUCE_N")
fi
if [[ -n "${PASS_UNDER_TEST:-}" ]]; then
  EXTRA_ARGS+=(--pass-under-test "$PASS_UNDER_TEST")
fi
if [[ -n "${MTRIPLE:-}" ]]; then
  EXTRA_ARGS+=(--mtriple "$MTRIPLE")
fi
if [[ -n "${EXTRACT_MIR_OUTPUT:-}" ]]; then
  EXTRA_ARGS+=(--extract-mir-output "$EXTRACT_MIR_OUTPUT")
fi
if [[ -n "${MIR_CODEGEN_ONLY:-}" ]]; then
  EXTRA_ARGS+=(--mir-codegen-only)
fi

python3 scripts/batch_reduce_using_coverage.py \
  --csv "$TESTS_TO_REDUCE" \
  --candidate-tests "$CANDIDATE_TESTS_DIR" \
  --output "$OUTPUT_DIR" \
  --llc "$LLVM_BIN/llc" \
  --llvm-reduce "$LLVM_BIN/llvm-reduce" \
  --n $N_FILES \
  "${EXTRA_ARGS[@]}"
