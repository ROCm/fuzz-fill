"""Aggregation skips lit ``%t`` copies and still fails on other missing binaries."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from coverage.constants import DEFAULT_LINE_COVERAGE_SUMMARY_FILE
from coverage.filepaths import Filepaths
from coverage.sancov import Sancov
from coverage.test_runner import TestRunner


def _runner(root: Path) -> TestRunner:
    bin_dir = root / "build-sancov" / "bin"
    bin_dir.mkdir(parents=True)
    llc = bin_dir / "llc"
    llc.write_text("", encoding="utf-8")
    output = root / "out"
    output.mkdir()
    return TestRunner(
        mode="lit",
        filepaths=Filepaths(
            output_dir=output,
            sancov=bin_dir / "sancov",
            llc=llc,
            line_coverage_summary_file=DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
        ),
        lit_suites=["llvm/test"],
    )


def _dump(raw: Path, name: str) -> None:
    raw.mkdir(parents=True, exist_ok=True)
    (raw / name).write_bytes(b"")


class AggregateLitTemporaryCoverageTest(unittest.TestCase):
    def test_skips_lit_temporary_and_symbolizes_real_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(Path(tmp))
            raw = runner.raw_sancov_output_dir
            _dump(raw, "llc.42.sancov")
            _dump(raw, "exec-options.ll.tmp.bin--.7.sancov")
            _dump(raw, "execname-options.ll.tmp.bin--gisel.8.sancov")
            seen: list[str] = []

            def record(sancov: Sancov) -> None:
                seen.append(sancov.suffix or "")

            covered = pd.DataFrame(
                [{"file": "a.cpp", "line": 1, "point": "0x1", "covered": 0}]
            )
            stdout = io.StringIO()
            with (
                patch("coverage.test_runner._merge_and_symbolize_sancov", record),
                patch.object(
                    Sancov, "load_coverage_dfs_from_sancovs", return_value=[covered]
                ),
                redirect_stdout(stdout),
            ):
                runner.get_aggregate_coverage()

            self.assertEqual(seen, ["llc"])
            text = stdout.getvalue()
            self.assertIn("exec-options.ll.tmp.bin--", text)
            self.assertIn("execname-options.ll.tmp.bin--gisel", text)
            output = runner.filepaths.output_dir
            self.assertTrue((output / "llc_address_line_map.csv").is_file())
            self.assertFalse(
                (output / "exec-options.ll.tmp.bin--_address_line_map.csv").exists()
            )

    def test_missing_real_binary_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(Path(tmp))
            raw = runner.raw_sancov_output_dir
            _dump(raw, "exec-options.ll.tmp.bin--.7.sancov")
            _dump(raw, "not-a-real-tool.9.sancov")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as ctx:
                    runner.get_aggregate_coverage()
            message = str(ctx.exception)
            self.assertIn("not-a-real-tool", message)
            self.assertNotIn("exec-options.ll.tmp.bin--", message)
            self.assertIn("exec-options.ll.tmp.bin--", stdout.getvalue())
