from __future__ import annotations

import os
import shutil
import subprocess
import pandas as pd
from pathlib import Path

from coverage.constants import DEFAULT_LIT_FILTER
from coverage.filepaths import Filepaths
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

        if self.mode == "lit":
            self._lit_filter = lit_filter if lit_filter is not None else DEFAULT_LIT_FILTER

        elif self.mode == "standalone":
            self._new_tests_limit = new_tests_limit
            self.instrumented_llc = filepaths.instrumented_bin / "llc"

        self.filepaths.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_sancov_output_dir.mkdir(parents=True, exist_ok=True)

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

        for test_path in to_run:
            self.run_standalone_test(test_path)

    def run_standalone_test(self, test_path: Path) -> None:
        rel = test_path.relative_to(self.filepaths.new_tests_dir)

        out_dir = self.raw_sancov_output_dir / test_path.name

        if out_dir.exists():
            print(f"Sancov files already exist in {out_dir}, skipping test {test_path}")
            return

        env = self.ubsan_environ_with_coverage(out_dir = out_dir)
        argv = [str(self.instrumented_llc), "-o", "/dev/null", str(rel)]

        if self.debug:
            print(f"\tRunning: {argv}")
            print(f"\tUBSAN_OPTIONS: {env['UBSAN_OPTIONS']}")
            print(f"\tCWD: {self.filepaths.new_tests_dir}")
            print(f"\tCoverage directory: {self.raw_sancov_output_dir}")
        else:
            try:
                subprocess.run(argv, cwd=self.filepaths.new_tests_dir, env=env, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error running test {test_path}: {e}")
                print(f"Output: {e.output}")
                print(f"Return code: {e.returncode}")
                print(f"Stderr: {e.stderr}")
                print(f"Skipping test {test_path}")
                shutil.rmtree(out_dir)
                return

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

        llc_address_line_map, joint_coverage_df = llc_sancov.get_joint_coverage(opt_sancov)

        llc_address_line_map.to_csv(self.filepaths.output_dir / self.filepaths.llc_address_line_map_file, index=False)
        joint_coverage_df.to_csv(self.filepaths.output_dir / self.filepaths.joint_llc_and_opt_coverage_file, index=False)


