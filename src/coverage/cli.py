"""CLI for llvm-lit + SanitizerCoverage amalgamation."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from coverage.config import CoverageConfig
from coverage.constants import (
    DEFAULT_LIT_FILTER,
    MERGED_SANCOV_SUFFIX_ID,
    default_lit_command,
)
from coverage.session import CoverageSession


def repo_base_from_here() -> Path:
    """Repository root (parent of ``src``) when this file lives in ``src/coverage/``."""
    return Path(__file__).resolve().parent.parent.parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Amalgamate SanitizerCoverage from llvm-lit runs (per --binary)."
    )
    parser.add_argument(
        "--command",
        "-c",
        default=None,
        help="Command line to run tests (parsed with shlex.split). Default: llvm-lit "
        "on ../llvm/test/ with --filter from --filter. Not used with --skip-run.",
    )
    parser.add_argument(
        "--filter",
        dest="lit_filter",
        default=DEFAULT_LIT_FILTER,
        metavar="PATTERN",
        help="Value for lit --filter= when using the default command (default: %(default)s). "
        "Ignored when --command (-c) is set.",
    )
    parser.add_argument(
        "--llvm-project",
        type=Path,
        default=None,
        help="Path to llvm-project root (default: <repo>/llvm-project)",
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=None,
        help="LLVM build tree (e.g. build/ or build-amdgpu/); each --binary and sancov are "
        "taken from <this>/bin/. Independent of --cwd. Default: <llvm-project>/build.",
    )
    parser.add_argument(
        "--coverage-dir",
        type=Path,
        default=None,
        help="Directory for raw .sancov files and merged outputs "
        "(default: <repo>/data/coverage_output/test_suite_<timestamp>)",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=None,
        help="Working directory for the test command (default: current directory).",
    )
    parser.add_argument(
        "--binary",
        dest="binaries",
        action="append",
        default=None,
        metavar="NAME",
        help="Instrumented tool basename under build-dir/bin (repeat for multiple). "
        "Default when omitted: llc opt. Raw files: <name>.<digits>.sancov; merged: "
        f"<name>.{MERGED_SANCOV_SUFFIX_ID}.sancov.",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Only merge/symbolize existing .sancov files in --coverage-dir (no new runs).",
    )
    parser.add_argument(
        "--union-batch",
        type=int,
        default=200,
        metavar="N",
        help="Max .sancov files per sancov -union invocation (avoid ARG_MAX).",
    )
    parser.add_argument(
        "--outline-json",
        type=Path,
        default=None,
        help="Write machine-readable outline (stats + paths) to this JSON file.",
    )
    return parser


def config_from_args(args: argparse.Namespace, base: Path) -> CoverageConfig:
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

    command: str | None
    if args.skip_run:
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
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    base = repo_base_from_here()
    config = config_from_args(args, base)
    try:
        CoverageSession(config).run()
    except (FileNotFoundError, RuntimeError) as e:
        print(f"ERROR: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
