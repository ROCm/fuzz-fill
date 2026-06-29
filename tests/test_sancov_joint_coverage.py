"""Unit tests for joint llc/opt symcov analysis."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from coverage.sancov import Sancov


def _write_symcov(path: Path, *, file_path: str, points: dict[str, str], covered: list[str]) -> None:
    payload = {
        "point-symbol-info": {file_path: {"fn": points}},
        "covered-points": covered,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class JointCoverageViewTests(unittest.TestCase):
    def test_line_status_full_partial_none(self) -> None:
        f = "/llvm/lib/Target/AMDGPU/example.cpp"
        with tempfile.TemporaryDirectory() as tmp:
            llc_path = Path(tmp) / "llc.0.symcov"
            opt_path = Path(tmp) / "opt.0.symcov"
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

        self.assertEqual(view.line_status[(f, 10)], "full")
        self.assertEqual(view.line_status[(f, 20)], "full")
        self.assertEqual(view.line_status[(f, 30)], "none")
        self.assertEqual(view.fully_covered_lines, {(f, 10), (f, 20)})
        self.assertEqual(view.all_uncovered_lines, {(f, 30)})
        self.assertEqual(view.point_addresses_by_line[(f, 30)], ["0x4"])

    def test_line_status_partial_on_single_tool_line(self) -> None:
        f = "/llvm/lib/Target/AMDGPU/partial.cpp"
        with tempfile.TemporaryDirectory() as tmp:
            llc_path = Path(tmp) / "llc.0.symcov"
            opt_path = Path(tmp) / "opt.0.symcov"
            _write_symcov(
                llc_path,
                file_path=f,
                points={"0x1": "5:0", "0x2": "5:1"},
                covered=["0x1"],
            )
            _write_symcov(opt_path, file_path=f, points={"0x9": "99:0"}, covered=[])
            view = Sancov.load_joint_coverage(llc_path, opt_path, "AMDGPU")

        self.assertEqual(view.line_status[(f, 5)], "partial")

    def test_load_from_suite_dir_requires_symcov_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            suite_dir = Path(tmp)
            (suite_dir / "processed_sancov").mkdir()
            with self.assertRaises(SystemExit):
                Sancov.load_joint_coverage_from_suite_dir(suite_dir, "AMDGPU")


if __name__ == "__main__":
    unittest.main()
