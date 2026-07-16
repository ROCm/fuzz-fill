"""Unit tests for per-line coverage summary classification."""

from __future__ import annotations

import unittest

import pandas as pd

from coverage.sancov import Sancov

FILE = "/llvm/Foo.cpp"
FILE_B = "/llvm/Bar.cpp"


def _coverage_df(rows: list[tuple[str, int, str, int]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["file", "line", "point", "covered"])


def _join_points(points: list[str]) -> str:
    return ";".join(sorted(set(points)))


def _line_point_summary_from_address_map(
    address_line_map: pd.DataFrame, *, point_column: str = "point"
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (file, line), group in address_line_map.groupby(["file", "line"], sort=False):
        all_pts = group[point_column].dropna().astype(str).tolist()
        covered_pts = (
            group.loc[group["covered"] == 1, point_column].dropna().astype(str).tolist()
        )
        rows.append(
            {
                "file": file,
                "line": int(line),
                "covered_points": _join_points(covered_pts),
                "all_points": _join_points(all_pts),
            }
        )
    return pd.DataFrame(rows).sort_values(["file", "line"]).reset_index(drop=True)


def _coverage_from_line_point_summaries(summaries: list[pd.DataFrame]) -> pd.DataFrame:
    per_tool: list[pd.DataFrame] = []
    for summary in summaries:
        tool = summary.copy()
        tool["line"] = tool["line"].astype(int)
        tool["tool_points"] = tool["all_points"].map(
            lambda s: len([p for p in str(s).split(";") if p])
        )
        tool["tool_covered"] = tool["covered_points"].map(
            lambda s: len([p for p in str(s).split(";") if p])
        )
        tool["tool_full"] = (tool["tool_covered"] == tool["tool_points"]) & (
            tool["tool_points"] > 0
        )
        per_tool.append(tool[["file", "line", "tool_covered", "tool_full"]])

    combined = pd.concat(per_tool, ignore_index=True)
    agg = combined.groupby(["file", "line"], as_index=False).agg(
        total_covered=("tool_covered", "sum"),
        any_tool_full=("tool_full", "any"),
    )
    agg["coverage"] = pd.Series(
        "partially",
        index=agg.index,
    )
    agg.loc[agg["total_covered"] == 0, "coverage"] = "uncovered"
    agg.loc[agg["any_tool_full"], "coverage"] = "covered"
    return agg[["file", "line", "coverage"]].sort_values(["file", "line"]).reset_index(
        drop=True
    )


def _summary_map(dfs: list[pd.DataFrame]) -> dict[tuple[str, int], str]:
    summary = Sancov.build_coverage_summary(dfs)
    return {
        (row.file, int(row.line)): row.coverage
        for row in summary.itertuples(index=False)
    }


class BuildCoverageSummaryTest(unittest.TestCase):
    def test_empty_input(self) -> None:
        summary = Sancov.build_coverage_summary([])
        self.assertEqual(list(summary.columns), ["file", "line", "coverage"])
        self.assertTrue(summary.empty)

    def test_rejects_duplicate_points_on_same_line(self) -> None:
        llc = _coverage_df([(FILE, 10, "0x1001", 1), (FILE, 10, "0x1001", 0)])
        with self.assertRaises(AssertionError):
            Sancov.build_coverage_summary([llc])

    def test_uncovered_when_all_tools_miss(self) -> None:
        llc = _coverage_df([(FILE, 10, "0x1001", 0), (FILE, 10, "0x1002", 0)])
        opt = _coverage_df([(FILE, 10, "0x2001", 0)])
        result = _summary_map([llc, opt])
        self.assertEqual(result[(FILE, 10)], "uncovered")

    def test_covered_when_one_tool_fully_covers(self) -> None:
        llc = _coverage_df([(FILE, 10, "0x1001", 1), (FILE, 10, "0x1002", 1)])
        opt = _coverage_df([(FILE, 10, "0x2001", 0), (FILE, 10, "0x2002", 0)])
        result = _summary_map([llc, opt])
        self.assertEqual(result[(FILE, 10)], "covered")

    def test_partially_when_some_hits_but_no_tool_fully_covers(self) -> None:
        llc = _coverage_df([(FILE, 10, "0x1001", 1), (FILE, 10, "0x1002", 0)])
        opt = _coverage_df([(FILE, 10, "0x2001", 0), (FILE, 10, "0x2002", 0)])
        result = _summary_map([llc, opt])
        self.assertEqual(result[(FILE, 10)], "partially")

    def test_one_tool_only_line_judged_on_that_tool(self) -> None:
        llc = _coverage_df([(FILE, 10, "0x1001", 1), (FILE, 10, "0x1002", 1)])
        opt = _coverage_df([(FILE, 20, "0x2001", 0)])
        result = _summary_map([llc, opt])
        self.assertEqual(result[(FILE, 10)], "covered")
        self.assertEqual(result[(FILE, 20)], "uncovered")

    def test_mixed_lines(self) -> None:
        llc = _coverage_df(
            [
                (FILE, 10, "0x1001", 1),
                (FILE, 10, "0x1002", 1),
                (FILE, 20, "0x2001", 1),
                (FILE, 20, "0x2002", 0),
                (FILE, 30, "0x3001", 0),
                (FILE, 30, "0x3002", 0),
            ]
        )
        opt = _coverage_df(
            [
                (FILE, 10, "0x1101", 0),
                (FILE, 10, "0x1102", 0),
                (FILE, 20, "0x2101", 0),
                (FILE, 20, "0x2102", 0),
                (FILE, 30, "0x3101", 0),
                (FILE, 30, "0x3102", 0),
            ]
        )
        result = _summary_map([llc, opt])
        self.assertEqual(result[(FILE, 10)], "covered")
        self.assertEqual(result[(FILE, 20)], "partially")
        self.assertEqual(result[(FILE, 30)], "uncovered")


def _address_line_map(rows: list[tuple[str, int, str, int]]) -> pd.DataFrame:
    return Sancov.build_address_line_map(_coverage_df(rows))


class BuildLinePointSummaryTest(unittest.TestCase):
    def test_empty_input(self) -> None:
        summary = Sancov.build_line_point_summary(
            pd.DataFrame(columns=["file", "line", "point", "covered"]),
        )
        self.assertEqual(
            list(summary.columns), ["file", "line", "covered_points", "all_points"]
        )
        self.assertTrue(summary.empty)

    def test_two_points_one_covered(self) -> None:
        address_map = _address_line_map(
            [(FILE, 10, "0x1002", 0), (FILE, 10, "0x1001", 1)]
        )
        summary = Sancov.build_line_point_summary(address_map)
        row = summary.iloc[0]
        self.assertEqual(row["all_points"], "0x1001;0x1002")
        self.assertEqual(row["covered_points"], "0x1001")

    def test_no_covered_points(self) -> None:
        address_map = _address_line_map([(FILE, 10, "0x1001", 0), (FILE, 10, "0x1002", 0)])
        summary = Sancov.build_line_point_summary(address_map)
        row = summary.iloc[0]
        self.assertEqual(row["all_points"], "0x1001;0x1002")
        self.assertEqual(row["covered_points"], "")

    def test_single_point_fully_covered(self) -> None:
        address_map = _address_line_map([(FILE, 10, "0x1001", 1)])
        summary = Sancov.build_line_point_summary(address_map)
        row = summary.iloc[0]
        self.assertEqual(row["all_points"], "0x1001")
        self.assertEqual(row["covered_points"], "0x1001")


class ConsistencyTest(unittest.TestCase):
    def test_line_point_summary_matches_address_line_map(self) -> None:
        """build_line_point_summary should match re-aggregating the address-line map by hand.

        The address-line map has one row per instrumentation point; the line point summary
        collapses those rows to one row per (file, line) with sorted semicolon-separated
        all_points and covered_points. Expected values are computed independently from the
        same map so the test checks that grouping/join logic did not drift.
        """
        # line 10: partial (one of two points covered)
        # line 20: fully covered
        # line 5 in another file: uncovered single point
        llc_rows = [
            (FILE, 10, "0x1002", 0),
            (FILE, 10, "0x1001", 1),
            (FILE, 20, "0x2001", 1),
            (FILE, 20, "0x2002", 1),
            (FILE_B, 5, "0x5001", 0),
        ]
        address_map = _address_line_map(llc_rows)
        actual = Sancov.build_line_point_summary(address_map)
        expected = _line_point_summary_from_address_map(address_map)
        actual = actual.sort_values(["file", "line"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(actual, expected)

    def test_coverage_summary_matches_line_point_summaries(self) -> None:
        llc = _coverage_df(
            [
                (FILE, 10, "0x1001", 1),
                (FILE, 10, "0x1002", 1),
                (FILE, 20, "0x2001", 1),
                (FILE, 20, "0x2002", 0),
                (FILE, 30, "0x3001", 0),
                (FILE, 30, "0x3002", 0),
            ]
        )
        opt = _coverage_df(
            [
                (FILE, 10, "0x1101", 0),
                (FILE, 10, "0x1102", 0),
                (FILE, 20, "0x2101", 0),
                (FILE, 20, "0x2102", 0),
                (FILE, 30, "0x3101", 0),
                (FILE, 30, "0x3102", 0),
            ]
        )
        llc_address_map = Sancov.build_address_line_map(llc)
        opt_address_map = Sancov.build_address_line_map(opt)
        llc_line_point_summary = Sancov.build_line_point_summary(llc_address_map)
        opt_line_point_summary = Sancov.build_line_point_summary(opt_address_map)

        actual = Sancov.build_coverage_summary([llc, opt])
        expected = _coverage_from_line_point_summaries(
            [llc_line_point_summary, opt_line_point_summary]
        )
        pd.testing.assert_frame_equal(actual, expected)


if __name__ == "__main__":
    unittest.main()
