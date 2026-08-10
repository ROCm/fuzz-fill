"""End-to-end unit tests for target-lines filtering via uncovered baseline CSV."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from coverage.constants import DEFAULT_LINE_COVERAGE_UNCOVERED_FILE
from coverage.target_lines_check import run_target_lines_check

REL = "llvm/lib/Target/AMDGPU/Foo.cpp"
ABS = "/llvm/llvm/lib/Target/AMDGPU/Foo.cpp"


def _write_csv(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


def _run_source_mismatch_check(
    root: Path, source_text: str, target_text: str
) -> list[dict[str, str]]:
    """Run target-lines with one uncovered ``Foo.cpp:2`` row and return the report rows.

    ``source_text`` is written to ``Foo.cpp`` on disk; ``target_text`` is the
    ``text`` column of the single target-lines row at line 2.
    """
    baseline = root / "baseline"
    baseline.mkdir()

    source_file = root / "Foo.cpp"
    source_file.write_text(source_text, encoding="utf-8")

    uncovered_csv = baseline / DEFAULT_LINE_COVERAGE_UNCOVERED_FILE
    _write_csv(uncovered_csv, [["file", "line"], [str(source_file), 2]])

    target_csv = root / "target.csv"
    _write_csv(target_csv, [["path", "line_no", "text"], ["Foo.cpp", 2, target_text]])

    report = root / "target_lines_uncovered.csv"
    run_target_lines_check(
        line_coverage_uncovered_csv=uncovered_csv,
        llvm_repo=root,
        target_lines_csv=target_csv,
        report_path=report,
    )

    with report.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class RunTargetLinesCheckTest(unittest.TestCase):
    def test_only_uncovered_lines_written_to_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = root / "baseline"
            baseline.mkdir()

            uncovered_csv = baseline / DEFAULT_LINE_COVERAGE_UNCOVERED_FILE
            _write_csv(
                uncovered_csv,
                [
                    ["file", "line"],
                    [ABS, 30],
                    [ABS, 40],
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
                line_coverage_uncovered_csv=uncovered_csv,
                llvm_repo=root / "llvm_repo",
                target_lines_csv=target_csv,
                report_path=report,
            )

            with report.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

            reported = {(row["file"], int(row["line"])) for row in rows}
            self.assertEqual(reported, {(ABS, 30), (ABS, 40)})
            self.assertEqual({row["text"] for row in rows}, {"uncovered line", "uncovered line 2"})

    def test_missing_uncovered_csv_raises_systemexit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target_csv = root / "target.csv"
            _write_csv(target_csv, [["path", "line_no", "text"], [REL, 30, "x"]])

            with self.assertRaises(SystemExit):
                run_target_lines_check(
                    line_coverage_uncovered_csv=root / "missing.csv",
                    llvm_repo=root / "llvm_repo",
                    target_lines_csv=target_csv,
                    report_path=root / "out.csv",
                )

    def test_line_text_mismatch_against_baseline_source_is_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rows = _run_source_mismatch_check(
                Path(tmp),
                source_text="line one\nold second line\nline three\n",
                target_text="new second line",
            )
            self.assertEqual(rows, [])

    def test_line_text_match_against_baseline_source_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rows = _run_source_mismatch_check(
                Path(tmp),
                source_text="line one\nshared second line\nline three\n",
                target_text="shared second line",
            )
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["line"], "2")

    def test_blank_target_text_skips_source_mismatch_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rows = _run_source_mismatch_check(
                Path(tmp),
                source_text="line one\nreal second line\nline three\n",
                target_text="",
            )
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["line"], "2")


if __name__ == "__main__":
    unittest.main()
