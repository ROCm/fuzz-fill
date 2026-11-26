"""Source-based ``coverage baseline``: check-all → merge → lcov → CSVs."""

from __future__ import annotations

import fcntl
import os
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pandas as pd

from coverage.constants import (
    DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
    DEFAULT_LIT_FAILURES_REPORT,
    MAX_LIT_JOBS,
)
from coverage.lcov import parse_lcov_to_summary
from coverage.line_coverage_summary import write_line_coverage_summary_splits
from coverage.lit_config import build_lit_filter_regex
from coverage.lit_failures import write_lit_failures_json
from coverage.revision_check import record_baseline_revision_from_src
from fuzz_fill.log import get_logger, log_timing, run_subprocess

logger = get_logger("coverage.source_baseline")

ELF_MAGIC = b"\x7fELF"


def discover_elf_binaries(bin_dir: Path) -> list[Path]:
    """Return sorted ELF executables under ``bin_dir`` (follow symlinks)."""
    if not bin_dir.is_dir():
        raise FileNotFoundError(f"build bin directory not found: {bin_dir}")
    found: list[Path] = []
    for entry in sorted(bin_dir.iterdir()):
        try:
            path = entry.resolve()
        except OSError:
            continue
        if not path.is_file() or not os.access(path, os.X_OK):
            continue
        try:
            with path.open("rb") as f:
                magic = f.read(4)
        except OSError:
            continue
        if magic == ELF_MAGIC:
            found.append(path)
    return found


def _resolve_jobs(jobs: int | None) -> int:
    if jobs is not None and jobs > 0:
        return min(jobs, MAX_LIT_JOBS)
    return min(os.cpu_count() or 1, MAX_LIT_JOBS)


def _run_ninja(
    build_dir: Path,
    target: str,
    *,
    jobs: int,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    cmd = ["ninja", "-C", str(build_dir), target, f"-j{jobs}"]
    return run_subprocess(
        logger,
        cmd,
        label=f"ninja {target}",
        check=check,
        capture_output=True,
        text=True,
        env=env,
    )


def _merge_profiles(
    *,
    llvm_src: Path,
    host_bin: Path,
    build_dir: Path,
    output_dir: Path,
    binaries: list[Path],
) -> Path:
    """Merge ``*.profraw`` via prepare-code-coverage-artifact.py --only-merge."""
    prepare = llvm_src / "llvm" / "utils" / "prepare-code-coverage-artifact.py"
    if not prepare.is_file():
        raise FileNotFoundError(f"missing prepare-code-coverage-artifact.py: {prepare}")
    profiles_dir = build_dir / "profiles"
    report_dir = output_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python3",
        str(prepare),
        str(host_bin / "llvm-profdata"),
        str(host_bin / "llvm-cov"),
        str(profiles_dir),
        str(report_dir),
        *[str(b) for b in binaries],
        "--only-merge",
        "--preserve-profiles",
    ]
    run_subprocess(logger, cmd, label="prepare-code-coverage-artifact merge", check=True)
    profdata = profiles_dir / "Coverage.profdata"
    if not profdata.is_file():
        raise FileNotFoundError(f"expected merged profile at {profdata}")
    # Keep a copy under the output dir for artifacts.
    out_prof = output_dir / "Coverage.profdata"
    shutil.copy2(profdata, out_prof)
    return profdata


def _export_lcov(
    *,
    host_bin: Path,
    profdata: Path,
    binaries: list[Path],
    output_lcov: Path,
    jobs: int,
) -> str:
    objects: list[str] = []
    for i, binary in enumerate(binaries):
        if i == 0:
            objects.append(str(binary))
        else:
            objects.extend(["-object", str(binary)])
    cmd = [
        str(host_bin / "llvm-cov"),
        "export",
        *objects,
        "-format=lcov",
        f"-instr-profile={profdata}",
        f"--num-threads={jobs}",
    ]
    proc = run_subprocess(
        logger,
        cmd,
        label="llvm-cov export lcov",
        check=True,
        capture_output=True,
        text=True,
    )
    output_lcov.write_text(proc.stdout, encoding="utf-8")
    return proc.stdout


