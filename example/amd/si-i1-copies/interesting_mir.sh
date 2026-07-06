#!/bin/bash
# Interesting-ness for llvm-reduce -x=mir: $1 is a candidate .mir file.
# Override LLVM_BIN or llc flags to match your tree / triple.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
LLVM_BIN="${LLVM_BIN:-${REPO_ROOT}/../llvm-project/build/bin}"
LLC=$LLVM_BIN/llc

output=$($LLC -verify-machineinstrs -mtriple=amdgcn-amd-amdhsa -run-pass=si-i1-copies "$1" 2>&1)

exitcode=$?

echo "$output"

if echo "$output" | awk '/PLEASE submit a bug report/{p1=1} /My crash is here/{p2=1} END{exit !(p1&&p2)}'; then
  exit 0
fi
exit 1
