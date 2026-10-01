from __future__ import annotations

import asyncio
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import time
import pandas as pd
from pathlib import Path

from coverage.candidate_test_settings import (
    DEFAULT_LLC_FLAG_VARIANTS,
    write_manifest_csv,
    write_settings_csv,
)
from coverage.constants import (
    BASELINE_LIT_PRIORITY_TESTS,
    DEFAULT_CANDIDATE_TEST_MANIFEST_FILE,
    DEFAULT_CANDIDATE_TEST_SETTINGS_FILE,
    DEFAULT_LIT_FAILURES_REPORT,
)
from coverage.filepaths import Filepaths
from coverage.lit_config import (
    ensure_lit_sancov_env_forwarding,
    filter_existing_lit_priority_tests,
    lit_test_suite_path,
    resolve_lit_job_count,
    resolved_lit_filter,
    seed_lit_priority_test_times,
)
from coverage.line_coverage_summary import write_line_coverage_summary_splits
from coverage.revision_check import record_baseline_revision
from coverage.sancov import Sancov
from fuzz_fill.log import get_logger, log_timing

logger = get_logger("coverage.test_runner")

_LIT_SELECTED_NONE = re.compile(
    r"filter did not match any tests|-- Testing: 0 of "
)


def _merge_and_symbolize_sancov(sancov: Sancov) -> None:
    sancov.merge()
    sancov.symbolize(
        sancov.get_merged_sancov_path(),
        sancov.get_merged_symcov_path(),
    )


def _find_unittests_executables(unittests_root: Path, tool: str) -> list[Path]:
    """Executable paths under ``unittests/`` whose basename matches *tool*."""
    if not unittests_root.is_dir():
        return []
    matches: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(unittests_root):
        if tool not in filenames:
            continue
        path = Path(dirpath) / tool
        try:
            if path.is_file() and os.access(path, os.X_OK):
                matches.append(path)
        except OSError:
            continue
    return matches


def _resolve_symbolize_target(bin_dir: Path, build_root: Path, tool: str) -> Path:
    """Locate the binary that produced ``<tool>.*.sancov`` dumps.

    Tools normally live in ``bin/``. Backend lit filters can also select
    LLVM-Unit shards whose binaries live under ``unittests/`` (for example
    ``unittests/MC/AMDGPU/AMDGPUMCTests``).
    """
    candidate = bin_dir / tool
    if candidate.is_file():
        return candidate

    matches = _find_unittests_executables(build_root / "unittests", tool)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        listed = "\n".join(f"  {path}" for path in matches)
        raise SystemExit(
            f"error: multiple instrumented binaries named {tool!r} under "
            f"{build_root / 'unittests'}:\n{listed}"
        )
    raise SystemExit(
        f"error: instrumented binary for {tool!r} not found: {candidate} "
        f"(also searched under {build_root / 'unittests'})"
    )


def _lit_selected_no_tests(lit_output: str) -> bool:
    """True when llvm-lit discovered tests but selected none to run."""
    return _LIT_SELECTED_NONE.search(lit_output) is not None


def _discard_sancovs(raw_sancov_dir: Path) -> int:
    """Delete every ``.sancov`` dump in *raw_sancov_dir*.

    A lit filter that selects no tests still runs ``--gtest_list_tests`` on
    every unit-test binary, and those processes write coverage dumps. No
    selected test ran, so none of the dumps are coverage to keep.
    """
    removed = 0
    for path in raw_sancov_dir.glob("*.sancov"):
        path.unlink()
        removed += 1
    return removed


