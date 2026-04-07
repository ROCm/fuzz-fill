#!/bin/bash
set -euo pipefail

COV_DIR=/home/agorzyns/local/dev/fuzz-fill/data/coverage_output/test_suite_full_coverage_010426

# Gets the line-to-address map for the llc binary from the symcov file.
python -m coverage symcov-line-map \
      $COV_DIR/llc.0.symcov
