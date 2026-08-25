import csv
import tempfile
import unittest
from pathlib import Path

from pr_check.gap_loader import iter_uncovered_gap_lines


def _write_gap_csv(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


class IterUncoveredGapLinesTests(unittest.TestCase):
    def test_yields_lines_from_completed_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "217396-amdgpu"
            _write_gap_csv(
                run_dir / "commit_lines_report" / "target_lines_uncovered.csv",
                [
                    ["file", "line", "text"],
                    ["/work/llvm-project/llvm/lib/Foo.cpp", "2832", "MI.build();"],
                ],
            )

            gaps = list(iter_uncovered_gap_lines(root))

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].pr_number, 217396)
        self.assertEqual(gaps[0].backend, "amdgpu")
        self.assertEqual(gaps[0].line, 2832)
        self.assertEqual(gaps[0].text, "MI.build();")

    def test_skips_incomplete_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "999999-amdgpu").mkdir()

            gaps = list(iter_uncovered_gap_lines(root))

        self.assertEqual(gaps, [])

    def test_accepts_line_no_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "42-spirv"
            _write_gap_csv(
                run_dir / "commit_lines_report" / "target_lines_uncovered.csv",
                [
                    ["file", "line_no", "text"],
                    ["/work/llvm-project/llvm/lib/Bar.cpp", "10", "return;"],
                ],
            )

            gaps = list(iter_uncovered_gap_lines(root))

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].line, 10)
