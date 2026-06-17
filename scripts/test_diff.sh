#!/bin/bash
set -euo pipefail

HOME=/home/agorzyns/local/dev
LLVM=$HOME/llvm-project
OUTPUT_DIR=$HOME/fuzz-fill/data/diff_output/bb_diff_090626
COMMIT=12b775409b1a0c238c3c1c5c0c270d0af23a1852

# Clear old output directory
rm -rf $OUTPUT_DIR

python -m diff added-lines \
    --output-dir $OUTPUT_DIR \
    --llvm-repo $LLVM \
    --commit $COMMIT
