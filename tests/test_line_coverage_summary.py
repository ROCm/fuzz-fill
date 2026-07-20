"""Unit tests for the shared line coverage summary loader."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from coverage.constants import (
    DEFAULT_LINE_COVERAGE_COVERED_FILE,
    DEFAULT_LINE_COVERAGE_PARTIALLY_FILE,
    DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
    DEFAULT_LINE_COVERAGE_UNCOVERED_FILE,
)
from coverage.line_coverage_summary import (
    load_baseline_uncovered_lines,
    load_coverage_by_line,
    load_line_coverage_summary,
    write_line_coverage_summary_splits,
)

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


class WriteLineCoverageSummarySplitsTest(unittest.TestCase):
    def test_writes_three_status_files(self) -> None:
        import pandas as pd

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            coverage = pd.DataFrame(
                [
                    {"file": FILE, "line": 10, "coverage": "covered"},
                    {"file": FILE, "line": 20, "coverage": "partially"},
                    {"file": FILE, "line": 30, "coverage": "uncovered"},
                    {"file": FILE, "line": 40, "coverage": "uncovered"},
                ]
            )
            paths = write_line_coverage_summary_splits(coverage, out)

            self.assertEqual(
                set(paths),
                {"covered", "partially", "uncovered"},
            )
            with paths["covered"].open(encoding="utf-8") as f:
                covered_rows = list(csv.reader(f))
            self.assertEqual(covered_rows, [["file", "line"], [FILE, "10"]])

            with paths["partially"].open(encoding="utf-8") as f:
                partially_rows = list(csv.reader(f))
            self.assertEqual(partially_rows, [["file", "line"], [FILE, "20"]])

            with paths["uncovered"].open(encoding="utf-8") as f:
                uncovered_rows = list(csv.reader(f))
            self.assertEqual(
                uncovered_rows,
                [["file", "line"], [FILE, "30"], [FILE, "40"]],
            )

    def test_empty_status_writes_header_only(self) -> None:
        import pandas as pd

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            coverage = pd.DataFrame(
                [{"file": FILE, "line": 10, "coverage": "covered"}]
            )
            paths = write_line_coverage_summary_splits(coverage, out)

            with paths["partially"].open(encoding="utf-8") as f:
                lines = f.read().strip().splitlines()
            self.assertEqual(lines, ["file,line"])


class LoadBaselineUncoveredLinesTest(unittest.TestCase):
    def test_prefers_uncovered_split_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp)
            _write_summary(
                baseline / DEFAULT_LINE_COVERAGE_UNCOVERED_FILE,
                [
                    ["file", "line"],
                    [FILE, 30],
                    [FILE, 40],
                ],
            )
            baseline_uncovered = load_baseline_uncovered_lines(baseline)

        self.assertEqual(baseline_uncovered, frozenset({(FILE, 30), (FILE, 40)}))

    def test_falls_back_to_summary_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp)
            _write_summary(
                baseline / DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
                [
                    ["file", "line", "coverage"],
                    [FILE, 10, "covered"],
                    [FILE, 30, "uncovered"],
                ],
            )
            baseline_uncovered = load_baseline_uncovered_lines(baseline)

        self.assertEqual(baseline_uncovered, frozenset({(FILE, 30)}))


class LoadCoverageByLineTest(unittest.TestCase):
    def test_prefers_split_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp)
            _write_summary(
                baseline / DEFAULT_LINE_COVERAGE_COVERED_FILE,
                [["file", "line"], [FILE, 10]],
            )
            _write_summary(
                baseline / DEFAULT_LINE_COVERAGE_PARTIALLY_FILE,
                [["file", "line"], [FILE, 20]],
            )
            _write_summary(
                baseline / DEFAULT_LINE_COVERAGE_UNCOVERED_FILE,
                [["file", "line"], [FILE, 30]],
            )
            coverage_by_line = load_coverage_by_line(baseline)

        self.assertEqual(coverage_by_line[(FILE, 10)], "covered")
        self.assertEqual(coverage_by_line[(FILE, 20)], "partially")
        self.assertEqual(coverage_by_line[(FILE, 30)], "uncovered")

    def test_falls_back_to_summary_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp)
            _write_summary(
                baseline / DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
                [
                    ["file", "line", "coverage"],
                    [FILE, 10, "covered"],
                    [FILE, 30, "uncovered"],
                ],
            )
            coverage_by_line = load_coverage_by_line(baseline)

        self.assertEqual(coverage_by_line[(FILE, 10)], "covered")
        self.assertEqual(coverage_by_line[(FILE, 30)], "uncovered")


if __name__ == "__main__":
    unittest.main()