@contextmanager
def _coverage_build_lock(build_dir: Path) -> Iterator[None]:
    """Serialize baseline runs that share one coverage build tree."""
    lock_path = build_dir / ".fuzz-fill-baseline.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def run_source_baseline(
    *,
    build_dir: Path,
    llvm_src: Path,
    host_bin: Path,
    output_dir: Path,
    jobs: int | None = None,
    filters: list[str] | None = None,
    binaries: list[Path] | None = None,
    strict_check_all: bool = False,
    require_profiles: bool = True,
) -> pd.DataFrame:
    """Run the source-coverage baseline pipeline; return the summary DataFrame."""
    build_dir = build_dir.resolve()
    llvm_src = llvm_src.resolve()
    host_bin = host_bin.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    for tool in ("llvm-profdata", "llvm-cov"):
        path = host_bin / tool
        if not path.is_file() or not os.access(path, os.X_OK):
            raise SystemExit(f"--host-bin missing executable {tool}: {path}")

    n_jobs = _resolve_jobs(jobs)
    bin_dir = build_dir / "bin"
    resolved_binaries = binaries if binaries else discover_elf_binaries(bin_dir)
    if not resolved_binaries:
        raise SystemExit(f"no ELF binaries found under {bin_dir}")
    logger.info("using %d binaries for llvm-cov export", len(resolved_binaries))

    with _coverage_build_lock(build_dir):
        return _run_source_baseline_locked(
            build_dir=build_dir,
            llvm_src=llvm_src,
            host_bin=host_bin,
            output_dir=output_dir,
            n_jobs=n_jobs,
            filters=filters,
            resolved_binaries=resolved_binaries,
            strict_check_all=strict_check_all,
            require_profiles=require_profiles,
        )


def _run_source_baseline_locked(
    *,
    build_dir: Path,
    llvm_src: Path,
    host_bin: Path,
    output_dir: Path,
    n_jobs: int,
    filters: list[str] | None,
    resolved_binaries: list[Path],
    strict_check_all: bool,
    require_profiles: bool,
) -> pd.DataFrame:
    with log_timing(logger, "clear-profile-data"):
        _run_ninja(build_dir, "clear-profile-data", jobs=n_jobs, check=True)

    lit_opts = [f"-j{n_jobs}"]
    if filters:
        lit_opts.append(f"--filter={build_lit_filter_regex(filters)}")
    env = os.environ.copy()
    env["LIT_OPTS"] = " ".join(lit_opts)
    logger.info("LIT_OPTS=%s", env["LIT_OPTS"])

    with log_timing(logger, "check-all"):
        check_proc = _run_ninja(
            build_dir,
            "check-all",
            jobs=n_jobs,
            env=env,
            check=False,
        )
    check_log = (check_proc.stdout or "") + (check_proc.stderr or "")
    (output_dir / "check-all.log").write_text(check_log, encoding="utf-8")
    n_fail = write_lit_failures_json(
        output_dir / DEFAULT_LIT_FAILURES_REPORT, check_log
    )
    logger.info(
        "check-all exit=%s lit_failures=%d",
        check_proc.returncode,
        n_fail,
    )
    if strict_check_all and check_proc.returncode != 0:
        raise SystemExit(
            f"check-all failed with exit {check_proc.returncode} "
            f"(--strict-check-all); see {output_dir / 'check-all.log'}"
        )

    # check-all may still run non-lit deps (e.g. clang Python unittests) that
    # write .profraw even when --filter matches nothing.
    filter_matched_nothing = "filter did not match any tests" in check_log

    profiles_dir = build_dir / "profiles"
    profraw = list(profiles_dir.glob("*.profraw")) if profiles_dir.is_dir() else []
    if filter_matched_nothing or not profraw:
        if require_profiles:
            if filter_matched_nothing:
                raise SystemExit(
                    "lit filter matched no tests / no .profraw files from the "
                    "filtered suite (use --no-require-profiles to allow an "
                    "empty baseline)"
                )
            raise SystemExit(
                f"no .profraw files under {profiles_dir} after check-all "
                "(use --no-require-profiles to allow an empty baseline)"
            )
        logger.warning(
            "%s; writing empty coverage CSVs",
            "lit filter matched no tests"
            if filter_matched_nothing
            else "no .profraw files",
        )
        summary = pd.DataFrame(columns=["file", "line", "coverage"])
    else:
        with log_timing(logger, "merge profiles"):
            profdata = _merge_profiles(
                llvm_src=llvm_src,
                host_bin=host_bin,
                build_dir=build_dir,
                output_dir=output_dir,
                binaries=resolved_binaries,
            )
        with log_timing(logger, "llvm-cov export"):
            lcov_text = _export_lcov(
                host_bin=host_bin,
                profdata=profdata,
                binaries=resolved_binaries,
                output_lcov=output_dir / "coverage.lcov",
                jobs=n_jobs,
            )
        summary = parse_lcov_to_summary(lcov_text, llvm_src=llvm_src)
        if summary.empty and require_profiles:
            raise SystemExit(
                "llvm-cov export produced no in-tree DA lines "
                "(use --no-require-profiles to allow an empty baseline)"
            )

    summary_path = output_dir / DEFAULT_LINE_COVERAGE_SUMMARY_FILE
    summary.to_csv(summary_path, index=False)
    write_line_coverage_summary_splits(summary, output_dir)
    logger.info(
        "wrote %s (%d rows: %d covered, %d uncovered)",
        summary_path,
        len(summary),
        int((summary["coverage"] == "covered").sum()) if not summary.empty else 0,
        int((summary["coverage"] == "uncovered").sum()) if not summary.empty else 0,
    )

    record_baseline_revision_from_src(llvm_src, output_dir)
    return summary
