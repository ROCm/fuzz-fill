"""Unit tests for periodic LLVM PR coverage checking helpers."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from pr_check.checker import (
    STATE_VERSION,
    DiscoveredPr,
    PrCheckerError,
    _aggregate_search_results,
    build_report_payload,
    count_csv_data_rows,
    count_lit_failures,
    diff_report_entries,
    entry_key,
    evaluate_output_dir,
    filter_report_payload,
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
            self.assertTrue(written["new_prs_md"].is_file())
            self.assertTrue(written["run_snapshot"].is_file())

            new_prs_text = written["new_prs_md"].read_text(encoding="utf-8")
            self.assertIn("new checks", new_prs_text)
            self.assertIn("#123", new_prs_text)


class ReportDeltaTest(unittest.TestCase):
    def _sample_entry(
        self,
        *,
        pr_number: int = 123,
        backend: str = "amdgpu",
        checked_at: str = "2026-07-29T18:00:00+00:00",
        head_sha: str = "abc123def456",
        status: str = "gaps",
        gap_count: int = 1,
    ) -> dict[str, object]:
        return {
            "key": entry_key(pr_number, backend),
            "pr_number": pr_number,
            "backend": backend,
            "title": "Fix foo",
            "head_sha": head_sha,
            "status": status,
            "gap_count": gap_count,
            "lit_failure_count": 0,
            "checked_at": checked_at,
            "output_dir": "/tmp/out",
            "error": None,
            "pr_url": f"https://github.com/llvm/llvm-project/pull/{pr_number}",
            "sample_gaps": [],
        }

    def _sample_payload(self, entries: list[dict[str, object]]) -> dict[str, object]:
        with_gaps = [entry for entry in entries if entry["status"] == "gaps"]
        failed = [entry for entry in entries if entry["status"] == "failed"]
        status_counts = {"gaps": 0, "clean": 0, "failed": 0}
        for entry in entries:
            status_counts[str(entry["status"])] += 1
        return {
            "generated_at": "2026-08-05T08:00:00+00:00",
            "github_repo": "llvm/llvm-project",
            "summary": {
                "total_entries": len(entries),
                "with_gaps": status_counts["gaps"],
                "clean": status_counts["clean"],
                "failed": status_counts["failed"],
            },
            "entries_with_gaps": with_gaps,
            "failed_entries": failed,
            "all_entries": entries,
        }

    def test_diff_detects_new_and_changed_entries(self) -> None:
        previous = self._sample_payload(
            [
                self._sample_entry(pr_number=1, checked_at="2026-01-01T00:00:00+00:00"),
                self._sample_entry(
                    pr_number=2,
                    backend="spirv",
                    status="clean",
                    gap_count=0,
                    checked_at="2026-01-01T00:00:00+00:00",
                ),
            ]
        )
        current = self._sample_payload(
            [
                self._sample_entry(
                    pr_number=1,
                    checked_at="2026-01-02T00:00:00+00:00",
                    head_sha="updated-sha",
                ),
                self._sample_entry(
                    pr_number=2,
                    backend="spirv",
                    status="clean",
                    gap_count=0,
                    checked_at="2026-01-01T00:00:00+00:00",
                ),
                self._sample_entry(pr_number=3, checked_at="2026-01-02T00:00:00+00:00"),
            ]
        )

        changed = diff_report_entries(current, previous)
        self.assertEqual(changed, {"1:amdgpu", "3:amdgpu"})

    def test_diff_without_previous_treats_all_entries_as_new(self) -> None:
        current = self._sample_payload([self._sample_entry()])
        self.assertEqual(diff_report_entries(current, None), {"123:amdgpu"})

    def test_filter_report_payload_recomputes_summary(self) -> None:
        payload = self._sample_payload(
            [
                self._sample_entry(pr_number=1),
                self._sample_entry(
                    pr_number=2,
                    status="clean",
                    gap_count=0,
                    checked_at="2026-01-01T00:00:00+00:00",
                ),
            ]
        )
        filtered = filter_report_payload(payload, {"1:amdgpu"})
        self.assertEqual(filtered["summary"]["total_entries"], 1)
        self.assertEqual(filtered["summary"]["with_gaps"], 1)
        self.assertEqual(len(filtered["all_entries"]), 1)

    def test_write_reports_emits_delta_against_previous_latest_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp) / "reports"
            previous = self._sample_payload([self._sample_entry(pr_number=1)])
            current = self._sample_payload(
                [
                    self._sample_entry(pr_number=1),
                    self._sample_entry(
                        pr_number=2,
                        status="clean",
                        gap_count=0,
                        checked_at="2026-08-05T09:00:00+00:00",
                    ),
                ]
            )

            write_reports(report_dir, previous, write_run_snapshot=False)
            written = write_reports(report_dir, current, write_run_snapshot=False)

            new_prs_text = written["new_prs_md"].read_text(encoding="utf-8")
            self.assertIn("New or updated since last report: 1 PR/backend pair(s)", new_prs_text)
            self.assertIn("1 clean", new_prs_text)
            self.assertNotIn("#1", new_prs_text)

    def test_write_reports_with_no_changes_writes_empty_delta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp) / "reports"
            payload = self._sample_payload([self._sample_entry()])

            write_reports(report_dir, payload, write_run_snapshot=False)
            written = write_reports(report_dir, payload, write_run_snapshot=False)

            new_prs_text = written["new_prs_md"].read_text(encoding="utf-8")
            self.assertIn(
                "No PRs with coverage gaps or failed checks since the last report.",
                new_prs_text,
            )
            self.assertIn("0 PR/backend pair(s)", new_prs_text)

    def test_render_report_markdown_delta_mode(self) -> None:
        payload = self._sample_payload([self._sample_entry()])
        markdown = render_report_markdown(payload, delta=True)
        self.assertIn("# LLVM PR coverage gap report — new checks", markdown)
        self.assertIn("New or updated since last report:", markdown)


class DiscoverPrsTest(unittest.TestCase):
    def test_backend_search_terms_include_label_and_age_filter_for_amdgpu(self) -> None:
        from pr_check.checker import _backend_search_terms

        terms = _backend_search_terms("amdgpu", max_age_days=30)
        self.assertEqual(len(terms), 1)
        self.assertIn('label:"backend:AMDGPU"', terms[0])
        self.assertRegex(terms[0], r'created:>\d{4}-\d{2}-\d{2}')

    def test_pr_touches_backend_path_matches_target_prefix(self) -> None:
        from pr_check.checker import _pr_touches_backend_path

        pr_view = {
            "files": [
                {"path": "clang/test/CodeGenHIP/foo.hip"},
                {"path": "llvm/lib/Target/AMDGPU/Foo.cpp"},
            ]
        }
        self.assertTrue(_pr_touches_backend_path(pr_view, "amdgpu"))
        self.assertFalse(_pr_touches_backend_path(pr_view, "spirv"))

    def test_merge_search_items_deduplicates_by_pr_number(self) -> None:
        from pr_check.checker import _merge_search_items

        merged = _merge_search_items(
            [
                [{"number": 10, "title": "From path", "updatedAt": "2026-01-01"}],
                [{"number": 10, "title": "", "updatedAt": "2026-01-03"}, {"number": 5, "title": "Label only", "updatedAt": "2026-01-02"}],
            ]
        )

        self.assertEqual([item["number"] for item in merged], [5, 10])
        self.assertEqual(merged[1]["updatedAt"], "2026-01-03")
        self.assertEqual(merged[1]["title"], "From path")

    def _pr_view_with_target_files(self) -> dict[str, object]:
        return {
            "headRefOid": "deadbeef",
            "title": "Test PR",
            "updatedAt": "2026-01-02",
            "files": [
                {"path": "llvm/lib/Target/AMDGPU/Foo.cpp"},
                {"path": "llvm/lib/Target/SPIRV/Bar.cpp"},
            ],
        }

    def test_discover_prs_resolves_head_sha_from_pr_view(self) -> None:
        from pr_check.checker import discover_prs

        def fake_search(backend: str, **kwargs: object) -> list[dict[str, object]]:
            return [{"number": 99, "title": "Test PR", "updatedAt": "2026-01-01"}]

        with mock.patch("pr_check.checker._search_backend_prs", side_effect=fake_search):
            with mock.patch(
                "pr_check.checker._view_pr",
                return_value=self._pr_view_with_target_files(),
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
                return_value=self._pr_view_with_target_files(),
            ):
                discovered = discover_prs(limit=1, backends=["amdgpu"])

        self.assertEqual(searched, ["amdgpu"])
        self.assertEqual(discovered[0].backends, ["amdgpu"])

    def test_discover_prs_skips_prs_without_target_path_changes(self) -> None:
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
                    "files": [{"path": "clang/test/CodeGenHIP/foo.hip"}],
                },
            ):
                discovered = discover_prs(limit=1, backends=["amdgpu"])

        self.assertEqual(discovered, [])


if __name__ == "__main__":
    unittest.main()
