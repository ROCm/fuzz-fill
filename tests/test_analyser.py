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
    DEFAULT_LINE_COVERAGE_UNCOVERED_FILE,
    DEFAULT_NEW_COVERAGE_CSV,
    DEFAULT_SOURCE_CODE_FILTER,
)
from coverage.filepaths import Filepaths
from coverage.sancov import Sancov

FILE = "/build/llvm/llvm/lib/Foo.cpp"
OTHER_FILE = "/build/llvm/llvm/include/Bar.h"
NEW_TEST = "test_0_example.ll"
# Stand-in for Sancov.get_covered_addresses(): new test hits every point on lines 10–30.
NEW_TEST_POINTS = {"0x1001", "0x1002", "0x2001", "0x2002", "0x3001"}


def _write_csv(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


class DiffPartialBaselineTest(unittest.TestCase):
    def test_partial_baseline_line_fully_covered_by_new_test_is_not_reported(self) -> None:
        """Diff reports only baseline ``uncovered`` lines, not partial ones the new test completes."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            suite = root / "test_suite"
            new_tests = root / "new_tests"
            diff = root / "diff"
            suite.mkdir()
            new_tests.mkdir()
            (new_tests / NEW_TEST).mkdir()

            uncovered_csv = suite / DEFAULT_LINE_COVERAGE_UNCOVERED_FILE
            map_csv = suite / DEFAULT_LLC_ADDRESS_LINE_MAP_FILE

            # Line 10: covered; line 20: partially; line 30: uncovered.
            _write_csv(
                uncovered_csv,
                [
                    ["file", "line"],
                    [FILE, 30],
                ],
            )
            _write_csv(
                map_csv,
                [
                    ["file", "line", "point"],
                    [FILE, 10, "0x1001"],
                    [FILE, 10, "0x1002"],
                    [FILE, 20, "0x2001"],
                    [FILE, 20, "0x2002"],
                    [FILE, 30, "0x3001"],
                ],
            )

            filepaths = Filepaths(
                output_dir=diff,
                output_candidate_tests_dir=new_tests,
                sancov=Path("/unused/sancov"),
                line_coverage_uncovered_csv=uncovered_csv,
                llc_address_line_map_csv=map_csv,
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

            # Core check: only baseline ``uncovered`` lines count as new coverage.
            # Line 20 is fully hit by the new test but was ``partially`` in the suite, so skip it.
            reported_lines = {int(row["line"]) for row in rows}
            self.assertEqual(reported_lines, {30})
            self.assertNotIn(20, reported_lines)

            self.assertEqual(rows[0]["covered-points"], "0x3001")

    def test_reads_baseline_uncovered_csv(self) -> None:
        """Incremental uses ``line_coverage_uncovered.csv``."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            suite = root / "test_suite"
            new_tests = root / "new_tests"
            diff = root / "diff"
            suite.mkdir()
            new_tests.mkdir()
            (new_tests / NEW_TEST).mkdir()

            uncovered_csv = suite / DEFAULT_LINE_COVERAGE_UNCOVERED_FILE
            map_csv = suite / DEFAULT_LLC_ADDRESS_LINE_MAP_FILE

            _write_csv(
                uncovered_csv,
                [
                    ["file", "line"],
                    [FILE, 30],
                ],
            )
            _write_csv(
                map_csv,
                [
                    ["file", "line", "point"],
                    [FILE, 30, "0x3001"],
                ],
            )

            filepaths = Filepaths(
                output_dir=diff,
                output_candidate_tests_dir=new_tests,
                sancov=Path("/unused/sancov"),
                line_coverage_uncovered_csv=uncovered_csv,
                llc_address_line_map_csv=map_csv,
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

            self.assertEqual({int(row["line"]) for row in rows}, {30})

    def test_source_filter_excludes_uncovered_lines_outside_filter(self) -> None:
        """Incremental --source-filter scopes gaps without pre-filtering the address map."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            suite = root / "test_suite"
            new_tests = root / "new_tests"
            diff = root / "diff"
            suite.mkdir()
            new_tests.mkdir()
            (new_tests / NEW_TEST).mkdir()

            uncovered_csv = suite / DEFAULT_LINE_COVERAGE_UNCOVERED_FILE
            map_csv = suite / DEFAULT_LLC_ADDRESS_LINE_MAP_FILE

            _write_csv(
                uncovered_csv,
                [
                    ["file", "line"],
                    [FILE, 30],
                    [OTHER_FILE, 40],
                ],
            )
            _write_csv(
                map_csv,
                [
                    ["file", "line", "point"],
                    [FILE, 30, "0x3001"],
                    [OTHER_FILE, 40, "0x4001"],
                ],
            )

            filepaths = Filepaths(
                output_dir=diff,
                output_candidate_tests_dir=new_tests,
                sancov=Path("/unused/sancov"),
                line_coverage_uncovered_csv=uncovered_csv,
                llc_address_line_map_csv=map_csv,
                new_coverage_csv=DEFAULT_NEW_COVERAGE_CSV,
            )

            with (
                patch.object(Sancov, "get_covered_addresses", return_value={"0x3001", "0x4001"}),
                patch(
                    "coverage.analyser.get_sancov_file",
                    return_value=new_tests / NEW_TEST / "llc.1.sancov",
                ),
            ):
                CoverageAnalyzer(
                    filepaths,
                    mode="full",
                    source_filter=DEFAULT_SOURCE_CODE_FILTER,
                ).get_incremental_coverage()

            with (diff / DEFAULT_NEW_COVERAGE_CSV).open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["file"], FILE)
            self.assertEqual(int(rows[0]["line"]), 30)


class PruneUninterestingSancovTest(unittest.TestCase):
    def test_removes_sancov_when_no_gap_points_are_hit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            suite = root / "test_suite"
            new_tests = root / "new_tests"
            diff = root / "diff"
            suite.mkdir()
            new_tests.mkdir()
            test_dir = new_tests / NEW_TEST
            test_dir.mkdir()
            sancov_path = test_dir / "llc.1.sancov"
            sancov_path.write_bytes(b"unused")

            uncovered_csv = suite / DEFAULT_LINE_COVERAGE_UNCOVERED_FILE
            map_csv = suite / DEFAULT_LLC_ADDRESS_LINE_MAP_FILE

            _write_csv(
                uncovered_csv,
                [
                    ["file", "line"],
                    [FILE, 30],
                ],
            )
            _write_csv(
                map_csv,
                [
                    ["file", "line", "point"],
                    [FILE, 30, "0x3001"],
                ],
            )

            filepaths = Filepaths(
                output_dir=diff,
                output_candidate_tests_dir=new_tests,
                sancov=Path("/unused/sancov"),
                line_coverage_uncovered_csv=uncovered_csv,
                llc_address_line_map_csv=map_csv,
                new_coverage_csv=DEFAULT_NEW_COVERAGE_CSV,
            )

            with (
                patch.object(Sancov, "get_covered_addresses", return_value={"0x9999"}),
                patch(
                    "coverage.analyser.get_sancov_file",
                    return_value=sancov_path,
                ),
            ):
                CoverageAnalyzer(filepaths, mode="full").get_incremental_coverage()

            self.assertFalse(sancov_path.exists())

            with (diff / DEFAULT_NEW_COVERAGE_CSV).open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

            self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
