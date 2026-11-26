from __future__ import annotations

import asyncio
import os
import shlex
import shutil
from pathlib import Path

from coverage.candidate_test_settings import (
    DEFAULT_LLC_FLAG_VARIANTS,
    write_manifest_csv,
    write_settings_csv,
)
from coverage.constants import (
    DEFAULT_CANDIDATE_TEST_MANIFEST_FILE,
    DEFAULT_CANDIDATE_TEST_SETTINGS_FILE,
)
from coverage.filepaths import Filepaths
from fuzz_fill.log import get_logger, log_timing

logger = get_logger("coverage.test_runner")


class TestRunner:
    """
    Executes standalone candidate tests using an instrumented LLVM build.
    """

    def __init__(
        self,
        mode: str,
        filepaths: Filepaths,
        jobs: int | None = None,
        candidate_tests_limit: int | None = None,
        llc_flag_variants: list[str] | None = None,
        timeout: int = 5,
        debug: bool = False,
    ) -> None:
        self.mode = mode
        self.filepaths = filepaths
        self.raw_sancov_output_dir = filepaths.output_dir / "raw_sancov"
        self.debug = debug

        self.filepaths.output_dir.mkdir(parents=True, exist_ok=True)

        if self.mode != "standalone":
            raise ValueError(f"Invalid mode: {self.mode!r}")

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

    def ubsan_environ_with_coverage(self, out_dir: Path | None = None) -> dict[str, str]:
        env = os.environ.copy()

        if out_dir is None:
            out_dir = self.raw_sancov_output_dir

        if not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)

        # Replace UBSAN_OPTIONS entirely. SanitizerCoverage honors the *last*
        # coverage_dir; inheriting a parent value (e.g. lit's temp dump dir)
        # would redirect dumps away from out_dir.
        env["UBSAN_OPTIONS"] = (
            f"coverage=1:coverage_dir={out_dir}:print_coverage_summary=0"
        )
        return env

    def collect_llc_input_files(self) -> list[Path]:
        """Sorted absolute paths under ``test_root`` with suffix ``.ll`` or ``.bc``."""
        root = self.filepaths.candidate_tests_dir.resolve()
        paths: set[Path] = set()
        for pattern in ("*.ll", "*.bc"):
            paths.update(p.resolve() for p in root.rglob(pattern) if p.is_file())
        return sorted(paths)

    def run(self) -> None:
        asyncio.run(self.run_standalone_tests())

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
            ubsan = self.ubsan_environ_with_coverage(out_dir=test_dir)["UBSAN_OPTIONS"]
            f.write(f"export UBSAN_OPTIONS={shlex.quote(ubsan)}\n")
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

