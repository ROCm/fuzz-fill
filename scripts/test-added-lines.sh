#!/bin/bash
set -euo pipefail

HOME=/home/agorzyns/local/dev
LLVM=$HOME/llvm-project
OUTPUT_DIR=$HOME/fuzz-fill/data/added-lines-output/bb-added-lines_090626
COMMIT=b01fe4e

# Clear old output directory
rm -rf $OUTPUT_DIR

python -m added_lines \
    --output-dir $OUTPUT_DIR \
    --llvm-repo $LLVM \
    --commit $COMMIT
