from __future__ import annotations

import argparse
from pathlib import Path

from coverage.filepaths import Filepaths
from coverage.test_runner import TestRunner
from coverage.constants import (
    DEFAULT_LLC_ADDRESS_LINE_MAP_FILE,
    DEFAULT_OPT_ADDRESS_LINE_MAP_FILE,
    DEFAULT_LLC_LINE_POINT_SUMMARY_FILE,
    DEFAULT_OPT_LINE_POINT_SUMMARY_FILE,
    DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_NEW_COVERAGE_CSV,
    DEFAULT_TARGET_LINES_REPORT,
    DEFAULT_TIMINGS_FILE,
)

from coverage.analyser import CoverageAnalyzer
from coverage.target_lines_check import run_target_lines_check
from fuzz_fill.env import (
    FUZZ_FILL_LLC,
    FUZZ_FILL_LLVM_LIT,
    FUZZ_FILL_LLVM_REPO,
    FUZZ_FILL_OPT,
    FUZZ_FILL_SANCOV,
    existing_dir_path,
    existing_file_path,
    path_from_flag_or_env,
)
from fuzz_fill.llvm_tools import (
    baseline_tools_from_args,
    candidate_test_tools_from_args,
    incremental_tools_from_args,
)
from fuzz_fill.log import (
    add_log_level_argument,
    add_log_to_file_argument,
    configure_logging,
    get_logger,
    log_timing,
    record_log_timings,
    resolve_log_file,
    write_timings_csv,
)

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
            "List target-lines CSV rows whose ``(file, line)`` appears in "
            "``line_coverage_uncovered.csv`` from ``coverage baseline`` (no lit re-run)."
        ),
    )

    add_shared_arguments(p_baseline)
    add_shared_arguments(p_candidate_test)
    add_shared_arguments(p_incremental)
    add_shared_arguments(p_target_lines)

    p_baseline.add_argument(
        "--sancov",
        type=Path,
        default=None,
        help=f"Path to the sancov executable (or set {FUZZ_FILL_SANCOV}).",
    )
    p_baseline.add_argument(
        "--llvm-lit",
        type=Path,
        default=None,
        help=f"Path to the llvm-lit executable (or set {FUZZ_FILL_LLVM_LIT}).",
    )
    p_baseline.add_argument(
        "--llc",
        type=Path,
        default=None,
        help=f"Path to the instrumented llc executable (or set {FUZZ_FILL_LLC}).",
    )
    p_baseline.add_argument(
        "--opt",
        type=Path,
        default=None,
        help=f"Path to the instrumented opt executable (or set {FUZZ_FILL_OPT}).",
    )
    p_baseline.add_argument(
        "--lit-filter",
        action="append",
        dest="lit_filters",
        default=None,
        metavar="REGEX",
        help=(
            "llvm-lit --filter= regex; repeat for multiple fragments "
            "(OR'd into one --filter= value)."
        ),
    )
    p_baseline.add_argument("-j", "--jobs", type=int, default=None,
        help=(
            "Number of parallel jobs forwarded to llvm-lit as -j<N>. "
            "If unset, uses the system core count (capped at 384). "
            "llc/opt symbolization uses min(-j, 2) (defaults to 2 when unset)."
        ))
    p_baseline.add_argument("--lit-verbose", action="store_true",
        help="Forward -vv to llvm-lit for verbose test output.")
    p_baseline.add_argument("--lit-allow-failures", action="store_true",
        help="Continue baseline coverage even if llvm-lit exits non-zero.")
    p_baseline.add_argument(
        "--require-sancov",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Exit with an error when the lit run produces no raw .sancov files "
            "(default: enabled). Use --no-require-sancov to allow an empty baseline."
        ),
    )

    p_candidate_test.add_argument(
        "--llc",
        type=Path,
        default=None,
        help=f"Path to the instrumented llc executable (or set {FUZZ_FILL_LLC}).",
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
        "--sancov",
        type=Path,
        default=None,
        help=f"Path to the sancov executable (or set {FUZZ_FILL_SANCOV}).",
    )
    p_incremental.add_argument(
        "--line-coverage-uncovered-csv",
        type=existing_file_path,
        required=True,
        help=(
            "Baseline uncovered lines CSV (``file``, ``line`` columns; output of "
            "``coverage baseline`` as ``line_coverage_uncovered.csv``)."
        ),
    )
    p_incremental.add_argument(
        "--llc-address-line-map-csv",
        type=existing_file_path,
        required=True,
        help=(
            "Baseline llc address-to-line map (``file``, ``line``, ``point`` columns; "
            "output of ``coverage baseline`` as ``llc_address_line_map.csv``)."
        ),
    )
    p_incremental.add_argument(
        "--candidate-tests-output-dir",
        type=existing_dir_path,
        required=True,
        help="Directory containing the candidate tests coverage output",
    )

    p_target_lines.add_argument(
        "--line-coverage-uncovered-csv",
        type=existing_file_path,
        required=True,
        help=(
            "Baseline uncovered lines CSV (``file``, ``line`` columns; output of "
            "``coverage baseline`` as ``line_coverage_uncovered.csv``)."
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
        type=existing_file_path,
        required=True,
        help="CSV of source lines to check (columns path, line_no, text).",
    )

    args = parser.parse_args()
    configure_logging(
        args.log_level,
        log_file=resolve_log_file(args.output_dir, args.log_to_file),
    )

    filepaths = get_filepaths(args)

    if args.debug:
        logger.debug("debug mode enabled")

    if args.subcmd == "baseline":
        tools = baseline_tools_from_args(
            sancov=args.sancov,
            llvm_lit=args.llvm_lit,
            llc=args.llc,
            opt=args.opt,
        )
        filepaths = get_filepaths(args, tools=tools)
        logger.info("getting baseline coverage for the test suite")
        with record_log_timings() as timings:
            with log_timing(logger, "baseline"):
                test_runner = TestRunner(
                    mode="lit",
                    filepaths=filepaths,
                    lit_filters=args.lit_filters,
                    jobs=args.jobs,
                    lit_verbose=args.lit_verbose,
                    lit_allow_failures=args.lit_allow_failures,
                    require_sancov=args.require_sancov,
                    debug=args.debug,
                )
                test_runner.run()
            timings_path = args.output_dir / DEFAULT_TIMINGS_FILE
            write_timings_csv(timings_path, timings)
            logger.info("wrote baseline timings to %s", timings_path)

    elif args.subcmd == "candidate-test":
        tools = candidate_test_tools_from_args(llc=args.llc)
        filepaths = get_filepaths(args, tools=tools)
        logger.info("getting coverage for the candidate tests")
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
        tools = incremental_tools_from_args(sancov=args.sancov)
        filepaths = get_filepaths(args, tools=tools)
        logger.info(
            "getting incremental coverage for candidate tests relative to the baseline test suite",
        )
        with log_timing(logger, "incremental"):
            filepaths.line_coverage_uncovered_csv = args.line_coverage_uncovered_csv
            filepaths.llc_address_line_map_csv = args.llc_address_line_map_csv
            filepaths.output_candidate_tests_dir = args.candidate_tests_output_dir

            coverage_analyzer = CoverageAnalyzer(filepaths, mode="full")

            coverage_analyzer.get_incremental_coverage()

    elif args.subcmd == "target-lines":
        args.llvm_repo = path_from_flag_or_env(
            args.llvm_repo, FUZZ_FILL_LLVM_REPO, flag_name="--llvm-repo"
        )
        logger.info(
            "checking target lines from CSV against baseline uncovered lines "
            "(no lit re-run)"
        )
        with log_timing(logger, "target-lines"):
            args.output_dir.mkdir(parents=True, exist_ok=True)
            report_path = args.output_dir / DEFAULT_TARGET_LINES_REPORT
            run_target_lines_check(
                line_coverage_uncovered_csv=args.line_coverage_uncovered_csv,
                llvm_repo=args.llvm_repo,
                target_lines_csv=args.target_lines_csv,
                report_path=report_path,
            )

    else:
        logger.error("unknown subcommand: %s", args.subcmd)
        return 1

def add_shared_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--debug", action="store_true", default=False)
    add_log_level_argument(parser)
    add_log_to_file_argument(parser)

def get_filepaths(
    args: argparse.Namespace,
    *,
    tools: object | None = None,
) -> Filepaths:
    sancov = llvm_lit = llc = opt = None
    if tools is not None:
        sancov = getattr(tools, "sancov", None)
        llvm_lit = getattr(tools, "llvm_lit", None)
        llc = getattr(tools, "llc", None)
        opt = getattr(tools, "opt", None)
    return Filepaths(
        output_dir=args.output_dir,
        sancov=sancov,
        llvm_lit=llvm_lit,
        llc=llc,
        opt=opt,
        candidate_tests_dir=getattr(args, "candidate_tests_dir", None),
        line_coverage_uncovered_csv=getattr(args, "line_coverage_uncovered_csv", None),
        llc_address_line_map_csv=getattr(args, "llc_address_line_map_csv", None),
        output_candidate_tests_dir=getattr(args, "candidate_tests_output_dir", None),
        llc_address_line_map_file=DEFAULT_LLC_ADDRESS_LINE_MAP_FILE,
        opt_address_line_map_file=DEFAULT_OPT_ADDRESS_LINE_MAP_FILE,
        llc_line_point_summary_file=DEFAULT_LLC_LINE_POINT_SUMMARY_FILE,
        opt_line_point_summary_file=DEFAULT_OPT_LINE_POINT_SUMMARY_FILE,
        line_coverage_summary_file=DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
        new_coverage_csv=DEFAULT_NEW_COVERAGE_CSV,
    )
if __name__ == "__main__":
    main()
