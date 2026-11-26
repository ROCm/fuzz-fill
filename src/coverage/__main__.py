from __future__ import annotations

import argparse
from pathlib import Path

from coverage.candidate_test_settings import load_llc_flag_variants
from coverage.filepaths import Filepaths
from coverage.test_runner import TestRunner
from coverage.constants import (
    DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_MIN_CANDIDATE_TESTS_CSV,
    DEFAULT_MIN_CANDIDATE_TESTS_POINTS_CSV,
    DEFAULT_MIN_CANDIDATE_TESTS_BATCH_SIZE,
    DEFAULT_NEW_COVERAGE_CSV,
    DEFAULT_SOURCE_CODE_FILTER,
    DEFAULT_TIMINGS_FILE,
)
from coverage.analyser import CoverageAnalyzer
from coverage.export_address_map import (
    default_address_map_output,
    export_address_map,
)
from coverage.html_report import write_html_report
from coverage.min_candidate_tests import MinCandidateTestsSelector
from coverage.source_baseline import run_source_baseline
from coverage.target_lines_check import run_target_lines_check
from fuzz_fill.env import (
    FUZZ_FILL_HOST_BIN,
    FUZZ_FILL_COVERAGE_BUILD_DIR,
    FUZZ_FILL_LLC,
    FUZZ_FILL_LLVM_REPO,
    FUZZ_FILL_LLVM_SRC,
    FUZZ_FILL_SANCOV,
    existing_dir_path,
    existing_file_path,
    path_from_flag_or_env,
    require_executable,
)
from fuzz_fill.llvm_tools import (
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
        metavar=(
            "{baseline,export-address-map,candidate-test,incremental,"
            "min-candidate-tests,target-lines,html-report}"
        ),
        required=True,
    )
    p_baseline = sub.add_parser(
        "baseline",
        help=(
            "Source-based coverage baseline: clear-profile-data → check-all → "
            "merge → lcov → covered/uncovered CSVs."
        ),
    )
    p_export_map = sub.add_parser(
        "export-address-map",
        help=(
            "Run a sancov-instrumented tool once and write a PC→line address map "
            "(default tool args: --version)."
        ),
    )
    p_candidate_test = sub.add_parser("candidate-test")
    p_incremental = sub.add_parser("incremental")
    p_min_candidate_tests = sub.add_parser(
        "min-candidate-tests",
        help=(
            "Greedily select candidate-test runs to cover instrumentation points; "
            "yields a minimal set, not necessarily the minimum. "
        ),
    )
    p_target_lines = sub.add_parser(
        "target-lines",
        help=(
            "Intersect a target-lines CSV with ``line_coverage_summary.csv`` "
            "(no lit re-run); write summary and uncovered reports."
        ),
    )
    p_html_report = sub.add_parser(
        "html-report",
        help=(
            "Write a self-contained HTML coverage report from "
            "``line_coverage_summary.csv`` (source pages with covered/uncovered coloring)."
        ),
    )

    add_shared_arguments(p_baseline)
    add_shared_arguments(p_export_map)
    add_shared_arguments(p_candidate_test)
    add_shared_arguments(p_incremental)
    add_shared_arguments(p_min_candidate_tests)
    add_shared_arguments(p_target_lines)
    add_shared_arguments(p_html_report)

    p_baseline.add_argument(
        "--build-dir",
        type=Path,
        default=None,
        help=(
            "Coverage-instrumented LLVM build directory (contains profiles/ and "
            f"ninja targets; or set {FUZZ_FILL_COVERAGE_BUILD_DIR})."
        ),
    )
    p_baseline.add_argument(
        "--llvm-src",
        type=Path,
        default=None,
        help=(
            "llvm-project source root (for prepare-code-coverage-artifact.py, "
            f"COMMIT, and canonical CSV paths; or set {FUZZ_FILL_LLVM_SRC})."
        ),
    )
    p_baseline.add_argument(
        "--host-bin",
        type=Path,
        default=None,
        help=(
            "Bootstrap bin with llvm-profdata and llvm-cov "
            f"(or set {FUZZ_FILL_HOST_BIN})."
        ),
    )
    p_baseline.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=None,
        help=(
            "Parallel jobs for ninja check-all / LIT_OPTS and "
            "llvm-cov export --num-threads (default: core count, capped)."
        ),
    )
    p_baseline.add_argument(
        "--filter",
        action="append",
        dest="filters",
        default=[],
        metavar="REGEX",
        help=(
            "Lit --filter= regex OR'd into LIT_OPTS. Repeatable. "
            "Omit to run check-all unfiltered."
        ),
    )
    p_baseline.add_argument(
        "--binary",
        action="append",
        dest="binaries",
        default=[],
        type=Path,
        metavar="PATH",
        help=(
            "Instrumented binary for llvm-cov export. Repeatable. "
            "Default: all ELF executables under <build-dir>/bin."
        ),
    )
    p_baseline.add_argument(
        "--strict-check-all",
        action="store_true",
        help="Hard-fail on non-zero check-all (default: continue-on-failure).",
    )
    p_baseline.add_argument(
        "--require-profiles",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Exit with an error when check-all produces no .profraw / usable "
            "export (default: enabled). Use --no-require-profiles for an empty baseline."
        ),
    )

    p_export_map.add_argument(
        "--tool",
        type=Path,
        required=True,
        help="Sancov-instrumented tool binary (e.g. llc).",
    )
    p_export_map.add_argument(
        "--sancov",
        type=Path,
        default=None,
        help=f"Path to the sancov executable (or set {FUZZ_FILL_SANCOV}).",
    )
    p_export_map.add_argument(
        "--llvm-src",
        type=Path,
        default=None,
        help=(
            "llvm-project source root for canonical file paths "
            f"(or set {FUZZ_FILL_LLVM_SRC})."
        ),
    )
    p_export_map.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output CSV path (default: <tool>_address_line_map.csv in --output-dir)."
        ),
    )
    p_export_map.add_argument(
        "--tool-args",
        nargs=argparse.REMAINDER,
        default=None,
        help="Arguments passed to --tool (default: --version). Use after other flags.",
    )

    p_candidate_test.add_argument(
        "--llc",
        type=Path,
        default=None,
        help=f"Path to the instrumented llc executable (or set {FUZZ_FILL_LLC}).",
    )
    p_candidate_test.add_argument(
        "--candidate-tests-dir",
        type=Path,
        required=True,
        help="Directory containing the candidate tests (.ll/.bc).",
    )
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
    p_candidate_test.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=None,
        help=(
            "Number of parallel jobs for running candidate tests. Defaults to the "
            "number of detected CPUs."
        ),
    )
    p_candidate_test.add_argument(
        "--timeout",
        type=int,
        default=5,
        help=(
            "Per-test wall-clock timeout in seconds; the test is killed with "
            "SIGKILL (timeout -s9) when exceeded. Default: 5."
        ),
    )
    p_candidate_test.add_argument(
        "--settings-csv",
        type=Path,
        default=None,
        help=(
            "CSV of llc flag variants (column llc_flags). "
            "Default: -O0, -O1, -O2, -O3 (4 variants per input)."
        ),
    )

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
        "--address-line-map-csv",
        type=existing_file_path,
        required=True,
        help=(
            "Sancov tool address-to-line map (``file``, ``line``, ``point`` columns; "
            "from ``coverage export-address-map``)."
        ),
    )
    p_incremental.add_argument(
        "--candidate-tests-output-dir",
        type=existing_dir_path,
        required=True,
        help="Directory containing the candidate tests coverage output",
    )
    p_incremental.add_argument(
        "--source-filter",
        default=DEFAULT_SOURCE_CODE_FILTER,
        metavar="REGEX",
        help=(
            "Only consider baseline gaps whose source file path matches this "
            f"regex (default: {DEFAULT_SOURCE_CODE_FILTER!r}). "
            "Pass an empty string to disable filtering."
        ),
    )

    p_min_candidate_tests.add_argument(
        "--sancov",
        type=Path,
        default=None,
        help=f"Path to the sancov executable (or set {FUZZ_FILL_SANCOV}).",
    )
    p_min_candidate_tests.add_argument(
        "--candidate-tests-output-dir",
        type=existing_dir_path,
        required=True,
        help="Directory containing candidate-test output (manifest, settings, test dirs)",
    )
    p_min_candidate_tests.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=None,
        help=(
            "Number of parallel sancov --print workers within each batch. "
            "Defaults to the number of detected CPUs."
        ),
    )
    p_min_candidate_tests.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_MIN_CANDIDATE_TESTS_BATCH_SIZE,
        help=(
            "Number of runs to load and minimize per batch "
            f"(default: {DEFAULT_MIN_CANDIDATE_TESTS_BATCH_SIZE})."
        ),
    )

    p_target_lines.add_argument(
        "--summary",
        type=existing_file_path,
        required=True,
        help="Path to line_coverage_summary.csv from coverage baseline.",
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
    p_target_lines.add_argument(
        "--commit-check",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Fail when the COMMIT files written by `coverage baseline` and "
            "`added_lines` disagree with each other or with HEAD of "
            "--llvm-repo. Skipped when --llvm-repo is not a git checkout "
            "(default: enabled)."
        ),
    )
    p_target_lines.add_argument(
        "--source-text-check",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Fail when a target line differs from the source on disk at that "
            "line number (default: enabled)."
        ),
    )

    p_html_report.add_argument(
        "--summary",
        type=existing_file_path,
        required=True,
        help="Path to line_coverage_summary.csv from coverage baseline.",
    )
    p_html_report.add_argument(
        "--strip-prefix",
        type=Path,
        default=None,
        help=(
            "Strip this directory prefix from CSV file paths when naming HTML "
            "pages (typically the LLVM checkout used for the baseline)."
        ),
    )
    p_html_report.add_argument(
        "--github-repo",
        default=None,
        help="Source repository for this run (shown on the index).",
    )
    p_html_report.add_argument(
        "--llvm-ref",
        default=None,
        help="Branch, tag, or commit-ish checked out (shown on the index).",
    )
    p_html_report.add_argument(
        "--commit",
        default=None,
        help="Resolved commit SHA for this run (shown on the index).",
    )
    p_html_report.add_argument(
        "--projects",
        default=None,
        help=(
            "Extra LLVM_ENABLE_PROJECTS for this run (shown on the index), "
            "e.g. clang. Use an empty value or 'none' when LLVM-only."
        ),
    )
    p_html_report.add_argument(
        "--backends",
        default=None,
        help=(
            "LLVM_TARGETS_TO_BUILD for this run (shown on the index), "
            "e.g. X86;AMDGPU or all."
        ),
    )
    p_html_report.add_argument(
        "--tests",
        action="append",
        default=None,
        metavar="SUITE",
        help=(
            "Lit suite used for this run (shown on the index). Repeatable. "
            "Optional metadata only."
        ),
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
        build_dir = path_from_flag_or_env(
            args.build_dir, FUZZ_FILL_COVERAGE_BUILD_DIR, flag_name="--build-dir"
        )
        llvm_src = path_from_flag_or_env(
            args.llvm_src, FUZZ_FILL_LLVM_SRC, flag_name="--llvm-src"
        )
        host_bin = path_from_flag_or_env(
            args.host_bin, FUZZ_FILL_HOST_BIN, flag_name="--host-bin"
        )
        if not build_dir.is_dir():
            raise SystemExit(f"--build-dir is not a directory: {build_dir}")
        if not llvm_src.is_dir():
            raise SystemExit(f"--llvm-src is not a directory: {llvm_src}")
        if not host_bin.is_dir():
            raise SystemExit(f"--host-bin is not a directory: {host_bin}")
        binaries = [p.resolve() for p in args.binaries] if args.binaries else None
        logger.info("running source-based coverage baseline")
        with record_log_timings() as timings:
            with log_timing(logger, "baseline"):
                run_source_baseline(
                    build_dir=build_dir,
                    llvm_src=llvm_src,
                    host_bin=host_bin,
                    output_dir=args.output_dir,
                    jobs=args.jobs,
                    filters=args.filters or None,
                    binaries=binaries,
                    strict_check_all=args.strict_check_all,
                    require_profiles=args.require_profiles,
                )
            timings_path = args.output_dir / DEFAULT_TIMINGS_FILE
            write_timings_csv(timings_path, timings)
            logger.info("wrote baseline timings to %s", timings_path)

    elif args.subcmd == "export-address-map":
        llvm_src = path_from_flag_or_env(
            args.llvm_src, FUZZ_FILL_LLVM_SRC, flag_name="--llvm-src"
        )
        sancov = path_from_flag_or_env(
            args.sancov, FUZZ_FILL_SANCOV, flag_name="--sancov"
        )
        require_executable(sancov, flag_name="--sancov")
        tool_args = args.tool_args
        if tool_args is None:
            tool_args = ["--version"]
        elif tool_args and tool_args[0] == "--":
            tool_args = tool_args[1:]
        output = args.output
        if output is None:
            output = args.output_dir / default_address_map_output(args.tool)
        with log_timing(logger, "export-address-map"):
            export_address_map(
                tool=args.tool,
                sancov=sancov,
                llvm_src=llvm_src,
                output=output,
                tool_args=tool_args,
            )

    elif args.subcmd == "candidate-test":
        if args.n is not None and args.n < 1:
            parser.error("--n must be a positive integer.")
        tools = candidate_test_tools_from_args(llc=args.llc)
        filepaths = get_filepaths(args, tools=tools)
        llc_flag_variants = load_llc_flag_variants(args.settings_csv)
        logger.info("getting coverage for the candidate tests")
        with log_timing(logger, "candidate-test"):
            test_runner = TestRunner(
                mode="standalone",
                filepaths=filepaths,
                candidate_tests_limit=args.n,
                llc_flag_variants=llc_flag_variants,
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
            filepaths.address_line_map_csv = args.address_line_map_csv
            filepaths.output_candidate_tests_dir = args.candidate_tests_output_dir

            coverage_analyzer = CoverageAnalyzer(
                filepaths,
                mode="full",
                source_filter=args.source_filter,
            )

            coverage_analyzer.get_incremental_coverage()

    elif args.subcmd == "min-candidate-tests":
        tools = incremental_tools_from_args(sancov=args.sancov)
        logger.info(
            "min-candidate-tests: selecting minimal set of candidate "
            "tests by instrumentation point coverage"
        )
        with log_timing(logger, "min-candidate-tests"):
            selector = MinCandidateTestsSelector(
                candidate_tests_output_dir=args.candidate_tests_output_dir,
                output_dir=args.output_dir,
                sancov_bin=tools.sancov,
                jobs=args.jobs,
                batch_size=args.batch_size,
            )
            selector.run()

    elif args.subcmd == "target-lines":
        args.llvm_repo = path_from_flag_or_env(
            args.llvm_repo, FUZZ_FILL_LLVM_REPO, flag_name="--llvm-repo"
        )
        logger.info(
            "checking target lines from CSV against baseline line coverage "
            "(no lit re-run)"
        )
        with log_timing(logger, "target-lines"):
            run_target_lines_check(
                summary_csv=args.summary,
                llvm_repo=args.llvm_repo,
                target_lines_csv=args.target_lines_csv,
                output_dir=args.output_dir,
                commit_check=args.commit_check,
                source_text_check=args.source_text_check,
            )

    elif args.subcmd == "html-report":
        strip = args.strip_prefix.resolve() if args.strip_prefix is not None else None
        logger.info(
            "writing HTML coverage report from %s into %s",
            args.summary,
            args.output_dir,
        )
        with log_timing(logger, "html-report"):
            write_html_report(
                summary_csv=args.summary,
                output_dir=args.output_dir,
                strip_prefix=strip,
                github_repo=args.github_repo,
                llvm_ref=args.llvm_ref,
                commit=args.commit,
                projects=args.projects,
                backends=args.backends,
                tests=args.tests,
            )
            logger.info("wrote HTML coverage report to %s", args.output_dir)

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
        address_line_map_csv=getattr(args, "address_line_map_csv", None),
        output_candidate_tests_dir=getattr(args, "candidate_tests_output_dir", None),
        line_coverage_summary_file=DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
        new_coverage_csv=DEFAULT_NEW_COVERAGE_CSV,
    )


if __name__ == "__main__":
    main()
