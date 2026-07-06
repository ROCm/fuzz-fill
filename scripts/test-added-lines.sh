#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${REPO_ROOT}/../llvm-project" && pwd)}"
OUTPUT_DIR="${REPO_ROOT}/data/added-lines-output/bb-added-lines_090626"
COMMIT=b01fe4e

# Clear old output directory
rm -rf $OUTPUT_DIR

cd "$REPO_ROOT"

python -m added_lines \
    --output-dir $OUTPUT_DIR \
    --llvm-repo $LLVM_REPO \
    --commit $COMMIT