class TestRunner:
    """
    Executes tests using an instrumented LLVM build.
    The tests may be LLVM lit-tests or standalone .ll/.bc files.
    """

    def __init__(
        self,
        mode: str,
        filepaths: Filepaths,
        lit_filters: list[str] | None = None,
        jobs: int | None = None,
        lit_verbose: bool = False,
        lit_allow_failures: bool = False,
        lit_priority_slow_tests: bool = True,
        require_sancov: bool = True,
        candidate_tests_limit: int | None = None,
        llc_flag_variants: list[str] | None = None,
        timeout: int = 5,
        debug: bool = False,
    ) -> None:
        self.mode = mode
        self.filepaths = filepaths
        self.raw_sancov_output_dir = filepaths.output_dir / "raw_sancov"
        self.jobs = jobs
        self.lit_verbose = lit_verbose
        self.lit_allow_failures = lit_allow_failures
        self.lit_priority_slow_tests = lit_priority_slow_tests
        self.require_sancov = require_sancov
        self.debug = debug
        self._lit_selected_no_tests = False

        self.filepaths.output_dir.mkdir(parents=True, exist_ok=True)

        if self.mode == "lit":
            self._lit_filter = resolved_lit_filter(lit_filters)
            self.raw_sancov_output_dir.mkdir(parents=True, exist_ok=True)

        elif self.mode == "standalone":
            self._candidate_tests_limit = candidate_tests_limit
            self._llc_flag_variants = (
                list(DEFAULT_LLC_FLAG_VARIANTS)
                if llc_flag_variants is None
                else llc_flag_variants
            )
            self._jobs = jobs if jobs is not None else (os.cpu_count() or 1)
            self._jobs = max(1, self._jobs)
            self._timeout = timeout
            self.llc = filepaths.llc
            self.standalone_test_id = 0
            self.standalone_total_tests = 0
            self.standalone_tests_complete = 0
            self.standalone_tests_skipped = 0

    def ubsan_environ_with_coverage(self, out_dir: str | None = None) -> dict[str, str]:
        env = os.environ.copy()

        if out_dir is None:
            out_dir = self.raw_sancov_output_dir

        if not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)

        cov_opts = f"coverage=1:coverage_dir={out_dir}"
        
        prev = env.get("UBSAN_OPTIONS", "").strip()
        env["UBSAN_OPTIONS"] = f"{cov_opts}:{prev}" if prev else cov_opts
        return env

    def collect_llc_input_files(self) -> list[Path]:
        """Sorted absolute paths under ``test_root`` with suffix ``.ll`` or ``.bc``."""
        root = self.filepaths.candidate_tests_dir.resolve()
        paths: set[Path] = set()
        for pattern in ("*.ll", "*.bc"):
            paths.update(p.resolve() for p in root.rglob(pattern) if p.is_file())
        return sorted(paths)

    def run(self) -> None:
        if self.mode == "lit":
            with log_timing(logger, "lit test suite"):
                self.run_lit_tests()
            self.get_aggregate_coverage()
            record_baseline_revision(self.filepaths.llvm_lit, self.filepaths.output_dir)
        elif self.mode == "standalone":
            asyncio.run(self.run_standalone_tests())
        else:
            raise ValueError(f"Invalid mode: {self.mode!r}")

    def run_lit_tests(self) -> None:
        """Run llvm-lit with SanitizerCoverage output under ``output_dir``."""

        if any(self.raw_sancov_output_dir.glob("*.sancov")):
            print(f"Sancov files already exist in {self.raw_sancov_output_dir}, skipping lit tests")
            return

        llvm_lit = self.filepaths.llvm_lit
        lit_site_cfg = ensure_lit_sancov_env_forwarding(llvm_lit)
        if self.lit_priority_slow_tests:
            priority_tests = filter_existing_lit_priority_tests(
                llvm_lit,
                BASELINE_LIT_PRIORITY_TESTS,
            )
            if priority_tests:
                seed_lit_priority_test_times(llvm_lit, priority_tests)
            else:
                print(
                    "warning: no configured lit priority tests exist in the LLVM "
                    "source tree; skipping .lit_test_times.txt seeding",
                    flush=True,
                )
        lit_suite = lit_test_suite_path(llvm_lit)
        if not lit_suite.is_dir():
            raise FileNotFoundError(
                f"LLVM lit test suite not found at {lit_suite}. "
                "Expected an instrumented LLVM build configured with the "
                "in-tree test suite (same layout as `ninja check-llvm`)."
            )

        lit_jobs = resolve_lit_job_count(self.jobs)
        lit_report_path = self.filepaths.output_dir / DEFAULT_LIT_FAILURES_REPORT
        argv = [
            sys.executable,
            str(llvm_lit),
            str(lit_suite),
            f"--filter={self._lit_filter}",
            f"-j{lit_jobs}",
            "--time-tests",
            "-o",
            str(lit_report_path),
            "--report-failures-only",
        ]
        if self.lit_verbose:
            argv.append("-vv")
        cwd = llvm_lit.parent.parent
        env = self.ubsan_environ_with_coverage()
        if self.debug:
            print(f"\tRunning: {argv})")
            print(f"\tUBSAN_OPTIONS: {env['UBSAN_OPTIONS']}")
            print(f"\tCWD: {cwd}")
            print(f"\tLit site config: {lit_site_cfg}")
            print(f"\tCoverage directory: {self.raw_sancov_output_dir}")
        else:
            logger.debug("running %s", argv)
            logger.debug("cwd: %s", cwd)
            started = time.perf_counter()
            lit_proc = subprocess.Popen(
                argv,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            assert lit_proc.stdout is not None
            for line in lit_proc.stdout:
                print(line, end="", flush=True)
                if _lit_selected_no_tests(line):
                    self._lit_selected_no_tests = True
            returncode = lit_proc.wait()
            logger.info(
                "llvm-lit finished in %.2fs", time.perf_counter() - started
            )
            if returncode != 0:
                if self.lit_allow_failures:
                    print(
                        f"warning: llvm-lit exited with code {returncode}; "
                        "continuing baseline coverage (--lit-allow-failures)",
                        flush=True,
                    )
                else:
                    raise subprocess.CalledProcessError(returncode, argv)

    def _print_standalone_progress(self, label: str | None = None) -> None:
        remaining = (
            self.standalone_total_tests
            - self.standalone_tests_complete
            - self.standalone_tests_skipped
        )
        msg = (
            f"complete={self.standalone_tests_complete}  "
            f"skipped={self.standalone_tests_skipped}  "
            f"remaining={remaining}"
        )
        if label:
            msg = f"{msg}  |  {label}"
        print(msg, flush=True)

    def _prepare_standalone_work(self) -> list[tuple[Path, Path, str]]:
        paths = self.collect_llc_input_files()
        limit = self._candidate_tests_limit
        to_run = paths if limit is None else paths[:limit]
        self.standalone_total_tests = len(to_run) * len(self._llc_flag_variants)
        self.standalone_test_id = 0
        self.standalone_tests_complete = 0
        self.standalone_tests_skipped = 0

        work: list[tuple[Path, Path, str]] = []
        tid = 0
        for test_path in to_run:
            for llc_flags in self._llc_flag_variants:
                test_dir = self.filepaths.output_dir / f"test_{tid}_{test_path.name}"
                work.append((test_dir, test_path, llc_flags))
                tid += 1
        return work

    def _record_standalone_outcome(self, name: str, outcome: str) -> None:
        if outcome == "success":
            self.standalone_tests_complete += 1
        else:
            self.standalone_tests_skipped += 1
        self._print_standalone_progress(f"[{name}]")

    async def run_standalone_tests(self) -> None:
        """Generate each standalone test directory and run it concurrently."""

        with log_timing(logger, "standalone candidate tests"):
            work = self._prepare_standalone_work()
            if self.standalone_total_tests == 0:
                self._print_standalone_progress("(no standalone inputs)")
                return

            output_dir = self.filepaths.output_dir
            write_settings_csv(
                self._llc_flag_variants,
                output_dir / DEFAULT_CANDIDATE_TEST_SETTINGS_FILE,
            )
            write_manifest_csv(
                work,
                output_dir / DEFAULT_CANDIDATE_TEST_MANIFEST_FILE,
            )

            sem = asyncio.Semaphore(self._jobs)

            async def _run_one(item: tuple[Path, Path, str]) -> tuple[str, str]:
                test_dir, test_path, llc_flags = item
                self.create_standalone_test_script(test_dir, test_path, llc_flags)
                async with sem:
                    return test_dir.name, await self._run_standalone_test(test_dir)

            tasks = [asyncio.create_task(_run_one(item)) for item in work]
            for coro in asyncio.as_completed(tasks):
                name, outcome = await coro
                self._record_standalone_outcome(name, outcome)

    def create_standalone_test_script(
        self, test_dir: Path, test_path: Path, llc_flags: str
    ) -> None:
        test_dir = test_dir.resolve()
        test_path = test_path.resolve()
        test_dir.mkdir(parents=True, exist_ok=True)
        script = test_dir / "test.sh"
        with open(script, "w") as f:
            f.write("#!/bin/bash\n")
            f.write("set -euo pipefail\n")
            f.write(
                f"export UBSAN_OPTIONS={self.ubsan_environ_with_coverage(out_dir=test_dir)['UBSAN_OPTIONS']}\n"
            )
            f.write(
                f"timeout -s9 {self._timeout} {self.llc} {llc_flags} {test_path} -o /dev/null\n"
            )
            f.flush()
            # Help overlay/network FS settle before exec; reduces ETXTBSY flakes under parallel runs.
            os.fsync(f.fileno())
        script.chmod(0o755)

    async def _run_standalone_test(self, test_dir: Path) -> str:
        test_dir = test_dir.resolve()
        script = test_dir / "test.sh"
        if any(test_dir.glob("*.sancov")):
            print(f"Sancov files already exist in {test_dir}, skipping test {test_dir}")
            return "skipped"

        if self.debug:
            print(f"\tRunning: {script}")
            print(f"\tCWD: {self.filepaths.candidate_tests_dir}")
            print(f"\tCoverage directory: {self.raw_sancov_output_dir}")
            return "skipped"

        proc = await asyncio.create_subprocess_exec(
            str(script),
            cwd=self.filepaths.candidate_tests_dir.resolve(),
            env=os.environ.copy(),
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=self._timeout + 2)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            shutil.rmtree(test_dir, ignore_errors=True)
            return "skipped"

        if proc.returncode != 0:
            shutil.rmtree(test_dir)
            return "skipped"

        return "success"

    def get_aggregate_coverage(self) -> None:
        """Get the aggregate coverage for the test suite."""
        with log_timing(logger, "aggregate coverage (sancov merge+symbolize)"):
            if self._lit_selected_no_tests:
                removed = _discard_sancovs(self.raw_sancov_output_dir)
                if removed:
                    print(
                        "warning: ignoring "
                        f"{removed} sancov dump(s); llvm-lit selected no tests",
                        flush=True,
                    )
            tools = Sancov.discover_tools(self.raw_sancov_output_dir)
            if not tools:
                if self.require_sancov:
                    raise SystemExit(
                        f"error: no sancov files found in {self.raw_sancov_output_dir}; "
                        "the selected tests produced no coverage. "
                        "Use --no-require-sancov to allow an empty baseline."
                    )
                coverage = Sancov.build_coverage_summary([])
                coverage.to_csv(
                    self.filepaths.output_dir / self.filepaths.line_coverage_summary_file,
                    index=False,
                )
                write_line_coverage_summary_splits(coverage, self.filepaths.output_dir)
                return

            if self.filepaths.llc is None:
                raise SystemExit(
                    "error: --llc is required to locate the instrumented bin directory"
                )
            if self.filepaths.sancov is None:
                raise SystemExit("error: --sancov is required to merge and symbolize coverage")

            instrumented_bin = self.filepaths.llc.parent
            build_root = instrumented_bin.parent
            sancovs: list[Sancov] = []
            for tool in tools:
                symbolize_target = _resolve_symbolize_target(
                    instrumented_bin, build_root, tool
                )
                sancovs.append(
                    Sancov(
                        self.filepaths.sancov,
                        symbolize_target,
                        self.raw_sancov_output_dir,
                        tool,
                    )
                )

            workers = len(sancovs)
            if self.jobs is not None:
                workers = min(self.jobs, workers)
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [
                    pool.submit(_merge_and_symbolize_sancov, s) for s in sancovs
                ]
                for future in concurrent.futures.as_completed(futures):
                    future.result()

        coverage_dfs = Sancov.load_coverage_dfs_from_sancovs(sancovs)
        address_line_maps, line_point_summaries, coverage = Sancov.get_joint_coverage(
            coverage_dfs
        )

        for tool, address_line_map, line_point_summary in zip(
            tools, address_line_maps, line_point_summaries
        ):
            address_line_map.to_csv(
                self.filepaths.output_dir
                / Sancov.tool_address_line_map_filename(tool),
                index=False,
            )
            line_point_summary.to_csv(
                self.filepaths.output_dir
                / Sancov.tool_line_point_summary_filename(tool),
                index=False,
            )
        coverage.to_csv(
            self.filepaths.output_dir / self.filepaths.line_coverage_summary_file,
            index=False,
        )
        write_line_coverage_summary_splits(coverage, self.filepaths.output_dir)

