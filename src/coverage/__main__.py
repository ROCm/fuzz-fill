"""CLI for ``python -m coverage`` and the ``llvm-test-suite-coverage`` console script."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from coverage.config import CoverageConfig
from coverage.constants import (
    DEFAULT_LIT_FILTER,
    MERGED_SANCOV_SUFFIX_ID,
    NEW_TESTS_DEFAULT_BASELINE_CSV,
    NEW_TESTS_DEFAULT_LINE_ADDRESS_MAP_JSON,
    NEW_TESTS_SUBDIR,
    RAW_SANCOV_DIRNAME,
    default_lit_command,
)
from coverage.session import CoverageSession
from coverage.stage_log import stage_line

# Default coverage output folder names under <repo>/data/coverage_output/ (see _config_from_*_args).
_COVERAGE_DIR_PREFIX_RUN = "test_suite"
_COVERAGE_DEFAULT_FOLDER_RUN = f"{_COVERAGE_DIR_PREFIX_RUN}_<timestamp>"

_LLVM_PROJECT_HELP = "Path to llvm-project root (default: <repo>/llvm-project)."
_BUILD_DIR_HELP = (
    "LLVM build directory (e.g. build/ or build-amdgpu/). Instrumented tools and sancov are "
    "resolved from <build-dir>/bin/ unless --build-dir already names a .../bin directory. "
    "Separate from where the test command runs (run's --cwd or new-tests' --tests-dir). "
    "Default: <llvm-project>/build."
)


def _coverage_dir_help(default_folder: str) -> str:
    return (
        "SanitizerCoverage output directory (raw .sancov under raw_sancov/ where applicable; "
        "merges, symbolized JSON, CSV reports). "
        f"Default: <repo>/data/coverage_output/{default_folder}."
    )


def _add_shared_llvm_coverage_args(
    p: argparse.ArgumentParser,
    *,
    coverage_default_folder: str,
    coverage_dir_help_extra: str = "",
    coverage_dir_required: bool = False,
) -> None:
    """``run`` and ``new-tests`` share ``--llvm-project``, ``--build-dir``, ``--coverage-dir``."""
    g = p.add_argument_group("LLVM tree and coverage output")
    g.add_argument(
        "--llvm-project",
        type=Path,
        default=None,
        help=_LLVM_PROJECT_HELP,
    )
    g.add_argument(
        "--build-dir",
        type=Path,
        default=None,
        help=_BUILD_DIR_HELP,
    )
    if coverage_dir_required:
        cov_help = (
            "Required. Parent directory from a prior ``coverage run`` (or same layout): "
            "default --baseline-csv / --line-address-map paths resolve here; "
            f"``new-tests`` writes only under {NEW_TESTS_SUBDIR}/ here."
        )
    else:
        cov_help = _coverage_dir_help(coverage_default_folder)
    if coverage_dir_help_extra:
        cov_help = cov_help.rstrip() + " " + coverage_dir_help_extra
    g.add_argument(
        "--coverage-dir",
        type=Path,
        default=None,
        required=coverage_dir_required,
        help=cov_help,
    )


def _add_run_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--command",
        "-c",
        default=None,
        help="Command line to run tests (parsed with shlex.split). Default: llvm-lit "
        "on ../llvm/test/ with --filter from --filter. Not used with --skip-run.",
    )
    p.add_argument(
        "--filter",
        dest="lit_filter",
        default=DEFAULT_LIT_FILTER,
        metavar="PATTERN",
        help="Value for lit --filter= when using the default command (default: %(default)s). "
        "Ignored when --command (-c) is set.",
    )
    _add_shared_llvm_coverage_args(
        p,
        coverage_default_folder=_COVERAGE_DEFAULT_FOLDER_RUN,
        coverage_dir_help_extra=(
            f"With run, raw <binary>.<pid>.sancov files are under {RAW_SANCOV_DIRNAME}/; merged "
            f"<binary>.{MERGED_SANCOV_SUFFIX_ID}.sancov and .symcov stay in the directory root. "
            f"With --skip-run, raw inputs must be under {RAW_SANCOV_DIRNAME}/."
        ),
    )
    p.add_argument(
        "--cwd",
        type=Path,
        default=None,
        help="Working directory for the test command (default: current directory).",
    )
    p.add_argument(
        "--binary",
        dest="binaries",
        action="append",
        default=None,
        metavar="NAME",
        help="Instrumented tool basename under build-dir/bin (repeat for multiple). "
        "Default when omitted: llc opt. Raw files: "
        f"{RAW_SANCOV_DIRNAME}/<name>.<digits>.sancov; merged (coverage-dir root): "
        f"<name>.{MERGED_SANCOV_SUFFIX_ID}.sancov.",
    )
    p.add_argument(
        "--skip-run",
        action="store_true",
        help="Only merge/symbolize; raw <binary>.<pid>.sancov files must already be under "
        f"{RAW_SANCOV_DIRNAME}/ inside --coverage-dir (no test run).",
    )
    p.add_argument(
        "--union-batch",
        type=int,
        default=200,
        metavar="N",
        help="Max .sancov files per sancov -union invocation (avoid ARG_MAX).",
    )
    p.add_argument(
        "--outline-json",
        type=Path,
        default=None,
        help="Write machine-readable outline (stats + paths) to this JSON file.",
    )


def _add_new_tests_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--tests-dir",
        type=Path,
        required=True,
        metavar="DIR",
        help="Search recursively for *.ll and *.bc; run llc -o /dev/null on each selected file "
        "(cwd is this directory) with UBSAN SanitizerCoverage.",
    )
    _add_shared_llvm_coverage_args(
        p,
        coverage_default_folder=_COVERAGE_DEFAULT_FOLDER_RUN,
        coverage_dir_required=True,
        coverage_dir_help_extra=(
            f"Artifacts are written under {NEW_TESTS_SUBDIR}/ here "
            f"({NEW_TESTS_SUBDIR}/{RAW_SANCOV_DIRNAME}/ for raw llc.<pid>.sancov when llc runs). "
            "If that folder already has llc_test_report.csv or per-test novel-line outputs, "
            "new files use llc_test_report_v2.csv (then _v3, …) and matching *_vN directories."
        ),
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Run at most N inputs (.ll/.bc, sorted path order). Default: 1.",
    )
    p.add_argument(
        "--baseline-csv",
        type=Path,
        default=None,
        metavar="PATH",
        help="Joint coverage CSV (file,function,line,llc_addresses as JSON array per row). "
        "Adds baseline vs test address counts and novel_vs_baseline_addresses on llc_test_report.csv. "
        f"Default when omitted: if {NEW_TESTS_DEFAULT_BASELINE_CSV!r} exists next to --coverage-dir, "
        "use it; otherwise baseline comparison is skipped.",
    )
    p.add_argument(
        "--line-address-map",
        type=Path,
        default=None,
        metavar="PATH",
        help="point_symbol_info.json (symcov point-symbol-info extract from a LIT merge/symbolize run). "
        "Requires a baseline CSV. Writes one CSV per test under llc_test_novel_source_lines/, or "
        "with --sense-check under llc_test_novel_source_lines_in_prefix/ and "
        "llc_test_novel_source_lines_outside_prefix/. "
        "When the map is loaded in full (no --source-path-prefix, or with --sense-check), aborts "
        "with an error if any llc address from a test is missing from the map. "
        f"Default when omitted: if {NEW_TESTS_DEFAULT_LINE_ADDRESS_MAP_JSON!r} exists next to "
        "--coverage-dir, use it; otherwise novel-line outputs are skipped.",
    )
    p.add_argument(
        "--source-path-prefix",
        type=str,
        default=None,
        metavar="PREFIX",
        help="Keep only baseline CSV rows and line-map JSON file keys whose source path is this "
        "POSIX path or under it (expanduser; compared after strip). Requires a baseline CSV "
        "(default file next to --coverage-dir, or --baseline-csv). "
        "Skips non-matching rows before json.loads / line indexing to shrink memory and work.",
    )
    p.add_argument(
        "--sense-check",
        action="store_true",
        help="With a baseline CSV, --line-address-map, and --source-path-prefix: load baseline and "
        "line map without path filtering, compare tests against the full baseline, then report "
        "novel addresses and source lines in two buckets—under the prefix vs outside it. "
        "Writes per-test CSVs under llc_test_novel_source_lines_in_prefix/ and "
        "llc_test_novel_source_lines_outside_prefix/ instead of a single combined file.",
    )
    p.add_argument(
        "--existing-sancov-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Do not run llc. Read raw llc.<pid>.sancov files from this directory and run the same "
        "baseline / novel-line analysis. Reports still go under --coverage-dir/new-tests/. "
        "If that folder already has llc_test_report.csv or per-test novel-line outputs, "
        "new files use llc_test_report_v2.csv (then _v3, …) and matching *_vN directories. "
        "Either pass --reuse-report pointing at a prior llc_test_report.csv from the same test set, "
        "or supply exactly one raw llc.*.sancov per selected test (see docs: same order as sorted "
        "tests under --tests-dir, PIDs increasing).",
    )
    p.add_argument(
        "--reuse-report",
        type=Path,
        default=None,
        metavar="PATH",
        help="With --existing-sancov-dir: prior llc_test_report.csv whose ``test`` and "
        "``raw_sancov_files`` columns list which basenames belong to each input (and ``llc_exit_code`` "
        "for the report). Required when multiple raw files exist per test or ordering is ambiguous.",
    )
    p.add_argument(
        "--novel-line-coverage-level",
        choices=("partial", "full"),
        default="partial",
        help="With --line-address-map: how to flag novel source lines. "
        "partial: at least one line-map address on the source line is hit by the test and none of "
        "those addresses appear in the baseline for that location (default). "
        "full: every line-map address on that source line is hit by the test and none appear in the "
        "baseline for that location.",
    )


def _add_symcov_line_map_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "symcov",
        type=Path,
        metavar="SYMCOV",
        help="Path to a .symcov JSON file (sancov -symbolize output).",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Output path (default: <symcov-stem>.point_symbol_info.json).",
    )
    p.add_argument(
        "--filter",
        dest="symcov_path_filter",
        default=None,
        metavar="PATTERN",
        help="If set, regular expression applied with re.search to each point-symbol-info source "
        "path (POSIX, expanduser)—same idea as llvm-lit --filter= on path strings. "
        "Only matching file entries are written (smaller JSON). Omit for all paths.",
    )


def _add_map_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "llc_symcov",
        type=Path,
        metavar="llc-symcov",
        help="Path to merged llc .symcov",
    )
    p.add_argument(
        "llc_sancov",
        type=Path,
        metavar="llc-sancov",
        help="Path to merged llc .sancov",
    )
    p.add_argument(
        "opt_symcov",
        type=Path,
        metavar="opt-symcov",
        help="Path to merged opt .symcov",
    )
    p.add_argument(
        "opt_sancov",
        type=Path,
        metavar="opt-sancov",
        help="Path to merged opt .sancov",
    )
    p.add_argument(
        "--get-summary",
        action="store_true",
        help="Load symcov files and write JSON summary (stdout or --output).",
    )
    p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="With --get-summary: write JSON to this file (default: stdout).",
    )
    p.add_argument(
        "--create-joint-sancov",
        action="store_true",
        help="Merge llc/opt symcov locations (union to stdout/JSON; use --joint-csv for CSV).",
    )
    p.add_argument(
        "--joint-csv",
        type=Path,
        default=None,
        metavar="PATH",
        help="With --create-joint-sancov: write source locations covered by *either* llc or opt "
        "(deduped union; columns: file, function, line).",
    )
    jf = p.add_mutually_exclusive_group()
    jf.add_argument(
        "--joint-file-prefix",
        type=str,
        default=None,
        metavar="PREFIX",
        help="With --create-joint-sancov: only include source paths under this prefix (POSIX path "
        "prefix after expanduser). Cannot be used with --no-joint-file-filter.",
    )
    jf.add_argument(
        "--no-joint-file-filter",
        action="store_true",
        help="With --create-joint-sancov: include every source path from symcov (no path filter). "
        "Cannot be used with --joint-file-prefix.",
    )


def _new_tests_resolve_optional_file(
    flag: Path | None,
    default_path: Path,
    *,
    flag_label: str,
) -> Path | None:
    """
    Explicit path: must exist. Omitted: use ``default_path`` if that file exists, else ``None``.
    """
    if flag is not None:
        p = Path(flag).resolve()
        if not p.is_file():
            raise ValueError(f"{flag_label} is not a file: {p}")
        return p
    if default_path.is_file():
        return default_path.resolve()
    return None


def _resolve_build_bin_dir(args: argparse.Namespace, base: Path) -> Path:
    llvm_project = args.llvm_project or base / "llvm-project"
    build_dir = args.build_dir if args.build_dir is not None else llvm_project / "build"
    build_dir = Path(build_dir).resolve()
    if build_dir.name != "bin":
        return build_dir / "bin"
    return build_dir


def _config_from_run_args(args: argparse.Namespace, base: Path) -> CoverageConfig:
    if args.binaries is None:
        binaries = ("llc", "opt")
    else:
        seen: set[str] = set()
        uniq: list[str] = []
        for b in args.binaries:
            if b not in seen:
                seen.add(b)
                uniq.append(b)
        binaries = tuple(uniq)

    if args.skip_run:
        command = args.command
    elif args.command:
        command = args.command
    else:
        command = default_lit_command(args.lit_filter)

    build_bin_dir = _resolve_build_bin_dir(args, base)
    cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd()

    if args.coverage_dir is not None:
        coverage_dir = Path(args.coverage_dir).resolve()
    else:
        coverage_dir = (
            base
            / "data"
            / "coverage_output"
            / f"{_COVERAGE_DIR_PREFIX_RUN}_{int(time.time())}"
        ).resolve()

    outline_json = Path(args.outline_json).resolve() if args.outline_json else None

    return CoverageConfig(
        build_bin_dir=build_bin_dir,
        coverage_dir=coverage_dir,
        cwd=cwd,
        binaries=binaries,
        command=command,
        skip_run=args.skip_run,
        union_batch=args.union_batch,
        outline_json=outline_json,
        merged_suffix_id=MERGED_SANCOV_SUFFIX_ID,
        new_tests_dir=None,
        new_tests_limit=None,
        new_tests_baseline_csv=None,
        new_tests_line_address_map=None,
        new_tests_source_path_prefix=None,
        new_tests_sense_check=False,
        new_tests_existing_sancov_dir=None,
        new_tests_reuse_report=None,
        new_tests_novel_line_coverage_level="partial",
    )


def _config_from_new_tests_args(args: argparse.Namespace, base: Path) -> CoverageConfig:
    tests_dir = Path(args.tests_dir).resolve()
    if not tests_dir.is_dir():
        raise ValueError(f"--tests-dir is not a directory: {tests_dir}")

    limit = 1 if args.limit is None else args.limit
    if limit < 1:
        raise ValueError("--limit must be >= 1")

    assert args.coverage_dir is not None
    parent_coverage_dir = Path(args.coverage_dir).resolve()
    if not parent_coverage_dir.is_dir():
        raise ValueError(f"--coverage-dir is not a directory: {parent_coverage_dir}")

    coverage_dir = (parent_coverage_dir / NEW_TESTS_SUBDIR).resolve()

    baseline_csv = _new_tests_resolve_optional_file(
        args.baseline_csv,
        parent_coverage_dir / NEW_TESTS_DEFAULT_BASELINE_CSV,
        flag_label="--baseline-csv",
    )
    line_map = _new_tests_resolve_optional_file(
        args.line_address_map,
        parent_coverage_dir / NEW_TESTS_DEFAULT_LINE_ADDRESS_MAP_JSON,
        flag_label="--line-address-map",
    )

    if line_map is not None and baseline_csv is None:
        raise ValueError(
            "A baseline CSV is required when using a line-address map. "
            "Pass --baseline-csv or place "
            f"{NEW_TESTS_DEFAULT_BASELINE_CSV!r} in the directory given by --coverage-dir."
        )

    source_prefix: str | None = None
    if args.source_path_prefix is not None:
        if baseline_csv is None:
            raise ValueError(
                "--source-path-prefix requires a baseline CSV "
                f"({NEW_TESTS_DEFAULT_BASELINE_CSV!r} next to --coverage-dir, or --baseline-csv)"
            )
        source_prefix = args.source_path_prefix.strip()
        if not source_prefix:
            raise ValueError("--source-path-prefix must be non-empty")

    if args.sense_check:
        if baseline_csv is None:
            raise ValueError(
                "--sense-check requires a baseline CSV "
                f"({NEW_TESTS_DEFAULT_BASELINE_CSV!r} next to --coverage-dir, or --baseline-csv)"
            )
        if line_map is None:
            raise ValueError(
                "--sense-check requires a line-address map "
                f"({NEW_TESTS_DEFAULT_LINE_ADDRESS_MAP_JSON!r} next to --coverage-dir, or "
                "--line-address-map)"
            )
        if source_prefix is None:
            raise ValueError("--sense-check requires --source-path-prefix")

    existing_sancov: Path | None = None
    if args.existing_sancov_dir is not None:
        existing_sancov = Path(args.existing_sancov_dir).resolve()
        if not existing_sancov.is_dir():
            raise ValueError(f"--existing-sancov-dir is not a directory: {existing_sancov}")

    reuse_report: Path | None = None
    if args.reuse_report is not None:
        if existing_sancov is None:
            raise ValueError("--reuse-report requires --existing-sancov-dir")
        reuse_report = Path(args.reuse_report).resolve()
        if not reuse_report.is_file():
            raise ValueError(f"--reuse-report is not a file: {reuse_report}")

    build_bin_dir = _resolve_build_bin_dir(args, base)

    return CoverageConfig(
        build_bin_dir=build_bin_dir,
        coverage_dir=coverage_dir,
        cwd=tests_dir,
        binaries=("llc",),
        command=None,
        skip_run=False,
        union_batch=200,
        outline_json=None,
        merged_suffix_id=MERGED_SANCOV_SUFFIX_ID,
        new_tests_dir=tests_dir,
        new_tests_limit=limit,
        new_tests_baseline_csv=baseline_csv,
        new_tests_line_address_map=line_map,
        new_tests_source_path_prefix=source_prefix,
        new_tests_sense_check=args.sense_check,
        new_tests_existing_sancov_dir=existing_sancov,
        new_tests_reuse_report=reuse_report,
        new_tests_novel_line_coverage_level=args.novel_line_coverage_level,
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(
        prog="coverage",
        description="LLVM SanitizerCoverage tools (run, new-tests, map, symcov-line-map, analyse, "
        "check-uncovered).",
    )
    sub = parser.add_subparsers(
        dest="subcmd",
        metavar="{run,new-tests,map,symcov-line-map,analyse,check-uncovered}",
        required=True,
    )
    run_p = sub.add_parser(
        "run",
        help="llvm-lit (or -c) with UBSAN coverage, then merge and symbolize per --binary.",
    )
    _add_run_arguments(run_p)

    new_p = sub.add_parser(
        "new-tests",
        help="Run llc on .ll/.bc under --tests-dir (or reuse raw .sancov via --existing-sancov-dir). "
        "Requires --coverage-dir (parent ``coverage run`` output); writes under new-tests/ there. "
        "Per-test addresses via sancov --print only (no merge/symbolize).",
    )
    _add_new_tests_arguments(new_p)

    map_p = sub.add_parser(
        "map",
        help="Map llc/opt symcov+sancov: optional JSON summary and/or joint .sancov.",
    )
    _add_map_arguments(map_p)

    slm_p = sub.add_parser(
        "symcov-line-map",
        help="Extract point-symbol-info from a .symcov JSON to a smaller .json beside it.",
    )
    _add_symcov_line_map_arguments(slm_p)

    analyse_p = sub.add_parser(
        "analyse",
        help="Summarise artifacts from a coverage new-tests output directory.",
    )
    analyse_p.add_argument(
        "output_dir",
        type=Path,
        metavar="DIR",
        help="Typically ``<coverage-dir from run>/new-tests/llc_test_novel_source_lines`` (or the "
        "whole ``…/new-tests`` directory); contains per-test novel-line CSVs for stacking.",
    )

    check_uncovered_p = sub.add_parser(
        "check-uncovered",
        help="Check coverage against original/replacement line snippets (stub).",
    )
    check_uncovered_p.add_argument(
        "csv",
        type=Path,
        metavar="CSV",
        help="CSV with columns from ``coverage analyse`` output (per_test_csv, file, function, line) "
        "plus line_original and line_replacement. Optional column ``skip``: value ``1`` skips that row; "
        "``0`` or empty runs the row.",
    )
    check_uncovered_p.add_argument(
        "llvm_build",
        type=Path,
        nargs="?",
        default=None,
        metavar="LLVM-BUILD",
        help="LLVM build directory (e.g. llvm-project/build). Required unless "
        "``--verify-originals-only``.",
    )
    check_uncovered_p.add_argument(
        "--verify-originals-only",
        action="store_true",
        help="Only check that each CSV ``original_line`` matches the source file at ``line``; "
        "no edits and no ninja. ``LLVM-BUILD`` may be omitted.",
    )
    check_uncovered_p.add_argument(
        "--lit-summary-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Directory for lit failure summary excerpts when ``ninja check-all`` fails. "
        "Defaults to the CSV file's directory.",
    )
    check_uncovered_p.add_argument(
        "--resume",
        action="store_true",
        help="Skip CSV rows when ``{csv_stem}_row{N}_lit_summary.txt`` (failed check-all) or "
        "``{csv_stem}_row{N}.done`` (completed check-all) already exists under "
        "``--lit-summary-dir``.",
    )
    check_uncovered_p.add_argument(
        "--start-csv-row",
        type=int,
        default=2,
        metavar="N",
        help="Only process CSV rows at line N or later (line 1 is the header; first data row is 2). "
        "Default is 2.",
    )

    args = parser.parse_args(argv)

    if args.subcmd == "analyse":
        from coverage.analyse import analyse_main

        return analyse_main(args)

    if args.subcmd == "check-uncovered":
        from coverage.check_uncovered import check_uncovered_main

        return check_uncovered_main(args)

    if args.subcmd == "map":
        from coverage.map import map_main

        return map_main(args)

    if args.subcmd == "symcov-line-map":
        from coverage.map import symcov_line_map_main

        return symcov_line_map_main(args)

    if args.subcmd == "run":
        base = Path(__file__).resolve().parent.parent.parent
        try:
            config = _config_from_run_args(args, base)
        except ValueError as e:
            stage_line("coverage", f"ERROR: {e}")
            return 2
        try:
            return CoverageSession(config).run()
        except (FileNotFoundError, RuntimeError) as e:
            stage_line("coverage", f"ERROR: {e}")
            return 1

    if args.subcmd == "new-tests":
        base = Path(__file__).resolve().parent.parent.parent
        try:
            config = _config_from_new_tests_args(args, base)
        except ValueError as e:
            stage_line("coverage", f"ERROR: {e}")
            return 2
        try:
            return CoverageSession(config).run()
        except (FileNotFoundError, RuntimeError) as e:
            stage_line("coverage", f"ERROR: {e}")
            return 1

    raise AssertionError(f"unknown subcommand: {args.subcmd}")


if __name__ == "__main__":
    raise SystemExit(main())
