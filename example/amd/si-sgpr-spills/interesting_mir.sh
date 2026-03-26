#!/bin/bash
# Interesting-ness for llvm-reduce -x=mir: $1 is a candidate .mir file.
# Adjust LLVM_BIN and llc flags to match your tree / triple.

LLVM_BIN=/home/agorzyns/local/dev/llvm-project/build/bin
LLC=$LLVM_BIN/llc

output=$($LLC -verify-machineinstrs -mtriple=amdgcn-amd-amdhsa -run-pass=si-lower-sgpr-spills "$1" 2>&1)

exitcode=$?

echo "$output"

if echo "$output" | awk '/PLEASE submit a bug report/{p1=1} /My crash is here/{p2=1} END{exit !(p1&&p2)}'; then
  exit 0
fi
exit 1
