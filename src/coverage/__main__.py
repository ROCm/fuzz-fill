from __future__ import annotations

import argparse
from pathlib import Path

from coverage.filepaths import Filepaths
from coverage.test_runner import TestRunner
from coverage.constants import (
    DEFAULT_LLC_ADDRESS_LINE_MAP_FILE,
    DEFAULT_JOINT_LLC_AND_OPT_COVERAGE_FILE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_NEW_COVERAGE_CSV,
    DEFAULT_PATH_FILTER,
    DEFAULT_COMMIT_LINES_REPORT,
)

from coverage.analyser import CoverageAnalyzer
from coverage.commit_lines_check import run_commit_lines_check

def main():

    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(
        dest="subcmd",
        metavar="{test-suite,new-tests,diff,commit-lines}",
        required=True,
    )
    p_test_suite = sub.add_parser("test-suite")
    p_new_tests = sub.add_parser("new-tests")
    p_diff = sub.add_parser("diff")
    p_commit_lines = sub.add_parser(
        "commit-lines",
        help=(
            "List added-lines rows where every symcov point on that line is uncovered "
            "by the suite (expects ``coverage test-suite`` output; no lit re-run)."
        ),
    )

    add_shared_arguments(p_test_suite)
    add_shared_arguments(p_new_tests)
    add_shared_arguments(p_diff)
    add_shared_arguments(p_commit_lines)

    p_test_suite.add_argument("--llvm-bin", type=Path, required=True,
        help="Path to the uninstrumented LLVM bin directory")
    p_test_suite.add_argument("--instrumented-bin", type=Path, required=True, 
        help="Path to the coverage-instrumented LLVM bin directory")
    p_test_suite.add_argument("--lit-filter", type=str, default=None,
        help="Prefix passed to llvm-lit as --filter=<PREFIX>")

    p_new_tests.add_argument("--instrumented-bin", type=Path, required=True, 
        help="Path to the coverage-instrumented LLVM bin directory")
    p_new_tests.add_argument("--new-tests-dir", type=Path, required=True,
        help="Directory containing the new tests (.ll/.bc).")
    p_new_tests.add_argument(
        "--n",
        type=int,
        default=1,
        help="Number of new tests to process (.ll/.bc, sorted path order).",
    )

    p_diff.add_argument("--llvm-bin", type=Path, required=True,
        help="Path to the uninstrumented LLVM bin directory")
    p_diff.add_argument("--test-suite-output-dir", type=Path, required=True,
        help="Directory containing the test suite coverage output")
    p_diff.add_argument("--new-tests-output-dir", type=Path, required=True,
        help="Directory containing the new tests coverage output")

    p_commit_lines.add_argument(
        "--test-suite-output-dir",
        type=Path,
        required=True,
        help=(
            "Same directory passed as ``--output-dir`` to ``coverage test-suite`` "
            "(must contain ``processed_sancov/llc.0.symcov`` and ``opt.0.symcov``)."
        ),
    )
    p_commit_lines.add_argument(
        "--llvm-repo",
        type=Path,
        required=True,
        help="LLVM checkout used to resolve ``path`` in the added-lines CSV (suffix match to symcov paths).",
    )
    p_commit_lines.add_argument(
        "--added-lines-csv",
        type=Path,
        required=True,
        help="CSV from ``python -m diff added-lines`` (columns path, line_no, text).",
    )
    p_commit_lines.add_argument(
        "--path-filter",
        type=str,
        default=DEFAULT_PATH_FILTER,
        help="Substring filter on symcov file paths (same idea as sancov path filter).",
    )

    args = parser.parse_args()

    filepaths = get_filepaths(args)

    if args.debug:
        print(f"Debug mode enabled")

    if args.subcmd == "test-suite":
        print("Getting baseline coverage for the test suite")
        test_runner = TestRunner(mode="lit", 
            filepaths=filepaths, 
            lit_filter=args.lit_filter, 
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

        coverage_analyzer = CoverageAnalyzer(filepaths, mode="full")

        coverage_analyzer.get_incremental_coverage()

    elif args.subcmd == "commit-lines":
        print(
            "Checking added lines from CSV against test-suite llc/opt symcov "
            "(no lit re-run)",
            flush=True,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        report_path = args.output_dir / DEFAULT_COMMIT_LINES_REPORT
        run_commit_lines_check(
            test_suite_output_dir=args.test_suite_output_dir.resolve(),
            llvm_repo=args.llvm_repo,
            added_lines_csv=args.added_lines_csv.resolve(),
            path_filter=args.path_filter,
            report_path=report_path,
        )

    else:
        print(f"Unknown subcommand: {args.subcmd}")
        return 1

def add_shared_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--debug", action="store_true", default=False)

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
        new_coverage_csv=DEFAULT_NEW_COVERAGE_CSV,
    )
if __name__ == "__main__":
    main()
