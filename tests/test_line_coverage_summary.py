"""Unit tests for the shared line coverage summary loader."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from coverage.line_coverage_summary import load_line_coverage_summary

FILE = "/llvm/Foo.cpp"


def _write_summary(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


class LoadLineCoverageSummaryTest(unittest.TestCase):
    def test_parses_and_builds_uncovered_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "line_coverage_summary.csv"
            _write_summary(
                path,
                [
                    ["file", "line", "coverage"],
                    [FILE, 10, "covered"],
                    [FILE, 20, "partially"],
                    [FILE, 30, "uncovered"],
                    [FILE, 40, "uncovered"],
                ],
            )
            coverage_by_line, baseline_uncovered = load_line_coverage_summary(path)

        self.assertEqual(coverage_by_line[(FILE, 10)], "covered")
        self.assertEqual(coverage_by_line[(FILE, 20)], "partially")
        self.assertEqual(coverage_by_line[(FILE, 30)], "uncovered")
        self.assertEqual(baseline_uncovered, frozenset({(FILE, 30), (FILE, 40)}))

    def test_line_cast_to_int(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "line_coverage_summary.csv"
            _write_summary(
                path,
                [["file", "line", "coverage"], [FILE, "30", "uncovered"]],
            )
            coverage_by_line, baseline_uncovered = load_line_coverage_summary(path)

        self.assertIn((FILE, 30), coverage_by_line)
        self.assertIn((FILE, 30), baseline_uncovered)

    def test_missing_file_raises_systemexit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "does_not_exist.csv"
            with self.assertRaises(SystemExit):
                load_line_coverage_summary(path)

    def test_missing_columns_raises_systemexit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "line_coverage_summary.csv"
            _write_summary(path, [["file", "line"], [FILE, 10]])
            with self.assertRaises(SystemExit):
                load_line_coverage_summary(path)


if __name__ == "__main__":
    unittest.main()
