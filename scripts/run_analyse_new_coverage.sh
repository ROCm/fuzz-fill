#!/bin/bash

BASE=/work/agorzyns/local/dev
TEST_DIR=$BASE/fuzz-fill/data/coverage_output/new_tests_1776687848_bb_coverage_200426/llc_test_novel_source_lines

python -m coverage analyse $TEST_DIR