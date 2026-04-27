from __future__ import annotations

import os
import subprocess
import pandas as pd
from pathlib import Path

from cov_new.constants import DEFAULT_LIT_FILTER
from cov_new.filepaths import Filepaths
from cov_new.sancov import Sancov

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

        if self.mode == "lit":
            self._lit_filter = lit_filter if lit_filter is not None else DEFAULT_LIT_FILTER

        elif self.mode == "standalone":
            self._new_tests_limit = new_tests_limit
            self.instrumented_llc = filepaths.instrumented_bin / "llc"

        self.filepaths.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_sancov_output_dir.mkdir(parents=True, exist_ok=True)

    def ubsan_environ_with_coverage(self) -> dict[str, str]:
        env = os.environ.copy()
        cov_opts = f"coverage=1:coverage_dir={self.raw_sancov_output_dir}"
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

        argv = [
            str(self.filepaths.instrumented_bin / "llvm-lit"),
            "../llvm/test/",
            f"--filter={self._lit_filter}",
        ]
        cwd = self.filepaths.instrumented_bin.parent
        env = self.ubsan_environ_with_coverage()
        if self.debug:
            print(f"\tRunning: {argv})")
            print(f"\tUBSAN_OPTIONS: {env['UBSAN_OPTIONS']}")
            print(f"\tCWD: {cwd}")
            print(f"\tCoverage directory: {self.raw_sancov_output_dir}")
        else:
            subprocess.run(argv, cwd=cwd, env=env, check=True)

    def run_standalone_tests(self) -> None:
        """Run ``llc -o /dev/null`` on each ``*.ll`` / ``*.bc`` (subset by ``new_tests_limit``)."""

        paths = self.collect_llc_input_files()
        to_run = paths[: self._new_tests_limit]
        env = self.ubsan_environ_with_coverage()

        for test_path in to_run:
            rel = test_path.relative_to(self.filepaths.new_tests_dir)
            argv = [str(self.instrumented_llc), "-o", "/dev/null", str(rel)]

            if self.debug:
                print(f"\tRunning: {argv}")
                print(f"\tUBSAN_OPTIONS: {env['UBSAN_OPTIONS']}")
                print(f"\tCWD: {self.filepaths.new_tests_dir}")
                print(f"\tCoverage directory: {self.raw_sancov_output_dir}")
            else:
                subprocess.run(argv, cwd=self.filepaths.new_tests_dir, env=env, check=True)

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

        joint_coverage: pd.DataFrame =llc_sancov.get_joint_coverage(opt_sancov)

