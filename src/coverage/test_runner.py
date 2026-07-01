from __future__ import annotations

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
        new_tests_limit: int = 1,
        debug: bool = False,
    ) -> None:
        self.mode = mode
        self.filepaths = filepaths
        self.raw_sancov_output_dir = filepaths.output_dir / "raw_sancov"
        self.debug = debug

        self.filepaths.output_dir.mkdir(parents=True, exist_ok=True)

        if self.mode == "lit":
            self._lit_filter = resolved_lit_filter(lit_filter)
            run_config = build_run_config(lit_filter=lit_filter)
            self._path_filter = run_config["path_filter"]
            write_run_config(self.filepaths.output_dir, lit_filter=lit_filter)
            self.raw_sancov_output_dir.mkdir(parents=True, exist_ok=True)

        elif self.mode == "standalone":
            self._new_tests_limit = new_tests_limit
            self.instrumented_llc = filepaths.instrumented_bin / "llc"
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
            paths.update(p for p in self.filepaths.new_tests_dir.rglob(pattern) if p.is_file())
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

        instrumented_bin = self.filepaths.instrumented_bin
        lit_site_cfg = ensure_lit_sancov_env_forwarding(instrumented_bin)
        lit_suite = lit_test_suite_path(instrumented_bin)
        if not lit_suite.is_dir():
            raise FileNotFoundError(
                f"LLVM lit test suite not found at {lit_suite}. "
                "Expected an instrumented LLVM build configured with the "
                "in-tree test suite (same layout as `ninja check-llvm`)."
            )

        llvm_lit = instrumented_bin / "llvm-lit"
        argv = [
            sys.executable,
            str(llvm_lit),
            str(lit_suite),
            f"--filter={self._lit_filter}",
        ]
        cwd = instrumented_bin.parent
        env = self.ubsan_environ_with_coverage()
        if self.debug:
            print(f"\tRunning: {argv})")
            print(f"\tUBSAN_OPTIONS: {env['UBSAN_OPTIONS']}")
            print(f"\tCWD: {cwd}")
            print(f"\tLit site config: {lit_site_cfg}")
            print(f"\tCoverage directory: {self.raw_sancov_output_dir}")
        else:
            subprocess.run(argv, cwd=cwd, env=env, check=True)

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

        paths = self.collect_llc_input_files()
        to_run = paths[: self._new_tests_limit]
        self.standalone_total_tests = len(to_run) * len(TEST_FLAGS)
        self.standalone_test_id = 0
        self.standalone_tests_complete = 0
        self.standalone_tests_skipped = 0

        if self.standalone_total_tests == 0:
            self._print_standalone_progress("(no standalone inputs)")
            return

        for test_path in to_run:
            for flag in TEST_FLAGS:
                new_test_dir = self.filepaths.output_dir / f"test_{self.standalone_test_id}_{test_path.name}"
                self.create_standalone_test_script(new_test_dir, test_path, flag)
                outcome = self.run_standalone_test(new_test_dir)
                if outcome == "success":
                    self.standalone_tests_complete += 1
                else:
                    self.standalone_tests_skipped += 1
                self._print_standalone_progress(f"[{new_test_dir.name}]")
                self.standalone_test_id += 1

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
            f.write(f"{self.instrumented_llc} {flag} {test_path} > /dev/null 2>&1\n")
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
            subprocess.run(argv, cwd=self.filepaths.new_tests_dir, env=env, check=True)
        except subprocess.CalledProcessError as e:
            shutil.rmtree(test_dir)
            return "skipped"

        return "success"

    def get_aggregate_coverage(self) -> None:
        """Get the aggregate coverage for the test suite."""
        llc_sancov = Sancov(self.filepaths.llvm_bin, 
                            self.filepaths.instrumented_bin / "llc", 
                            self.raw_sancov_output_dir, 
                            "llc")

        opt_sancov = Sancov(self.filepaths.llvm_bin, 
                            self.filepaths.instrumented_bin / "opt", 
                            self.raw_sancov_output_dir, 
                            "opt")

        llc_sancov.merge()
        llc_sancov.symbolize(llc_sancov.get_merged_sancov_path(), llc_sancov.get_merged_symcov_path())

        opt_sancov.merge()
        opt_sancov.symbolize(opt_sancov.get_merged_sancov_path(), opt_sancov.get_merged_symcov_path())

        llc_address_line_map, joint_coverage_df = llc_sancov.get_joint_coverage(
            opt_sancov, self._path_filter
        )

        llc_address_line_map.to_csv(self.filepaths.output_dir / self.filepaths.llc_address_line_map_file, index=False)
        joint_coverage_df.to_csv(self.filepaths.output_dir / self.filepaths.joint_llc_and_opt_coverage_file, index=False)


