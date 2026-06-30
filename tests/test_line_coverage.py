"""Unit tests for line_coverage_status.csv export and load."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from coverage.line_coverage import export_line_coverage_status, load_line_coverage_status
from coverage.sancov import Sancov


def _write_symcov(path: Path, *, file_path: str, points: dict[str, str], covered: list[str]) -> None:
    payload = {
        "point-symbol-info": {file_path: {"fn": points}},
        "covered-points": covered,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class LineCoverageCsvTests(unittest.TestCase):
    def test_export_load_roundtrip(self) -> None:
        f = "/llvm/lib/Target/AMDGPU/example.cpp"
        with tempfile.TemporaryDirectory() as tmp:
            llc_path = Path(tmp) / "llc.0.symcov"
            opt_path = Path(tmp) / "opt.0.symcov"
            csv_path = Path(tmp) / "line_coverage_status.csv"
            _write_symcov(
                llc_path,
                file_path=f,
                points={"0x1": "10:0", "0x2": "20:0"},
                covered=["0x1"],
            )
            _write_symcov(
                opt_path,
                file_path=f,
                points={"0x3": "20:0", "0x4": "30:0"},
                covered=["0x3"],
            )
            view = Sancov.load_joint_coverage(llc_path, opt_path, "AMDGPU")
            export_line_coverage_status(view, csv_path)
            baseline = load_line_coverage_status(csv_path)

        self.assertEqual(baseline.line_status[(f, 10)], "full")
        self.assertEqual(baseline.line_status[(f, 20)], "full")
        self.assertEqual(baseline.line_status[(f, 30)], "none")
        self.assertEqual(baseline.point_addresses_by_line[(f, 30)], ["0x4"])
        self.assertIn(f, baseline.source_files)

    def test_load_missing_file_exits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                load_line_coverage_status(Path(tmp) / "missing.csv")

    def test_load_invalid_status_exits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "bad.csv"
            csv_path.write_text(
                "file,line,status,point_addresses\n"
                "/llvm/foo.cpp,1,bad,\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                load_line_coverage_status(csv_path)


if __name__ == "__main__":
    unittest.main()
