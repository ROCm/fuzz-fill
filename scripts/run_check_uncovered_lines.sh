#!/bin/bash

BASE=/work/agorzyns/local/dev
LLVM=$BASE/llvm-project
BUILD_DIR=$LLVM/build
COV_DIR=$BASE/fuzz-fill/data/coverage_output/new_tests_1775642180
ENRICHED_CSV=$COV_DIR/analyse_stacked_novel_lines/all_novel_source_lines_with_original_and_replacement.csv

python -m coverage check-uncovered \
    --csv $ENRICHED_CSV \
    --llvm-build $BUILD_DIR