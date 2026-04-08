#!/bin/bash
set -euo pipefail
BASE=/work/agorzyns/local/dev
LLVM=$BASE/llvm-project
COV_DIR=$BASE/fuzz-fill/data/coverage_output/test_suite_full_coverage_010426
PREFIX=$LLVM/llvm/lib/Target/AMDGPU

# Gets the line-to-address map for the llc binary from the symcov file.
python -m coverage symcov-line-map \
      $COV_DIR/llc.0.symcov
#      --filter "$PREFIX"

