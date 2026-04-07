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
    default_lit_command,
)
from coverage.session import CoverageSession


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
    p.add_argument(
        "--llvm-project",
        type=Path,
        default=None,
        help="Path to llvm-project root (default: <repo>/llvm-project)",
    )
    p.add_argument(
        "--build-dir",
        type=Path,
        default=None,
        help="LLVM build tree (e.g. build/ or build-amdgpu/); each --binary and sancov are "
        "taken from <this>/bin/. Independent of --cwd. Default: <llvm-project>/build.",
    )
    p.add_argument(
        "--coverage-dir",
        type=Path,
        default=None,
        help="Directory for raw .sancov files and merged outputs "
        "(default: <repo>/data/coverage_output/test_suite_<timestamp>)",
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
        "Default when omitted: llc opt. Raw files: <name>.<digits>.sancov; merged: "
        f"<name>.{MERGED_SANCOV_SUFFIX_ID}.sancov.",
    )
    p.add_argument(
        "--skip-run",
        action="store_true",
        help="Only merge/symbolize existing .sancov files in --coverage-dir (no new runs).",
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
    p.add_argument(
        "--llc-tests-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Run llc -o /dev/null on each *.ll and *.bc under DIR (recursive), with the same UBSAN coverage "
        "as lit runs. Symbolizes each run's raw llc.*.sancov and writes "
        "<stem>.line_address_map.csv (file,function,line,llc_addresses) next to the .symcov. "
        "Default --coverage-dir: <repo>/data/coverage_output/new_tests_<timestamp>. "
        "Not compatible with -c or --skip-run.",
    )
    p.add_argument(
        "--llc-test-limit",
        type=int,
        default=None,
        metavar="N",
        help="With --llc-tests-dir: run at most N input files (.ll/.bc, sorted path order). Default: 1.",
    )
    p.add_argument(
        "--llc-baseline-csv",
        type=Path,
        default=None,
        metavar="PATH",
        help="With --llc-tests-dir: CSV with columns file,function,line,llc_addresses (JSON array of "
        "hex ids per row). Loaded once; llc_test_report.csv gains baseline vs test address counts "
        "(unique normalized ids) and novel_vs_baseline_addresses (JSON array; [] without this flag).",
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
        metavar="CSV",
        help="Output CSV path (default: <symcov-dir>/<symcov-stem>.line_address_map.csv).",
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


def _config_from_run_args(args: argparse.Namespace, base: Path) -> CoverageConfig:
    llc_tests_dir: Path | None = None
    llc_tests_limit: int | None = None
    if args.llc_tests_dir is not None:
        llc_tests_dir = Path(args.llc_tests_dir).resolve()
        if not llc_tests_dir.is_dir():
            raise ValueError(f"--llc-tests-dir is not a directory: {llc_tests_dir}")
        if args.skip_run:
            raise ValueError("--llc-tests-dir cannot be used with --skip-run")
        if args.command is not None:
            raise ValueError("--llc-tests-dir cannot be used with --command (-c)")
        llc_tests_limit = 1 if args.llc_test_limit is None else args.llc_test_limit
        if llc_tests_limit < 1:
            raise ValueError("--llc-test-limit must be >= 1")
    else:
        if args.llc_test_limit is not None:
            raise ValueError("--llc-test-limit requires --llc-tests-dir")
        if args.llc_baseline_csv is not None:
            raise ValueError("--llc-baseline-csv requires --llc-tests-dir")

    llc_baseline_csv: Path | None = None
    if llc_tests_dir is not None and args.llc_baseline_csv is not None:
        llc_baseline_csv = Path(args.llc_baseline_csv).resolve()
        if not llc_baseline_csv.is_file():
            raise ValueError(f"--llc-baseline-csv is not a file: {llc_baseline_csv}")

    if llc_tests_dir is not None:
        binaries = ("llc",)
    elif args.binaries is None:
        binaries = ("llc", "opt")
    else:
        seen: set[str] = set()
        uniq: list[str] = []
        for b in args.binaries:
            if b not in seen:
                seen.add(b)
                uniq.append(b)
        binaries = tuple(uniq)

    command: str | None
    if llc_tests_dir is not None:
        command = None
    elif args.skip_run:
        command = args.command
    elif args.command:
        command = args.command
    else:
        command = default_lit_command(args.lit_filter)

    llvm_project = args.llvm_project or base / "llvm-project"
    build_dir = args.build_dir if args.build_dir is not None else llvm_project / "build"
    build_dir = Path(build_dir).resolve()
    if build_dir.name != "bin":
        build_bin_dir = build_dir / "bin"
    else:
        build_bin_dir = build_dir

    cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd()

    if args.coverage_dir is not None:
        coverage_dir = Path(args.coverage_dir).resolve()
    elif llc_tests_dir is not None:
        coverage_dir = (
            base / "data" / "coverage_output" / f"new_tests_{int(time.time())}"
        ).resolve()
    else:
        coverage_dir = (
            base / "data" / "coverage_output" / f"test_suite_{int(time.time())}"
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
        llc_tests_dir=llc_tests_dir,
        llc_tests_limit=llc_tests_limit,
        llc_baseline_csv=llc_baseline_csv,
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(
        prog="coverage",
        description="LLVM SanitizerCoverage tools (run, map, symcov-line-map).",
    )
    sub = parser.add_subparsers(
        dest="subcmd", metavar="{run,map,symcov-line-map}", required=True
    )
    run_p = sub.add_parser(
        "run",
        help="Run tests with UBSAN coverage and merge/symbolize per --binary (default).",
    )
    _add_run_arguments(run_p)

    map_p = sub.add_parser(
        "map",
        help="Map llc/opt symcov+sancov: optional JSON summary and/or joint .sancov.",
    )
    _add_map_arguments(map_p)

    slm_p = sub.add_parser(
        "symcov-line-map",
        help="Extract file/function/line → llc address ids from one .symcov JSON; write CSV beside it.",
    )
    _add_symcov_line_map_arguments(slm_p)

    args = parser.parse_args(argv)

    if args.subcmd == "map":
        from coverage.map_cmd import map_main

        return map_main(args)

    if args.subcmd == "symcov-line-map":
        from coverage.map_cmd import symcov_line_map_main

        return symcov_line_map_main(args)

    if args.subcmd == "run":
        base = Path(__file__).resolve().parent.parent.parent
        try:
            config = _config_from_run_args(args, base)
        except ValueError as e:
            print(f"ERROR: {e}")
            return 2
        try:
            return CoverageSession(config).run()
        except (FileNotFoundError, RuntimeError) as e:
            print(f"ERROR: {e}")
            return 1

    raise AssertionError(f"unknown subcommand: {args.subcmd}")


if __name__ == "__main__":
    raise SystemExit(main())
