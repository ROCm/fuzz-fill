"""Unit tests for incremental coverage diffing."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from coverage.analyser import CoverageAnalyzer
from coverage.constants import (
    DEFAULT_LLC_ADDRESS_LINE_MAP_FILE,
    DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
    DEFAULT_NEW_COVERAGE_CSV,
)
from coverage.filepaths import Filepaths
from coverage.sancov import Sancov

FILE = "/llvm/Foo.cpp"
NEW_TEST = "test_0_example.ll"
# Stand-in for Sancov.get_covered_addresses(): new test hits every point on lines 10–30.
NEW_TEST_POINTS = {"0x1001", "0x1002", "0x2001", "0x2002", "0x3001"}


def _write_csv(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


class DiffPartialBaselineTest(unittest.TestCase):
    def test_partial_baseline_line_fully_covered_by_new_test_is_not_reported(self) -> None:
        """Diff reports only baseline ``none`` lines, not partial ones the new test completes."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            suite = root / "test_suite"
            new_tests = root / "new_tests"
            diff = root / "diff"
            suite.mkdir()
            new_tests.mkdir()
            (new_tests / NEW_TEST).mkdir()

            # Line 10: full; line 20: partial; line 30: none.
            _write_csv(
                suite / DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
                [
                    ["file", "line", "coverage", "point_addresses"],
                    [FILE, 10, "full", "0x1001;0x1002"],
                    [FILE, 20, "partial", "0x2001;0x2002"],
                    [FILE, 30, "none", "0x3001"],
                ],
            )
            _write_csv(
                suite / DEFAULT_LLC_ADDRESS_LINE_MAP_FILE,
                [
                    ["file", "line", "point_llc"],
                    [FILE, 10, "0x1001"],
                    [FILE, 10, "0x1002"],
                    [FILE, 20, "0x2001"],
                    [FILE, 20, "0x2002"],
                    [FILE, 30, "0x3001"],
                ],
            )

            filepaths = Filepaths(
                output_dir=diff,
                output_baseline_dir=suite,
                output_candidate_tests_dir=new_tests,
                llvm_bin=Path("/unused"),
                llc_address_line_map_file=DEFAULT_LLC_ADDRESS_LINE_MAP_FILE,
                line_coverage_summary_file=DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
                new_coverage_csv=DEFAULT_NEW_COVERAGE_CSV,
            )

            with (
                patch.object(Sancov, "get_covered_addresses", return_value=NEW_TEST_POINTS),
                patch(
                    "coverage.analyser.get_sancov_file",
                    return_value=new_tests / NEW_TEST / "llc.1.sancov",
                ),
            ):
                CoverageAnalyzer(filepaths, mode="full").get_incremental_coverage()

            with (diff / DEFAULT_NEW_COVERAGE_CSV).open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

            # Core check: only baseline ``none`` lines count as new coverage.
            # Line 20 is fully hit by the new test but was ``partial`` in the suite, so skip it.
            reported_lines = {int(row["line"]) for row in rows}
            self.assertEqual(reported_lines, {30})
            self.assertNotIn(20, reported_lines)

            self.assertEqual(rows[0]["covered-points"], "0x3001")


if __name__ == "__main__":
    unittest.main()
