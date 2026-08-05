"""Unit tests for line_rules helpers."""

from __future__ import annotations

import unittest

import pandas as pd

from coverage.constants import DEFAULT_SOURCE_CODE_FILTER
from coverage.line_rules import (
    filter_uncovered_lines,
    gap_address_line_map,
    normalize_llc_address_line_map,
)

FILE = "/build/llvm/llvm/lib/Foo.cpp"
OTHER_FILE = "/build/llvm/llvm/include/Bar.h"
LIBEXTRA_FILE = "/build/llvm/llvm/libextra/Baz.cpp"


class GapAddressLineMapTest(unittest.TestCase):
    def test_keeps_only_baseline_uncovered_lines_with_all_points(self) -> None:
        address_map = normalize_llc_address_line_map(
            pd.DataFrame(
                [
                    [FILE, 10, "0x1001"],
                    [FILE, 10, "0x1002"],
                    [FILE, 20, "0x2001"],
                    [FILE, 30, "0x3001"],
                ],
                columns=["file", "line", "point"],
            )
        )
        baseline_uncovered = frozenset({(FILE, 20), (FILE, 30)})

        gap = gap_address_line_map(address_map, baseline_uncovered)

        self.assertEqual(len(gap), 2)
        self.assertEqual(set(zip(gap["file"], gap["line"])), baseline_uncovered)
        self.assertNotIn(10, set(gap["line"]))

    def test_empty_baseline_uncovered_returns_empty_frame(self) -> None:
        address_map = normalize_llc_address_line_map(
            pd.DataFrame([[FILE, 10, "0x1001"]], columns=["file", "line", "point"])
        )
        gap = gap_address_line_map(address_map, frozenset())
        self.assertTrue(gap.empty)
        self.assertEqual(list(gap.columns), list(address_map.columns))


class FilterUncoveredLinesTest(unittest.TestCase):
    def test_empty_filter_keeps_all_lines(self) -> None:
        uncovered = frozenset({(FILE, 10), (OTHER_FILE, 20)})
        self.assertEqual(filter_uncovered_lines(uncovered, ""), uncovered)

    def test_default_filter_keeps_matching_files_only(self) -> None:
        uncovered = frozenset({(FILE, 10), (OTHER_FILE, 20), (FILE, 30)})
        filtered = filter_uncovered_lines(uncovered, DEFAULT_SOURCE_CODE_FILTER)
        self.assertEqual(filtered, frozenset({(FILE, 10), (FILE, 30)}))

    def test_default_filter_excludes_libextra_paths(self) -> None:
        uncovered = frozenset({(LIBEXTRA_FILE, 10), (FILE, 20)})
        filtered = filter_uncovered_lines(uncovered, DEFAULT_SOURCE_CODE_FILTER)
        self.assertEqual(filtered, frozenset({(FILE, 20)}))

    def test_alternation_filter_keeps_matching_files_only(self) -> None:
        uncovered = frozenset({(FILE, 10), (OTHER_FILE, 20), (FILE, 30)})
        filtered = filter_uncovered_lines(
            uncovered, r"(?:^|/)llvm/lib/|(?:^|/)llvm/include/"
        )
        self.assertEqual(filtered, uncovered)

    def test_non_matching_regex_excludes_all_lines(self) -> None:
        uncovered = frozenset({(FILE, 10), (OTHER_FILE, 20)})
        filtered = filter_uncovered_lines(uncovered, r"no/such/path/")
        self.assertEqual(filtered, frozenset())

    def test_invalid_regex_raises_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid source filter regex"):
            filter_uncovered_lines(frozenset({(FILE, 10)}), r"(")

    def test_gap_map_scopes_address_rows_to_filtered_uncovered(self) -> None:
        """Filtering uncovered lines is enough; gap merge excludes other paths."""
        address_map = normalize_llc_address_line_map(
            pd.DataFrame(
                [
                    [FILE, 10, "0x1001"],
                    [OTHER_FILE, 20, "0x2001"],
                    [FILE, 30, "0x3001"],
                ],
                columns=["file", "line", "point"],
            )
        )
        uncovered = filter_uncovered_lines(
            frozenset({(FILE, 10), (OTHER_FILE, 20), (FILE, 30)}),
            DEFAULT_SOURCE_CODE_FILTER,
        )
        gap = gap_address_line_map(address_map, uncovered)
        self.assertEqual(set(zip(gap["file"], gap["line"])), frozenset({(FILE, 10), (FILE, 30)}))


if __name__ == "__main__":
    unittest.main()
