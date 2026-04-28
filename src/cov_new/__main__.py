from __future__ import annotations

import argparse
from pathlib import Path

from cov_new.filepaths import Filepaths
from cov_new.test_runner import TestRunner
from cov_new.constants import (
    DEFAULT_LLC_ADDRESS_LINE_MAP_FILE,
    DEFAULT_JOINT_LLC_AND_OPT_COVERAGE_FILE,
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
    p_new_tests.add_argument(
        "--n",
        type=int,
        default=1,
        help="Number of new tests to process (.ll/.bc, sorted path order).",
    )

    p_diff.add_argument("--test-suite-output-dir", type=Path, required=True,
        help="Directory containing the test suite coverage output")
    p_diff.add_argument("--new-tests-output-dir", type=Path, required=True,
        help="Directory containing the new tests coverage output")

    args = parser.parse_args()

    filepaths = get_filepaths(args)

    if args.debug:
        print(f"Debug mode enabled")

    if args.subcmd == "test-suite":
        print("Getting baseline coverage for the test suite")
        test_runner = TestRunner(mode="lit", 
            filepaths=filepaths, 
            lit_filter=args.filter, 
            debug=args.debug)
        test_runner.run()

    elif args.subcmd == "new-tests":
        print("Getting coverage for the new tests")
        test_runner = TestRunner(
            mode="standalone",
            filepaths=filepaths,
            new_tests_limit=args.n,
        )
        test_runner.run()
    
    elif args.subcmd == "diff":
        print("Getting incremental coverage for new tests relative to the baseline test suite")
        filepaths.output_test_suite_dir = args.test_suite_output_dir
        filepaths.output_new_tests_dir = args.new_tests_output_dir
        print(filepaths)
    
    else:
        print(f"Unknown subcommand: {args.subcmd}")
        return 1

def add_shared_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--debug", action="store_true", default=False)

def add_llvm_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--llvm-bin", type=Path, required=True,
        help="Path to the uninstrumented LLVM bin directory")
    parser.add_argument("--instrumented-bin", type=Path, required=True, 
        help="Path to the coverage-instrumented LLVM bin directory")
    parser.add_argument("--filter", type=str, default=None, 
        help="Filter prefix for the test suite")

def get_filepaths(args: argparse.Namespace) -> Filepaths:
    return Filepaths(
        output_dir=args.output_dir,
        llvm_bin=getattr(args, "llvm_bin", None),
        instrumented_bin=getattr(args, "instrumented_bin", None),
        new_tests_dir=getattr(args, "new_tests_dir", None),
        output_test_suite_dir=getattr(args, "output_test_suite_dir", None),
        output_new_tests_dir=getattr(args, "output_new_tests_dir", None),
        llc_address_line_map_file=DEFAULT_LLC_ADDRESS_LINE_MAP_FILE,
        joint_llc_and_opt_coverage_file=DEFAULT_JOINT_LLC_AND_OPT_COVERAGE_FILE,
    )
if __name__ == "__main__":
    main()
