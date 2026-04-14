#!/bin/bash

BASE=/work/agorzyns/local/dev
LLVM=$BASE/llvm-project
BUILD_DIR=$LLVM/build
COV_DIR=$BASE/fuzz-fill/data/coverage_output/new_tests_1775743874
ENRICHED_CSV=$COV_DIR/llc_test_novel_source_lines/analyse_stacked_novel_lines/all_novel_source_lines_original_and_replacement.csv

python -m coverage check-uncovered \
    $ENRICHED_CSV \
    $BUILD_DIR \
    --resume
