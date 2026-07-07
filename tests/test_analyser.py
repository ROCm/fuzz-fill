"""Unit tests for incremental coverage diffing."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from coverage.analyser import CoverageAnalyzer
from coverage.constants import (
    DEFAULT_LLC_ADDRESS_LINE_MAP_FILE,
    DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
    DEFAULT_NEW_COVERAGE_CSV,
)
from coverage.filepaths import Filepaths
from coverage.line_rules import LineCoverageIndex
from coverage.sancov import Sancov

FILE = "/llvm/Foo.cpp"


class DiffPartialBaselineTest(unittest.TestCase):
    """Diff excludes partial baseline lines even when the new test fully covers them."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.test_suite_dir = self.root / "test_suite"
        self.new_tests_dir = self.root / "new_tests"
        self.diff_dir = self.root / "diff"
        self.test_suite_dir.mkdir()
        self.new_tests_dir.mkdir()
        self.diff_dir.mkdir()

        # Line 10: fully covered by the suite (0x1001 and 0x1002 both hit).
        # Line 20: partially covered (0x2001 hit, 0x2002 not); point_addresses lists
        # every instrumentation point on the line, as in line_coverage_summary.csv.
        # Line 30: completely uncovered by the suite.
        self._write_csv(
            self.test_suite_dir / DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
            [
                ["file", "line", "coverage", "point_addresses"],
                [FILE, 10, "full", "0x1001;0x1002"],
                [FILE, 20, "partial", "0x2001;0x2002"],
                [FILE, 30, "none", "0x3001"],
            ],
        )
        self._write_csv(
            self.test_suite_dir / DEFAULT_LLC_ADDRESS_LINE_MAP_FILE,
            [
                ["file", "line", "point_llc"],
                [FILE, 10, "1001"],
                [FILE, 10, "1002"],
                [FILE, 20, "2001"],
                [FILE, 20, "2002"],
                [FILE, 30, "3001"],
            ],
        )

        new_test_dir = self.new_tests_dir / "test_0_example.ll"
        new_test_dir.mkdir()
        self.new_test_dir = new_test_dir

        # New test hits every instrumentation point on all three lines.
        self.new_test_addresses = {
            "0x1001",
            "0x1002",
            "0x2001",
            "0x2002",
            "0x3001",
        }

        self.filepaths = Filepaths(
            output_dir=self.diff_dir,
            output_test_suite_dir=self.test_suite_dir,
            output_new_tests_dir=self.new_tests_dir,
            llvm_bin=Path("/unused/bin"),
            llc_address_line_map_file=DEFAULT_LLC_ADDRESS_LINE_MAP_FILE,
            line_coverage_summary_file=DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
            new_coverage_csv=DEFAULT_NEW_COVERAGE_CSV,
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    @staticmethod
    def _write_csv(path: Path, rows: list[list[object]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

    def test_partial_baseline_line_fully_covered_by_new_test_is_not_reported(self) -> None:
        """Incremental diff reports only baseline gaps (``none``), not partial lines.

        Even when a new test hits every instrumentation point on a line the suite
        only partially covered, that line must not appear in ``new_coverage.csv``.
        """
        summary = self.test_suite_dir / DEFAULT_LINE_COVERAGE_SUMMARY_FILE
        baseline = LineCoverageIndex.from_summary_df(pd.read_csv(summary))
        self.assertEqual(baseline.classify(FILE, 20), "partial")

        with (
            patch.object(
                Sancov, "get_covered_addresses", return_value=self.new_test_addresses
            ),
            patch(
                "coverage.analyser.get_sancov_file",
                return_value=self.new_test_dir / "llc.1.sancov",
            ),
        ):
            CoverageAnalyzer(self.filepaths, mode="full").get_incremental_coverage()

        report = self.diff_dir / DEFAULT_NEW_COVERAGE_CSV
        with report.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        reported_lines = {int(row["line"]) for row in rows}
        self.assertEqual(reported_lines, {30})
        self.assertNotIn(20, reported_lines)
        self.assertNotIn(10, reported_lines)

        gap_row = rows[0]
        self.assertEqual(gap_row["test_name"], "test_0_example.ll")
        self.assertEqual(gap_row["file"], FILE)
        self.assertEqual(gap_row["line"], "30")
        self.assertEqual(gap_row["covered-points"], "0x3001")


if __name__ == "__main__":
    unittest.main()
