from __future__ import annotations

import concurrent.futures
import os
import shutil
import subprocess
import sys
import pandas as pd
from pathlib import Path

from coverage.constants import TEST_FLAGS
from coverage.filepaths import Filepaths
from coverage.lit_config import (
    ensure_lit_sancov_env_forwarding,
    lit_test_suite_path,
)
from coverage.run_config import build_run_config, resolved_lit_filter, write_run_config
from coverage.sancov import Sancov
from fuzz_fill.log import get_logger, log_timing, run_subprocess

logger = get_logger("coverage.test_runner")

class TestRunner:
    """
    Executes tests using an instrumented LLVM build.
    The tests may be LLVM lit-tests or standalone .ll/.bc files.
    """

    def __init__(
        self,
        mode: str,
        filepaths: Filepaths,
        lit_filter: str | None = None,
        jobs: int | None = None,
        lit_verbose: bool = False,
        lit_allow_failures: bool = False,
        candidate_tests_limit: int | None = None,
        timeout: int = 5,
        debug: bool = False,
    ) -> None:
        self.mode = mode
        self.filepaths = filepaths
        self.raw_sancov_output_dir = filepaths.output_dir / "raw_sancov"
        self.jobs = jobs
        self.lit_verbose = lit_verbose
        self.lit_allow_failures = lit_allow_failures
        self.debug = debug

        self.filepaths.output_dir.mkdir(parents=True, exist_ok=True)

        if self.mode == "lit":
            self._lit_filter = resolved_lit_filter(lit_filter)
            run_config = build_run_config(lit_filter=lit_filter)
            self._path_filter = run_config["path_filter"]
            write_run_config(self.filepaths.output_dir, lit_filter=lit_filter)
            self.raw_sancov_output_dir.mkdir(parents=True, exist_ok=True)

        elif self.mode == "standalone":
            self._candidate_tests_limit = candidate_tests_limit
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
        """Sorted paths under ``test_root`` with suffix ``.ll`` or ``.bc``."""
        paths: set[Path] = set()
        for pattern in ("*.ll", "*.bc"):
            paths.update(p for p in self.filepaths.candidate_tests_dir.rglob(pattern) if p.is_file())
        return sorted(paths)

    def run(self) -> None:
        if self.mode == "lit":
            self.run_lit_tests()
            self.get_aggregate_coverage()
        elif self.mode == "standalone":
            self.run_standalone_tests()
        else:
            raise ValueError(f"Invalid mode: {self.mode!r}")

    def run_lit_tests(self) -> None:
        """Run llvm-lit with SanitizerCoverage output under ``output_dir``."""

        if any(self.raw_sancov_output_dir.glob("*.sancov")):
            print(f"Sancov files already exist in {self.raw_sancov_output_dir}, skipping lit tests")
            return

        llvm_lit = self.filepaths.llvm_lit
        lit_site_cfg = ensure_lit_sancov_env_forwarding(llvm_lit)
        lit_suite = lit_test_suite_path(llvm_lit)
        if not lit_suite.is_dir():
            raise FileNotFoundError(
                f"LLVM lit test suite not found at {lit_suite}. "
                "Expected an instrumented LLVM build configured with the "
                "in-tree test suite (same layout as `ninja check-llvm`)."
            )

        argv = [
            sys.executable,
            str(llvm_lit),
            str(lit_suite),
            f"--filter={self._lit_filter}",
        ]
        if self.jobs is not None:
            argv.append(f"-j{self.jobs}")
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
            result = run_subprocess(
                logger,
                argv,
                label="llvm-lit",
                cwd=cwd,
                env=env,
                check=False,
            )
            if result.returncode != 0:
                if self.lit_allow_failures:
                    print(
                        f"warning: llvm-lit exited with code {result.returncode}; "
                        "continuing baseline coverage (--lit-allow-failures)",
                        flush=True,
                    )
                else:
                    raise subprocess.CalledProcessError(
                        result.returncode, argv, result.stdout, result.stderr
                    )

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

    def run_standalone_tests(self) -> None:
        """Generate each standalone test directory and run it before moving to the next."""

        with log_timing(logger, "standalone candidate tests"):
            paths = self.collect_llc_input_files()
            limit = self._candidate_tests_limit
            to_run = paths if limit is None else paths[:limit]
            self.standalone_total_tests = len(to_run) * len(TEST_FLAGS)
            self.standalone_test_id = 0
            self.standalone_tests_complete = 0
            self.standalone_tests_skipped = 0

            if self.standalone_total_tests == 0:
                self._print_standalone_progress("(no standalone inputs)")
                return

            # Pre-assign ids in nested order so dir names match the sequential
            # version and workers never share mutable id state.
            work = []
            tid = 0
            for test_path in to_run:
                for flag in TEST_FLAGS:
                    test_dir = self.filepaths.output_dir / f"test_{tid}_{test_path.name}"
                    work.append((test_dir, test_path, flag))
                    tid += 1

            def _run_one(item):
                test_dir, test_path, flag = item
                self.create_standalone_test_script(test_dir, test_path, flag)
                return test_dir.name, self.run_standalone_test(test_dir)

            with concurrent.futures.ThreadPoolExecutor(max_workers=self._jobs) as pool:
                futures = [pool.submit(_run_one, item) for item in work]
                # Drain on the main thread: counters/prints stay single-threaded.
                for future in concurrent.futures.as_completed(futures):
                    name, outcome = future.result()
                    if outcome == "success":
                        self.standalone_tests_complete += 1
                    else:
                        self.standalone_tests_skipped += 1
                    self._print_standalone_progress(f"[{name}]")

    def create_standalone_test_script(
        self, test_dir: Path, test_path: Path, flag: str
    ) -> None:
        test_dir.mkdir(parents=True, exist_ok=True)
        script = test_dir / "test.sh"
        with open(script, "w") as f:
            f.write("#!/bin/bash\n")
            f.write("set -euo pipefail\n")
            f.write(
                f"export UBSAN_OPTIONS={self.ubsan_environ_with_coverage(out_dir=test_dir)['UBSAN_OPTIONS']}\n"
            )
            f.write(f"timeout -s9 {self._timeout} {self.llc} {flag} {test_path} -o /dev/null\n")
        script.chmod(0o755)

    def run_standalone_test(self, test_dir: Path) -> str:
        if any(test_dir.glob("*.sancov")):
            print(f"Sancov files already exist in {test_dir}, skipping test {test_dir}")
            return "skipped"

        argv = [str(test_dir / "test.sh")]
        env = os.environ.copy()

        if self.debug:
            print(f"\tRunning: {argv}")
            print(f"\tCWD: {test_dir}")
            print(f"\tCoverage directory: {self.raw_sancov_output_dir}")
            return "skipped"

        try:
            run_subprocess(
                logger,
                argv,
                cwd=self.filepaths.candidate_tests_dir,
                env=env,
                check=True,
            )
        except subprocess.CalledProcessError:
            shutil.rmtree(test_dir)
            return "skipped"

        return "success"

    def get_aggregate_coverage(self) -> None:
        """Get the aggregate coverage for the test suite."""
        with log_timing(logger, "aggregate coverage"):
            llc_sancov = Sancov(
                self.filepaths.sancov,
                self.filepaths.llc,
                self.raw_sancov_output_dir,
                "llc",
            )

            opt_sancov = Sancov(
                self.filepaths.sancov,
                self.filepaths.opt,
                self.raw_sancov_output_dir,
                "opt",
            )

            for sancov in (llc_sancov, opt_sancov):
                if sancov.has_raw_files():
                    sancov.merge()
                    sancov.symbolize(sancov.get_merged_sancov_path(), sancov.get_merged_symcov_path())
                else:
                    print(
                        f"warning: no {sancov.suffix} sancov files in {self.raw_sancov_output_dir}; "
                        f"the selected tests produced no {sancov.suffix} coverage. "
                        f"Treating {sancov.suffix} as empty.",
                        flush=True,
                    )
                    sancov.write_empty_symcov()

        llc_address_line_map, line_coverage_summary = llc_sancov.get_joint_coverage(
            opt_sancov, self._path_filter
        )

        llc_address_line_map.to_csv(self.filepaths.output_dir / self.filepaths.llc_address_line_map_file, index=False)
        line_coverage_summary.to_csv(
            self.filepaths.output_dir / self.filepaths.line_coverage_summary_file,
            index=False,
        )

