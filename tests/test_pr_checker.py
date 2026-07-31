"""Unit tests for periodic LLVM PR coverage checking helpers."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pr_check.checker import (  # noqa: E402
    STATE_VERSION,
    DiscoveredPr,
    PrCheckerError,
    _aggregate_search_results,
    build_report_payload,
    count_csv_data_rows,
    count_lit_failures,
    entry_key,
    evaluate_output_dir,
    load_gap_rows,
    load_state,
    plan_work,
    record_result,
    render_report_markdown,
    save_state,
    write_reports,
)


def _write_gap_csv(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


class EntryKeyTest(unittest.TestCase):
    def test_formats_pr_and_backend(self) -> None:
        self.assertEqual(entry_key(203468, "amdgpu"), "203468:amdgpu")


class StateFileTest(unittest.TestCase):
    def test_load_missing_state_returns_empty_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = load_state(Path(tmp) / "state.json")
        self.assertEqual(state["version"], STATE_VERSION)
        self.assertEqual(state["entries"], {})

    def test_save_and_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            state = {"version": STATE_VERSION, "entries": {}}
            record_result(
                state,
                pr_number=42,
                backend="spirv",
                title="SPIR-V fix",
                head_sha="abc123",
                status="clean",
                gap_count=0,
                lit_failure_count=0,
                output_dir="/tmp/out",
            )
            save_state(path, state)
            loaded = load_state(path)

        self.assertIn("42:spirv", loaded["entries"])
        self.assertEqual(loaded["entries"]["42:spirv"]["status"], "clean")

    def test_unsupported_version_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text(json.dumps({"version": 99, "entries": {}}), encoding="utf-8")
            with self.assertRaises(PrCheckerError):
                load_state(path)


class PlanWorkTest(unittest.TestCase):
    def test_queues_new_and_head_changed_items_only(self) -> None:
        discovered = [
            DiscoveredPr(
                pr_number=1,
                title="A",
                head_sha="sha-new",
                updated_at="2026-01-01",
                backends=["amdgpu", "spirv"],
            ),
            DiscoveredPr(
                pr_number=2,
                title="B",
                head_sha="same-sha",
                updated_at="2026-01-01",
                backends=["amdgpu"],
            ),
        ]
        state = {
            "version": STATE_VERSION,
            "entries": {
                "1:amdgpu": {
                    "pr_number": 1,
                    "backend": "amdgpu",
                    "title": "A",
                    "head_sha": "sha-old",
                    "status": "gaps",
                    "gap_count": 3,
                    "lit_failure_count": 0,
                    "checked_at": "2026-01-01T00:00:00+00:00",
                    "output_dir": "/tmp/1-amdgpu",
                    "error": None,
                },
                "2:amdgpu": {
                    "pr_number": 2,
                    "backend": "amdgpu",
                    "title": "B",
                    "head_sha": "same-sha",
                    "status": "clean",
                    "gap_count": 0,
                    "lit_failure_count": 0,
                    "checked_at": "2026-01-01T00:00:00+00:00",
                    "output_dir": "/tmp/2-amdgpu",
                    "error": None,
                },
            },
        }

        work = plan_work(discovered, state)
        reasons = {(item.pr_number, item.backend): item.reason for item in work}

        self.assertEqual(reasons[(1, "amdgpu")], "head_changed")
        self.assertEqual(reasons[(1, "spirv")], "new")
        self.assertNotIn((2, "amdgpu"), reasons)


class AggregateSearchResultsTest(unittest.TestCase):
    def test_merges_backends_for_same_pr(self) -> None:
        frame = pd.DataFrame(
            [
                {"number": 10, "title": "AMDGPU pass", "updatedAt": "2026-01-01", "backend": "amdgpu"},
                {"number": 10, "title": "", "updatedAt": "2026-01-03", "backend": "spirv"},
                {"number": 5, "title": "SPIR-V only", "updatedAt": "2026-01-02", "backend": "spirv"},
            ]
        )
        aggregated = _aggregate_search_results(frame)

        self.assertEqual(aggregated["pr_number"].tolist(), [5, 10])
        row_10 = aggregated.loc[aggregated["pr_number"] == 10].iloc[0]
        self.assertEqual(row_10["backends"], ["amdgpu", "spirv"])
        self.assertEqual(row_10["title"], "AMDGPU pass")
        self.assertEqual(row_10["updated_at"], "2026-01-03")


class GapCsvHelpersTest(unittest.TestCase):
    def test_count_and_load_gap_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gap_csv = Path(tmp) / "target_lines_uncovered.csv"
            _write_gap_csv(
                gap_csv,
                [
                    ["file", "line_no", "text"],
                    ["llvm/lib/Target/AMDGPU/Foo.cpp", "10", "return x;"],
                    ["llvm/lib/Target/AMDGPU/Foo.cpp", "11", "return y;"],
                ],
            )

            self.assertEqual(count_csv_data_rows(gap_csv), 2)
            rows = load_gap_rows(gap_csv, max_rows=1)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["line_no"], "10")

    def test_count_lit_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lit_path = Path(tmp) / "lit_failures.json"
            lit_path.write_text(
                json.dumps({"tests": [{"code": "FAIL"}, {"code": "PASS"}]}),
                encoding="utf-8",
            )
            self.assertEqual(count_lit_failures(lit_path), 1)


class EvaluateOutputDirTest(unittest.TestCase):
    def test_reports_gaps_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_gap_csv(
                root / "commit_lines_report" / "target_lines_uncovered.csv",
                [["file", "line_no", "text"], ["llvm/Foo.cpp", "1", "x = 1;"]],
            )
            result = evaluate_output_dir(root)

        self.assertEqual(result["gap_count"], 1)
        self.assertEqual(result["status"], "gaps")


class ReportGenerationTest(unittest.TestCase):
    def test_build_render_and_write_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run-123-amdgpu"
            _write_gap_csv(
                run_dir / "commit_lines_report" / "target_lines_uncovered.csv",
                [
                    ["file", "line_no", "text"],
                    ["llvm/lib/Target/AMDGPU/Foo.cpp", "10", "return x;"],
                ],
            )
            state = {
                "version": STATE_VERSION,
                "entries": {
                    "123:amdgpu": {
                        "pr_number": 123,
                        "backend": "amdgpu",
                        "title": "Fix foo",
                        "head_sha": "abc123def456",
                        "status": "gaps",
                        "gap_count": 1,
                        "lit_failure_count": 2,
                        "checked_at": "2026-07-29T18:00:00+00:00",
                        "output_dir": str(run_dir),
                        "error": None,
                    }
                },
            }

            payload = build_report_payload(state)
            self.assertEqual(payload["summary"]["with_gaps"], 1)
            self.assertEqual(payload["entries_with_gaps"][0]["sample_gaps"][0]["line_no"], "10")

            markdown = render_report_markdown(payload)
            self.assertIn("#123", markdown)
            self.assertIn("LIT failure", markdown)

            report_dir = root / "reports"
            written = write_reports(report_dir, payload, write_run_snapshot=True)
            self.assertTrue(written["latest_json"].is_file())
            self.assertTrue(written["latest_md"].is_file())
            self.assertTrue(written["run_snapshot"].is_file())


class DiscoverPrsTest(unittest.TestCase):
    def test_backend_search_query_includes_opened_within_filter(self) -> None:
        from pr_check.checker import _backend_search_query

        query = _backend_search_query("amdgpu", max_age_days=30)
        self.assertIn('path:"llvm/lib/Target/AMDGPU"', query)
        self.assertRegex(query, r'created:>\d{4}-\d{2}-\d{2}')

    def test_discover_prs_resolves_head_sha_from_pr_view(self) -> None:
        from pr_check.checker import discover_prs

        def fake_search(backend: str, **kwargs: object) -> list[dict[str, object]]:
            return [{"number": 99, "title": "Test PR", "updatedAt": "2026-01-01"}]

        with mock.patch("pr_check.checker._search_backend_prs", side_effect=fake_search):
            with mock.patch(
                "pr_check.checker._view_pr",
                return_value={
                    "headRefOid": "deadbeef",
                    "title": "Test PR",
                    "updatedAt": "2026-01-02",
                },
            ):
                discovered = discover_prs(limit=1)

        self.assertEqual(len(discovered), 1)
        self.assertEqual(discovered[0].pr_number, 99)
        self.assertEqual(discovered[0].head_sha, "deadbeef")
        self.assertEqual(discovered[0].backends, ["amdgpu", "spirv"])

    def test_discover_prs_honors_backends_filter(self) -> None:
        from pr_check.checker import discover_prs

        searched: list[str] = []

        def fake_search(backend: str, **kwargs: object) -> list[dict[str, object]]:
            searched.append(backend)
            return [{"number": 99, "title": "Test PR", "updatedAt": "2026-01-01"}]

        with mock.patch("pr_check.checker._search_backend_prs", side_effect=fake_search):
            with mock.patch(
                "pr_check.checker._view_pr",
                return_value={
                    "headRefOid": "deadbeef",
                    "title": "Test PR",
                    "updatedAt": "2026-01-02",
                },
            ):
                discovered = discover_prs(limit=1, backends=["amdgpu"])

        self.assertEqual(searched, ["amdgpu"])
        self.assertEqual(discovered[0].backends, ["amdgpu"])


if __name__ == "__main__":
    unittest.main()
