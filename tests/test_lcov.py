"""Unit tests for LCOV-to-line-summary parsing."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coverage.lcov import parse_lcov_to_summary


class ParseLcovToSummaryTest(unittest.TestCase):
    def test_parses_counts_and_canonicalizes_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            llvm_src = Path(tmp) / "llvm-project"
            source = llvm_src / "llvm" / "lib" / "Foo.cpp"
            source.parent.mkdir(parents=True)
            source.write_text("x\n", encoding="utf-8")
            outside = Path(tmp) / "outside.cpp"
            outside.write_text("x\n", encoding="utf-8")

            frame = parse_lcov_to_summary(
                "\n".join(
                    [
                        f"SF:{source}",
                        "DA:10,0",
                        "DA:11,7",
                        "DA:not-a-line,1",
                        "end_of_record",
                        "SF:llvm/lib/Foo.cpp",
                        "DA:10,3",
                        "end_of_record",
                        f"SF:{outside}",
                        "DA:1,9",
                        "end_of_record",
                    ]
                ),
                llvm_src=llvm_src,
            )

        rows = {
            (row.file, int(row.line)): row.coverage
            for row in frame.itertuples(index=False)
        }
        self.assertEqual(
            rows,
            {
                ("llvm/lib/Foo.cpp", 10): "covered",
                ("llvm/lib/Foo.cpp", 11): "covered",
            },
        )

    def test_empty_input_has_expected_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frame = parse_lcov_to_summary("", llvm_src=Path(tmp))

        self.assertEqual(list(frame.columns), ["file", "line", "coverage"])
        self.assertTrue(frame.empty)


if __name__ == "__main__":
    unittest.main()
