"""Unit tests for target-lines filtering via baseline summary CSV."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from coverage.constants import (
    DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
    DEFAULT_TARGET_LINES_COVERAGE_SUMMARY,
    DEFAULT_TARGET_LINES_REPORT,
)
from coverage.target_lines_check import run_target_lines_check

REL = "llvm/lib/Target/AMDGPU/Foo.cpp"


def _write_csv(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


def _run_source_mismatch_check(
    root: Path, source_text: str, target_text: str, source_text_check: bool = True
) -> list[dict[str, str]]:
    """Run target-lines with one uncovered ``Foo.cpp:2`` row."""
    baseline = root / "baseline"
    baseline.mkdir()
    out = root / "out"

    source_file = root / "Foo.cpp"
    source_file.write_text(source_text, encoding="utf-8")

    summary_csv = baseline / DEFAULT_LINE_COVERAGE_SUMMARY_FILE
    _write_csv(
        summary_csv,
        [["file", "line", "coverage"], [str(source_file), 2, "uncovered"]],
    )

    target_csv = root / "target.csv"
    _write_csv(target_csv, [["path", "line_no", "text"], ["Foo.cpp", 2, target_text]])

    run_target_lines_check(
        summary_csv=summary_csv,
        llvm_repo=root,
        target_lines_csv=target_csv,
        output_dir=out,
        source_text_check=source_text_check,
    )

    with (out / DEFAULT_TARGET_LINES_REPORT).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class RunTargetLinesCheckTest(unittest.TestCase):
    def test_summary_and_uncovered_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = root / "baseline"
            baseline.mkdir()
            out = root / "out"

            source_file = root / REL
            source_file.parent.mkdir(parents=True)
            source_file.write_text(
                "\n".join(f"line {i}" for i in range(1, 30))
                + "\nuncovered line\n"
                + "\n".join(f"line {i}" for i in range(31, 40))
                + "\nuncovered line 2\n",
                encoding="utf-8",
            )
            abs_path = str(source_file)

            summary_csv = baseline / DEFAULT_LINE_COVERAGE_SUMMARY_FILE
            _write_csv(
                summary_csv,
                [
                    ["file", "line", "coverage"],
                    [abs_path, 10, "covered"],
                    [abs_path, 20, "partially"],
                    [abs_path, 30, "uncovered"],
                    [abs_path, 40, "uncovered"],
                ],
            )

            target_csv = root / "target.csv"
            _write_csv(
                target_csv,
                [
                    ["path", "line_no", "text"],
                    [REL, 10, "line 10"],
                    [REL, 20, "line 20"],
                    [REL, 30, "uncovered line"],
                    [REL, 40, "uncovered line 2"],
                    [REL, 999, "not instrumented"],
                    ["some/unknown/File.cpp", 1, "unknown file"],
                ],
            )

            run_target_lines_check(
                summary_csv=summary_csv,
                llvm_repo=root / "llvm_repo",
                target_lines_csv=target_csv,
                output_dir=out,
            )

            with (out / DEFAULT_TARGET_LINES_COVERAGE_SUMMARY).open(
                newline="", encoding="utf-8"
            ) as f:
                summary_rows = list(csv.DictReader(f))
            with (out / DEFAULT_TARGET_LINES_REPORT).open(
                newline="", encoding="utf-8"
            ) as f:
                uncovered_rows = list(csv.DictReader(f))

            self.assertEqual(
                [(r["file"], int(r["line"]), r["coverage"]) for r in summary_rows],
                [
                    (abs_path, 10, "covered"),
                    (abs_path, 20, "partially"),
                    (abs_path, 30, "uncovered"),
                    (abs_path, 40, "uncovered"),
                ],
            )
            self.assertEqual(
                {(r["file"], int(r["line"])) for r in uncovered_rows},
                {(abs_path, 30), (abs_path, 40)},
            )
            self.assertEqual(
                {r["text"] for r in uncovered_rows},
                {"uncovered line", "uncovered line 2"},
            )

    def test_missing_summary_csv_raises_systemexit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target_csv = root / "target.csv"
            _write_csv(target_csv, [["path", "line_no", "text"], [REL, 30, "x"]])

            with self.assertRaises(SystemExit):
                run_target_lines_check(
                    summary_csv=root / "missing.csv",
                    llvm_repo=root / "llvm_repo",
                    target_lines_csv=target_csv,
                    output_dir=root / "out",
                )

    def test_line_text_mismatch_against_baseline_source_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as ctx:
                _run_source_mismatch_check(
                    Path(tmp),
                    source_text="line one\nold second line\nline three\n",
                    target_text="new second line",
                )
            self.assertIn("do not match the source on disk", str(ctx.exception))

    def test_line_text_mismatch_reported_when_check_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            uncovered = _run_source_mismatch_check(
                Path(tmp),
                source_text="line one\nold second line\nline three\n",
                target_text="new second line",
                source_text_check=False,
            )
            self.assertEqual(len(uncovered), 1)
            self.assertEqual(uncovered[0]["line"], "2")

    def test_line_text_match_against_baseline_source_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            uncovered = _run_source_mismatch_check(
                Path(tmp),
                source_text="line one\nshared second line\nline three\n",
                target_text="shared second line",
            )
            self.assertEqual(len(uncovered), 1)
            self.assertEqual(uncovered[0]["line"], "2")

    def test_blank_target_text_against_nonblank_source_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as ctx:
                _run_source_mismatch_check(
                    Path(tmp),
                    source_text="line one\nreal second line\nline three\n",
                    target_text="",
                )
            self.assertIn("do not match the source on disk", str(ctx.exception))

    def test_blank_target_text_against_blank_source_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            uncovered = _run_source_mismatch_check(
                Path(tmp),
                source_text="line one\n\nline three\n",
                target_text="",
            )
            self.assertEqual(len(uncovered), 1)
            self.assertEqual(uncovered[0]["line"], "2")


if __name__ == "__main__":
    unittest.main()
