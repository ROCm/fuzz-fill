#!/bin/bash

BASE=/work/agorzyns/local/dev
TEST_DIR=$BASE/fuzz-fill/data/coverage_output/new_tests_1775743874/llc_test_novel_source_lines

python -m coverage analyse $TEST_DIR