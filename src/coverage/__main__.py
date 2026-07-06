from __future__ import annotations

import argparse
from pathlib import Path

from coverage.filepaths import Filepaths
from coverage.test_runner import TestRunner
from coverage.constants import (
    DEFAULT_LLC_ADDRESS_LINE_MAP_FILE,
    DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_NEW_COVERAGE_CSV,
    DEFAULT_TARGET_LINES_REPORT,
)

from coverage.analyser import CoverageAnalyzer
from coverage.target_lines_check import run_target_lines_check
from fuzz_fill.env import (
    FUZZ_FILL_LLVM_BIN,
    FUZZ_FILL_LLVM_INSTRUMENTED_BIN,
    FUZZ_FILL_LLVM_REPO,
    path_from_flag_or_env,
)
from fuzz_fill.log import add_log_level_argument, configure_logging, get_logger, log_timing

logger = get_logger("coverage")

def main():

    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(
        dest="subcmd",
        metavar="{baseline,candidate-test,incremental,target-lines}",
        required=True,
    )
    p_baseline = sub.add_parser("baseline")
    p_candidate_test = sub.add_parser("candidate-test")
    p_incremental = sub.add_parser("incremental")
    p_target_lines = sub.add_parser(
        "target-lines",
        help=(
            "List target-lines CSV rows where every instrumentation point on that line is "
            "uncovered by the suite (expects ``line_coverage_summary.csv`` from "
            "``coverage baseline``; no lit re-run)."
        ),
    )

    add_shared_arguments(p_baseline)
    add_shared_arguments(p_candidate_test)
    add_shared_arguments(p_incremental)
    add_shared_arguments(p_target_lines)

    p_baseline.add_argument(
        "--llvm-bin",
        type=Path,
        default=None,
        help=f"Path to the uninstrumented LLVM bin directory (or set {FUZZ_FILL_LLVM_BIN}).",
    )
    p_baseline.add_argument(
        "--instrumented-bin",
        type=Path,
        default=None,
        help=(
            f"Path to the coverage-instrumented LLVM bin directory "
            f"(or set {FUZZ_FILL_LLVM_INSTRUMENTED_BIN})."
        ),
    )
    p_baseline.add_argument("--lit-filter", type=str, default=None,
        help="Prefix passed to llvm-lit as --filter=<PREFIX> (also selects symcov path scope).")
    p_baseline.add_argument("-j", "--jobs", type=int, default=None,
        help="Number of parallel jobs forwarded to llvm-lit as -j<N>. If unset, llvm-lit chooses.")
    p_baseline.add_argument("--lit-verbose", action="store_true",
        help="Forward -vv to llvm-lit for verbose test output.")
    p_baseline.add_argument("--lit-allow-failures", action="store_true",
        help="Continue baseline coverage even if llvm-lit exits non-zero.")

    p_candidate_test.add_argument(
        "--instrumented-bin",
        type=Path,
        default=None,
        help=(
            f"Path to the coverage-instrumented LLVM bin directory "
            f"(or set {FUZZ_FILL_LLVM_INSTRUMENTED_BIN})."
        ),
    )
    p_candidate_test.add_argument("--candidate-tests-dir", type=Path, required=True,
        help="Directory containing the candidate tests (.ll/.bc).")
    p_candidate_test.add_argument(
        "--n",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Process only the first N candidate tests (.ll/.bc, sorted path order). "
            "Default: all tests under --candidate-tests-dir."
        ),
    )
    p_candidate_test.add_argument("-j", "--jobs", type=int, default=None,
        help="Number of parallel jobs for running candidate tests. Defaults to the "
             "number of detected CPUs.")
    p_candidate_test.add_argument("--timeout", type=int, default=5,
        help="Per-test wall-clock timeout in seconds; the test is killed with "
             "SIGKILL (timeout -s9) when exceeded. Default: 5.")

    p_incremental.add_argument(
        "--llvm-bin",
        type=Path,
        default=None,
        help=f"Path to the uninstrumented LLVM bin directory (or set {FUZZ_FILL_LLVM_BIN}).",
    )
    p_incremental.add_argument("--baseline-output-dir", type=Path, required=True,
        help="Directory containing the baseline coverage output")
    p_incremental.add_argument("--candidate-tests-output-dir", type=Path, required=True,
        help="Directory containing the candidate tests coverage output")

    p_target_lines.add_argument(
        "--baseline-output-dir",
        type=Path,
        required=True,
        help=(
            "Same directory passed as ``--output-dir`` to ``coverage baseline`` "
            "(must contain ``line_coverage_summary.csv``)."
        ),
    )
    p_target_lines.add_argument(
        "--llvm-repo",
        type=Path,
        default=None,
        help=(
            "LLVM checkout used to resolve ``path`` in the target-lines CSV "
            f"(suffix match to summary paths; or set {FUZZ_FILL_LLVM_REPO})."
        ),
    )
    p_target_lines.add_argument(
        "--target-lines-csv",
        type=Path,
        required=True,
        help="CSV of source lines to check (columns path, line_no, text).",
    )

    args = parser.parse_args()
    configure_logging(args.log_level)

    if args.debug:
        print(f"Debug mode enabled")

    if args.subcmd == "baseline":
        args.llvm_bin = path_from_flag_or_env(
            args.llvm_bin, FUZZ_FILL_LLVM_BIN, flag_name="--llvm-bin"
        )
        args.instrumented_bin = path_from_flag_or_env(
            args.instrumented_bin,
            FUZZ_FILL_LLVM_INSTRUMENTED_BIN,
            flag_name="--instrumented-bin",
        )
        filepaths = get_filepaths(args)
        print("Getting baseline coverage for the test suite")
        with log_timing(logger, "baseline"):
            test_runner = TestRunner(
                mode="lit",
                filepaths=filepaths,
                lit_filter=args.lit_filter,
                jobs=args.jobs,
                lit_verbose=args.lit_verbose,
                lit_allow_failures=args.lit_allow_failures,
                debug=args.debug,
            )
            test_runner.run()

    elif args.subcmd == "candidate-test":
        args.instrumented_bin = path_from_flag_or_env(
            args.instrumented_bin,
            FUZZ_FILL_LLVM_INSTRUMENTED_BIN,
            flag_name="--instrumented-bin",
        )
        filepaths = get_filepaths(args)
        print("Getting coverage for the candidate tests")
        with log_timing(logger, "candidate-test"):
            test_runner = TestRunner(
                mode="standalone",
                filepaths=filepaths,
                candidate_tests_limit=args.n,
                jobs=args.jobs,
                timeout=args.timeout,
            )
            test_runner.run()
    
    elif args.subcmd == "incremental":
        args.llvm_bin = path_from_flag_or_env(
            args.llvm_bin, FUZZ_FILL_LLVM_BIN, flag_name="--llvm-bin"
        )
        filepaths = get_filepaths(args)
        print("Getting incremental coverage for candidate tests relative to the baseline test suite")
        with log_timing(logger, "incremental"):
            filepaths.output_baseline_dir = args.baseline_output_dir
            filepaths.output_candidate_tests_dir = args.candidate_tests_output_dir

            coverage_analyzer = CoverageAnalyzer(filepaths, mode="full")

            coverage_analyzer.get_incremental_coverage()

    elif args.subcmd == "target-lines":
        args.llvm_repo = path_from_flag_or_env(
            args.llvm_repo, FUZZ_FILL_LLVM_REPO, flag_name="--llvm-repo"
        )
        print(
            "Checking target lines from CSV against baseline line coverage summary "
            "(no lit re-run)",
            flush=True,
        )
        with log_timing(logger, "target-lines"):
            args.output_dir.mkdir(parents=True, exist_ok=True)
            report_path = args.output_dir / DEFAULT_TARGET_LINES_REPORT
            run_target_lines_check(
                baseline_output_dir=args.baseline_output_dir.resolve(),
                llvm_repo=args.llvm_repo,
                target_lines_csv=args.target_lines_csv.resolve(),
                report_path=report_path,
            )

    else:
        print(f"Unknown subcommand: {args.subcmd}")
        return 1

def add_shared_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--debug", action="store_true", default=False)
    add_log_level_argument(parser)

def get_filepaths(args: argparse.Namespace) -> Filepaths:
    return Filepaths(
        output_dir=args.output_dir,
        llvm_bin=getattr(args, "llvm_bin", None),
        instrumented_bin=getattr(args, "instrumented_bin", None),
        candidate_tests_dir=getattr(args, "candidate_tests_dir", None),
        output_baseline_dir=getattr(args, "baseline_output_dir", None),
        output_candidate_tests_dir=getattr(args, "candidate_tests_output_dir", None),
        llc_address_line_map_file=DEFAULT_LLC_ADDRESS_LINE_MAP_FILE,
        line_coverage_summary_file=DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
        new_coverage_csv=DEFAULT_NEW_COVERAGE_CSV,
    )
if __name__ == "__main__":
    main()
