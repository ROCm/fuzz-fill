from __future__ import annotations

import argparse
import secrets
import sys
import time
from pathlib import Path

from cov_new.filepaths import Filepaths

from cov_new.constants import (
    CSV_FILE_NAME_COVERED,
    DEFAULT_OUTPUT_DIR,
)

def main():

    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(
        dest="subcmd",
        metavar="{test-suite,new-tests,diff}",
        required=True,
    )
    p_test_suite = sub.add_parser("test-suite")
    p_new_tests = sub.add_parser("new-tests")
    p_diff = sub.add_parser("diff")

    add_shared_arguments(p_test_suite)
    add_shared_arguments(p_new_tests)
    add_shared_arguments(p_diff)

    add_llvm_arguments(p_test_suite)
    add_llvm_arguments(p_new_tests)

    p_new_tests.add_argument("--new-tests-dir", type=Path, required=True,
        help="Directory containing the new tests (.ll/.bc).")
    p_new_tests.add_argument("--n", type=int, default=1, 
        help="Number of new tests to process (.ll/.bc, sorted path order).")

    p_diff.add_argument("--baseline-csv", type=Path, default=CSV_FILE_NAME_COVERED,
        help="Baseline CSV file (file,function,line,llc_addresses as JSON array per row).")

    args = parser.parse_args()

    filepaths = get_filepaths(args)

    if args.subcmd == "test-suite":
        print("Getting baseline coverage for the test suite")
        print(filepaths)
    elif args.subcmd == "new-tests":
        print("Getting coverage for the new tests")
        print(filepaths)
    elif args.subcmd == "diff":
        print("Getting incremental coverage for new tests relative to the baseline test suite")
        print(filepaths)
    else:
        print(f"Unknown subcommand: {args.subcmd}")
        return 1

def add_shared_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)

def add_llvm_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--llvm-project", type=Path, required=True,
        help="Path to the LLVM project root")
    parser.add_argument("--build-dir", type=Path, required=True, 
        help="Path to the coverage-instrumentedLLVM build directory")
    parser.add_argument("--filter", type=str, default=None, 
        help="Filter prefix for the test suite")

def get_filepaths(args: argparse.Namespace) -> Filepaths:
    return Filepaths(
        output_dir=args.output_dir,
        llvm_project=getattr(args, "llvm_project", None),
        build_dir=getattr(args, "build_dir", None),
        new_tests_dir=getattr(args, "new_tests_dir", None),
        baseline_csv=getattr(args, "baseline_csv", None),
    )
if __name__ == "__main__":
    main()
