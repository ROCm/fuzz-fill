"""End-to-end unit tests for target-lines filtering via the shared summary loader."""

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
from coverage.target_lines_check import run_target_lines_check

REL = "llvm/lib/Target/AMDGPU/Foo.cpp"
ABS = "/llvm/llvm/lib/Target/AMDGPU/Foo.cpp"


def _write_csv(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


class RunTargetLinesCheckTest(unittest.TestCase):
    def test_only_uncovered_lines_written_to_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = root / "baseline"
            baseline.mkdir()

            _write_csv(
                baseline / DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
                [
                    ["file", "line", "coverage"],
                    [ABS, 10, "covered"],
                    [ABS, 20, "partially"],
                    [ABS, 30, "uncovered"],
                    [ABS, 40, "uncovered"],
                ],
            )

            target_csv = root / "target.csv"
            _write_csv(
                target_csv,
                [
                    ["path", "line_no", "text"],
                    [REL, 10, "covered line"],
                    [REL, 20, "partial line"],
                    [REL, 30, "uncovered line"],
                    [REL, 40, "uncovered line 2"],
                    [REL, 999, "not instrumented"],
                    ["some/unknown/File.cpp", 1, "unknown file"],
                ],
            )

            report = root / "target_lines_uncovered.csv"
            run_target_lines_check(
                baseline_output_dir=baseline,
                llvm_repo=root / "llvm_repo",
                target_lines_csv=target_csv,
                report_path=report,
            )

            with report.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

            reported = {(row["file"], int(row["line_no"])) for row in rows}
            self.assertEqual(reported, {(REL, 30), (REL, 40)})

    def test_reads_split_baseline_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = root / "baseline"
            baseline.mkdir()

            _write_csv(
                baseline / DEFAULT_LINE_COVERAGE_COVERED_FILE,
                [["file", "line"], [ABS, 10]],
            )
            _write_csv(
                baseline / DEFAULT_LINE_COVERAGE_PARTIALLY_FILE,
                [["file", "line"], [ABS, 20]],
            )
            _write_csv(
                baseline / DEFAULT_LINE_COVERAGE_UNCOVERED_FILE,
                [["file", "line"], [ABS, 30], [ABS, 40]],
            )

            target_csv = root / "target.csv"
            _write_csv(
                target_csv,
                [
                    ["path", "line_no", "text"],
                    [REL, 10, "covered line"],
                    [REL, 20, "partial line"],
                    [REL, 30, "uncovered line"],
                    [REL, 40, "uncovered line 2"],
                ],
            )

            report = root / "target_lines_uncovered.csv"
            run_target_lines_check(
                baseline_output_dir=baseline,
                llvm_repo=root / "llvm_repo",
                target_lines_csv=target_csv,
                report_path=report,
            )

            with report.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

            reported = {(row["file"], int(row["line_no"])) for row in rows}
            self.assertEqual(reported, {(REL, 30), (REL, 40)})

    def test_missing_summary_raises_systemexit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = root / "baseline"
            baseline.mkdir()
            target_csv = root / "target.csv"
            _write_csv(target_csv, [["path", "line_no", "text"], [REL, 30, "x"]])

            with self.assertRaises(SystemExit):
                run_target_lines_check(
                    baseline_output_dir=baseline,
                    llvm_repo=root / "llvm_repo",
                    target_lines_csv=target_csv,
                    report_path=root / "out.csv",
                )


if __name__ == "__main__":
    unittest.main()
