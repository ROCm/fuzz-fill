"""Unit tests for target-lines analysis against line_coverage_status.csv."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from coverage.filepaths import Filepaths
from coverage.target_lines import TargetLinesAnalyzer


def _write_line_coverage_csv(path: Path, rows: list[dict[str, str | int]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["file", "line", "status", "point_addresses"]
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_target_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "line_no", "text"])
        writer.writeheader()
        writer.writerows(rows)


class TargetLinesAnalyzerTests(unittest.TestCase):
    def test_classifies_lines_from_baseline_csv(self) -> None:
        source = "/llvm/lib/Target/AMDGPU/example.cpp"
        rel = "lib/Target/AMDGPU/example.cpp"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            suite_dir = root / "test_suite"
            report_dir = root / "report"
            suite_dir.mkdir()
            report_dir.mkdir()

            _write_line_coverage_csv(
                suite_dir / "line_coverage_status.csv",
                [
                    {"file": source, "line": 10, "status": "full", "point_addresses": ""},
                    {"file": source, "line": 20, "status": "partial", "point_addresses": ""},
                    {"file": source, "line": 30, "status": "none", "point_addresses": "0x4;0x5"},
                ],
            )
            target_csv = root / "targets.csv"
            _write_target_csv(
                target_csv,
                [
                    {"path": rel, "line_no": "10", "text": "covered"},
                    {"path": rel, "line_no": "20", "text": "partial"},
                    {"path": rel, "line_no": "30", "text": "uncovered"},
                    {"path": rel, "line_no": "99", "text": "not instrumented"},
                    {"path": "lib/Other/missing.cpp", "line_no": "1", "text": "unknown"},
                ],
            )

            analyzer = TargetLinesAnalyzer(
                Filepaths(
                    output_dir=report_dir,
                    output_test_suite_dir=suite_dir,
                ),
                llvm_repo=Path("/llvm"),
                target_lines_csv=target_csv,
            )
            analyzer.run()

            with (report_dir / "target_lines_uncovered.csv").open(
                encoding="utf-8", newline=""
            ) as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["path"], rel)
        self.assertEqual(rows[0]["line_no"], "30")
        self.assertEqual(rows[0]["symcov_file"], source)
        self.assertEqual(rows[0]["point_addresses"], "0x4;0x5")


if __name__ == "__main__":
    unittest.main()
