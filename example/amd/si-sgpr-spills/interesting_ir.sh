#!/bin/bash

LLVM_BIN=/home/agorzyns/local/dev/llvm-project/build/bin

LLC=$LLVM_BIN/llc

output=$($LLC -O0 "$1" 2>&1)

exitcode=$?

echo "$output"

# Interesting
if echo "$output" | awk '/PLEASE submit a bug report/{p1=1} /My crash is here/{p2=1} END{exit !(p1&&p2)}'; then
  exit 0 
fi

# Not interesting
exit 1