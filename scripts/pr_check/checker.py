#!/usr/bin/env python3
# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Discover, plan, and record periodic LLVM PR coverage-gap checks."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd

STATE_VERSION = 1
DEFAULT_GITHUB_REPO = "llvm/llvm-project"
DEFAULT_SEARCH_LIMIT = 100
DEFAULT_MAX_PR_AGE_DAYS = 30

BACKEND_SEARCH_QUERIES: dict[str, str] = {
    "amdgpu": 'path:"llvm/lib/Target/AMDGPU"',
    "spirv": 'path:"llvm/lib/Target/SPIRV"',
}

SEARCH_JSON_FIELDS = ["number", "title", "updatedAt"]
PR_VIEW_JSON_FIELDS = ["number", "title", "headRefOid", "updatedAt"]
LIT_FAILURE_CODES = frozenset({"FAIL", "TIMEOUT", "UNRESOLVED", "XPASS"})

LOG_FORMAT = "%(levelname)-8s %(message)s"
log = logging.getLogger("pr_check")


class PrCheckerError(Exception):
    """Error from PR checker operations."""


@dataclass(frozen=True)
class DiscoveredPr:
    """An open PR that touches at least one tracked backend."""

    pr_number: int
    title: str
    head_sha: str
    updated_at: str
    backends: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkItem:
    """A PR/backend pair that should be checked."""

    pr_number: int
    backend: str
    title: str
    head_sha: str
    reason: str


@dataclass
class StateEntry:
    """Persistent record for one PR/backend check."""

    pr_number: int
    backend: str
    title: str
    head_sha: str
    status: str
    gap_count: int
    lit_failure_count: int
    checked_at: str
    output_dir: str
    error: str | None = None


def entry_key(pr_number: int, backend: str) -> str:
    return f"{pr_number}:{backend}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def configure_logging(level: str = "info") -> None:
    """Send log records to stderr so stdout stays free for JSON payloads."""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise PrCheckerError(f"invalid log level: {level}")

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root = logging.getLogger("pr_check")
    root.handlers.clear()
    root.setLevel(numeric_level)
    root.addHandler(handler)
    root.propagate = False


def _validate_max_age_days(max_age_days: int) -> None:
    if max_age_days <= 0:
        raise PrCheckerError(f"max_age_days must be a positive integer: {max_age_days}")


def _search_created_since(max_age_days: int) -> str:
    """Return a YYYY-MM-DD date for GitHub ``created:>`` search qualifiers."""
    _validate_max_age_days(max_age_days)
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=max_age_days)
    return cutoff.isoformat()


def _backend_search_query(backend: str, *, max_age_days: int) -> str:
    """Build a gh search query for one backend, limited to recently opened PRs."""
    created_since = _search_created_since(max_age_days)
    return f'{BACKEND_SEARCH_QUERIES[backend]} created:>{created_since}'


def _require_gh() -> str:
    from shutil import which

    gh_path = which("gh")
    if gh_path is None:
        raise PrCheckerError("required command not found: gh")
    return gh_path


def _run_gh(args: list[str], *, timeout: int = 120) -> str:
    gh_path = _require_gh()
    log.debug("running gh %s", " ".join(args))
    try:
        result = subprocess.run(
            [gh_path, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PrCheckerError(f"gh command timed out after {timeout}s: {' '.join(args)}") from exc
    except OSError as exc:
        raise PrCheckerError(f"failed to run gh: {exc}") from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip() or "(no error message)"
        raise PrCheckerError(f"gh {' '.join(args)} failed: {stderr}")

    return result.stdout


def _gh_json(args: list[str], *, timeout: int = 120) -> Any:
    stdout = _run_gh([*args, "--json", ",".join(_json_fields_for_command(args))], timeout=timeout)
    if not stdout.strip():
        return []
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise PrCheckerError(f"gh returned invalid JSON: {exc.msg}") from exc


def _gh_api_json(endpoint: str) -> Any:
    stdout = _run_gh(["api", endpoint])
    if not stdout.strip():
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise PrCheckerError(f"gh api returned invalid JSON: {exc.msg}") from exc


def _normalize_search_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map GitHub issue-search items to the fields used elsewhere in this module."""
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "number": item.get("number"),
                "title": item.get("title") or "",
                "updatedAt": item.get("updated_at") or "",
            }
        )
    return normalized


def _json_fields_for_command(args: list[str]) -> list[str]:
    if args and args[0] == "search":
        return SEARCH_JSON_FIELDS
    if args and args[0] == "pr" and len(args) >= 2 and args[1] == "view":
        return PR_VIEW_JSON_FIELDS
    raise PrCheckerError(f"unsupported gh command for JSON parsing: {' '.join(args)}")


def _search_backend_prs(
    backend: str,
    *,
    github_repo: str = DEFAULT_GITHUB_REPO,
    limit: int = DEFAULT_SEARCH_LIMIT,
    max_age_days: int = DEFAULT_MAX_PR_AGE_DAYS,
) -> list[dict[str, Any]]:
    query = _backend_search_query(backend, max_age_days=max_age_days)
    search_query = f"repo:{github_repo} is:pr is:open {query}"
    log.info(
        "Searching %s PRs on %s (query=%r, limit=%d, max_age_days=%d)",
        backend,
        github_repo,
        search_query,
        limit,
        max_age_days,
    )
    payload = _gh_api_json(
        "search/issues?"
        + urlencode(
            {
                "q": search_query,
                "per_page": str(min(limit, 100)),
            }
        )
    )
    if not isinstance(payload, dict):
        raise PrCheckerError(f"unexpected gh api search payload for {backend}: {type(payload)!r}")
    items = _normalize_search_items(payload.get("items", []))
    log.info("Found %d open %s PR(s)", len(items), backend)
    return items[:limit]


def _view_pr(pr_number: int, github_repo: str) -> dict[str, Any]:
    payload = _gh_json(["pr", "view", str(pr_number), "--repo", github_repo])
    if not isinstance(payload, dict):
        raise PrCheckerError(f"unexpected gh pr view payload for #{pr_number}: {type(payload)!r}")
    return payload


def _search_results_dataframe(
    *,
    github_repo: str = DEFAULT_GITHUB_REPO,
    limit: int = DEFAULT_SEARCH_LIMIT,
    max_age_days: int = DEFAULT_MAX_PR_AGE_DAYS,
) -> pd.DataFrame:
    """Run backend searches and return one row per (PR, backend) match."""
    frames: list[pd.DataFrame] = []
    for backend in BACKEND_SEARCH_QUERIES:
        items = _search_backend_prs(
            backend,
            github_repo=github_repo,
            limit=limit,
            max_age_days=max_age_days,
        )
        if not items:
            continue
        frame = pd.DataFrame(items)
        frame["backend"] = backend
        frames.append(frame)

    if not frames:
        return pd.DataFrame(columns=["number", "title", "updatedAt", "backend"])

    return pd.concat(frames, ignore_index=True)


def _non_empty_first(values: pd.Series) -> str:
    for value in values:
        if pd.notna(value) and str(value):
            return str(value)
    return ""


def _aggregate_search_results(search_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse per-backend search hits to one row per PR."""
    if search_df.empty:
        return pd.DataFrame(columns=["pr_number", "title", "updated_at", "backends"])

    return (
        search_df.groupby("number", sort=True)
        .agg(
            title=("title", _non_empty_first),
            updated_at=("updatedAt", "max"),
            backends=("backend", lambda values: sorted(set(values))),
        )
        .reset_index()
        .rename(columns={"number": "pr_number"})
    )


def discover_prs(
    *,
    github_repo: str = DEFAULT_GITHUB_REPO,
    limit: int = DEFAULT_SEARCH_LIMIT,
    max_age_days: int = DEFAULT_MAX_PR_AGE_DAYS,
) -> list[DiscoveredPr]:
    """Find open PRs touching AMDGPU and/or SPIR-V target paths."""
    log.info(
        "Discovering open PRs on %s (limit=%d per backend, max_age_days=%d, backends=%s)",
        github_repo,
        limit,
        max_age_days,
        ", ".join(sorted(BACKEND_SEARCH_QUERIES)),
    )
    search_df = _search_results_dataframe(
        github_repo=github_repo,
        limit=limit,
        max_age_days=max_age_days,
    )
    grouped = _aggregate_search_results(search_df)
    if grouped.empty:
        log.info("No matching open PRs found")
        return []

    total = len(grouped)
    log.info(
        "Search returned %d unique PR(s); resolving head SHAs via gh pr view",
        total,
    )

    discovered: list[DiscoveredPr] = []
    for index, row in enumerate(grouped.itertuples(index=False), start=1):
        pr_number = int(row.pr_number)
        if index == 1 or index == total or index % 10 == 0:
            log.info("Resolving head SHA %d/%d: #%d", index, total, pr_number)
        else:
            log.debug("Resolving head SHA %d/%d: #%d", index, total, pr_number)

        pr_view = _view_pr(pr_number, github_repo)
        head_sha = pr_view.get("headRefOid")
        if not head_sha:
            raise PrCheckerError(f"could not resolve headRefOid for {github_repo}#{pr_number}")

        discovered.append(
            DiscoveredPr(
                pr_number=pr_number,
                title=pr_view.get("title") or row.title or "",
                head_sha=head_sha,
                updated_at=pr_view.get("updatedAt") or row.updated_at or "",
                backends=list(row.backends),
            )
        )

    log.info("Discovery complete: %d PR(s) with head SHAs", len(discovered))
    return discovered


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        log.info("State file not found, starting fresh: %s", path)
        return {"version": STATE_VERSION, "entries": {}}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PrCheckerError(f"invalid state file {path}: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise PrCheckerError(f"invalid state file {path}: expected object at top level")
    if payload.get("version") != STATE_VERSION:
        raise PrCheckerError(
            f"unsupported state version in {path}: {payload.get('version')!r} (expected {STATE_VERSION})"
        )
    if not isinstance(payload.get("entries"), dict):
        raise PrCheckerError(f"invalid state file {path}: missing entries object")

    log.info("Loaded state from %s (%d entries)", path, len(payload["entries"]))
    return payload


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log.info("Saved state to %s (%d entries)", path, len(state.get("entries", {})))


def _state_entry_from_dict(raw: dict[str, Any]) -> StateEntry:
    return StateEntry(
        pr_number=int(raw["pr_number"]),
        backend=str(raw["backend"]),
        title=str(raw.get("title", "")),
        head_sha=str(raw["head_sha"]),
        status=str(raw["status"]),
        gap_count=int(raw.get("gap_count", 0)),
        lit_failure_count=int(raw.get("lit_failure_count", 0)),
        checked_at=str(raw.get("checked_at", "")),
        output_dir=str(raw.get("output_dir", "")),
        error=raw.get("error"),
    )


def plan_work(discovered: list[DiscoveredPr], state: dict[str, Any]) -> list[WorkItem]:
    """Return PR/backend pairs that need a fresh coverage run."""
    entries: dict[str, Any] = state["entries"]
    work: list[WorkItem] = []
    pair_count = 0
    skipped_up_to_date = 0
    new_count = 0
    head_changed_count = 0

    log.info(
        "Planning work from %d discovered PR(s) against %d state entries",
        len(discovered),
        len(entries),
    )

    for pr in discovered:
        for backend in pr.backends:
            pair_count += 1
            key = entry_key(pr.pr_number, backend)
            existing = entries.get(key)
            if existing is None:
                new_count += 1
                work.append(
                    WorkItem(
                        pr_number=pr.pr_number,
                        backend=backend,
                        title=pr.title,
                        head_sha=pr.head_sha,
                        reason="new",
                    )
                )
                log.debug("Queued #%d (%s): new", pr.pr_number, backend)
                continue

            previous = _state_entry_from_dict(existing)
            if previous.head_sha != pr.head_sha:
                head_changed_count += 1
                work.append(
                    WorkItem(
                        pr_number=pr.pr_number,
                        backend=backend,
                        title=pr.title,
                        head_sha=pr.head_sha,
                        reason="head_changed",
                    )
                )
                log.debug(
                    "Queued #%d (%s): head changed %s -> %s",
                    pr.pr_number,
                    backend,
                    previous.head_sha[:12],
                    pr.head_sha[:12],
                )
            else:
                skipped_up_to_date += 1
                log.debug(
                    "Skipping #%d (%s): already checked at head %s",
                    pr.pr_number,
                    backend,
                    pr.head_sha[:12],
                )

    work.sort(key=lambda item: (item.pr_number, item.backend))
    log.info(
        "Plan summary: %d PR/backend pair(s) scanned, %d queued (%d new, %d head_changed), %d up-to-date",
        pair_count,
        len(work),
        new_count,
        head_changed_count,
        skipped_up_to_date,
    )
    for item in work:
        log.info(
            "  -> #%d (%s) [%s] head=%s",
            item.pr_number,
            item.backend,
            item.reason,
            item.head_sha[:12],
        )
    return work


def record_result(
    state: dict[str, Any],
    *,
    pr_number: int,
    backend: str,
    title: str,
    head_sha: str,
    status: str,
    gap_count: int,
    lit_failure_count: int,
    output_dir: str,
    error: str | None = None,
) -> None:
    key = entry_key(pr_number, backend)
    log.info(
        "Recording result for #%d (%s): status=%s gap_count=%d lit_failures=%d",
        pr_number,
        backend,
        status,
        gap_count,
        lit_failure_count,
    )
    state["entries"][key] = {
        "pr_number": pr_number,
        "backend": backend,
        "title": title,
        "head_sha": head_sha,
        "status": status,
        "gap_count": gap_count,
        "lit_failure_count": lit_failure_count,
        "checked_at": utc_now_iso(),
        "output_dir": output_dir,
        "error": error,
    }


def _discovered_to_json(discovered: list[DiscoveredPr]) -> list[dict[str, Any]]:
    return [
        {
            "pr_number": pr.pr_number,
            "title": pr.title,
            "head_sha": pr.head_sha,
            "updated_at": pr.updated_at,
            "backends": pr.backends,
        }
        for pr in discovered
    ]


def _work_to_json(work: list[WorkItem]) -> list[dict[str, Any]]:
    return [asdict(item) for item in work]


def _read_gap_csv(gap_csv: Path, *, max_rows: int | None = None) -> pd.DataFrame:
    """Load a target_lines_uncovered.csv file as a normalized DataFrame."""
    if not gap_csv.is_file():
        return pd.DataFrame(columns=["file", "line_no", "text"])

    frame = pd.read_csv(gap_csv, nrows=max_rows)
    if frame.empty:
        return pd.DataFrame(columns=["file", "line_no", "text"])

    for column in ("file", "line_no", "text"):
        if column not in frame.columns:
            frame[column] = ""

    normalized = frame[["file", "line_no", "text"]].fillna("").astype(str)
    return normalized.apply(lambda series: series.str.strip())


def count_csv_data_rows(path: Path) -> int:
    """Return the number of data rows in a CSV file (excluding the header)."""
    return len(_read_gap_csv(path))


def load_gap_rows(gap_csv: Path, *, max_rows: int = 20) -> list[dict[str, str]]:
    """Read uncovered line rows from a target_lines_uncovered.csv file."""
    if max_rows <= 0:
        return []

    frame = _read_gap_csv(gap_csv, max_rows=max_rows)
    if frame.empty:
        return []

    return frame.to_dict(orient="records")


def count_lit_failures(path: Path) -> int:
    """Count LIT tests that failed during baseline collection."""
    if not path.is_file():
        return 0

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0

    tests = payload.get("tests", [])
    if not isinstance(tests, list):
        return 0

    return sum(
        1
        for test in tests
        if isinstance(test, dict) and test.get("code") in LIT_FAILURE_CODES
    )


def evaluate_output_dir(output_dir: Path) -> dict[str, Any]:
    """Summarize a completed pr-cov-gaps-detection output directory."""
    gap_csv = output_dir / "commit_lines_report" / "target_lines_uncovered.csv"
    lit_failures_json = output_dir / "baseline" / "lit_failures.json"
    gap_count = count_csv_data_rows(gap_csv)
    lit_failure_count = count_lit_failures(lit_failures_json)
    return {
        "gap_count": gap_count,
        "lit_failure_count": lit_failure_count,
        "status": "gaps" if gap_count > 0 else "clean",
        "gap_report": str(gap_csv),
        "lit_failures_json": str(lit_failures_json),
    }


def pr_url(github_repo: str, pr_number: int) -> str:
    return f"https://github.com/{github_repo}/pull/{pr_number}"


def _state_entries_dataframe(state: dict[str, Any]) -> pd.DataFrame:
    """Convert state entries into a flat DataFrame for report aggregation."""
    rows: list[dict[str, Any]] = []
    for key, raw in state.get("entries", {}).items():
        if not isinstance(raw, dict):
            continue

        entry = _state_entry_from_dict(raw)
        rows.append(
            {
                "key": key,
                "pr_number": entry.pr_number,
                "backend": entry.backend,
                "title": entry.title,
                "head_sha": entry.head_sha,
                "status": entry.status,
                "gap_count": entry.gap_count,
                "lit_failure_count": entry.lit_failure_count,
                "checked_at": entry.checked_at,
                "output_dir": entry.output_dir,
                "error": entry.error,
            }
        )

    columns = [
        "key",
        "pr_number",
        "backend",
        "title",
        "head_sha",
        "status",
        "gap_count",
        "lit_failure_count",
        "checked_at",
        "output_dir",
        "error",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(rows)


def _attach_sample_gaps(frame: pd.DataFrame, *, max_gap_lines: int) -> pd.DataFrame:
    """Add a sample_gaps list column for entries that reported coverage gaps."""

    def sample_gaps_for_row(row: pd.Series) -> list[dict[str, str]]:
        if row["status"] != "gaps" or int(row["gap_count"]) <= 0:
            return []
        gap_csv = Path(row["output_dir"]) / "commit_lines_report" / "target_lines_uncovered.csv"
        return load_gap_rows(gap_csv, max_rows=max_gap_lines)

    enriched = frame.copy()
    enriched["sample_gaps"] = enriched.apply(sample_gaps_for_row, axis=1)
    return enriched


def build_report_payload(
    state: dict[str, Any],
    *,
    github_repo: str = DEFAULT_GITHUB_REPO,
    max_gap_lines: int = 20,
) -> dict[str, Any]:
    """Aggregate state entries into a report payload."""
    frame = _state_entries_dataframe(state)
    if frame.empty:
        return {
            "generated_at": utc_now_iso(),
            "github_repo": github_repo,
            "summary": {
                "total_entries": 0,
                "with_gaps": 0,
                "clean": 0,
                "failed": 0,
            },
            "entries_with_gaps": [],
            "failed_entries": [],
            "all_entries": [],
        }

    frame = _attach_sample_gaps(frame, max_gap_lines=max_gap_lines)
    frame["pr_url"] = frame["pr_number"].map(lambda number: pr_url(github_repo, int(number)))

    status_counts = frame["status"].value_counts()
    with_gaps_frame = frame[frame["status"] == "gaps"].sort_values(
        ["gap_count", "pr_number", "backend"],
        ascending=[False, True, True],
    )
    failed_frame = frame[frame["status"] == "failed"].sort_values(["pr_number", "backend"])
    all_entries_frame = frame.sort_values(["pr_number", "backend"])

    return {
        "generated_at": utc_now_iso(),
        "github_repo": github_repo,
        "summary": {
            "total_entries": int(len(frame)),
            "with_gaps": int(status_counts.get("gaps", 0)),
            "clean": int(status_counts.get("clean", 0)),
            "failed": int(status_counts.get("failed", 0)),
        },
        "entries_with_gaps": with_gaps_frame.to_dict(orient="records"),
        "failed_entries": failed_frame.to_dict(orient="records"),
        "all_entries": all_entries_frame.to_dict(orient="records"),
    }


def _markdown_escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_report_markdown(report: dict[str, Any]) -> str:
    """Render a human-readable Markdown summary."""
    lines = [
        "# LLVM PR coverage gap report",
        "",
        f"Generated: {report['generated_at']}",
        f"Repository: {report['github_repo']}",
    ]
    summary = report["summary"]
    lines.extend(
        [
            (
                "Entries: "
                f"{summary['total_entries']} total, "
                f"{summary['with_gaps']} with gaps, "
                f"{summary['clean']} clean, "
                f"{summary['failed']} failed"
            ),
            "",
        ]
    )

    entries_with_gaps = report.get("entries_with_gaps", [])
    if entries_with_gaps:
        lines.append("## PRs with coverage gaps")
        lines.append("")
        for entry in entries_with_gaps:
            lines.append(
                f"### #{entry['pr_number']} ({entry['backend']}) — "
                f"{entry['gap_count']} uncovered line(s)"
            )
            lines.append("")
            lines.append(f"- **Title:** {entry['title']}")
            lines.append(f"- **PR:** {entry['pr_url']}")
            lines.append(f"- **Head:** `{entry['head_sha'][:12]}`")
            lines.append(f"- **Checked:** {entry['checked_at']}")
            if entry["lit_failure_count"] > 0:
                lines.append(
                    f"- **Warning:** {entry['lit_failure_count']} LIT failure(s) during baseline"
                )
            lines.append("")
            sample_gaps = entry.get("sample_gaps", [])
            if sample_gaps:
                lines.extend(["| File | Line | Text |", "|------|------|------|"])
                for row in sample_gaps:
                    text = _markdown_escape_cell(row.get("text", ""))
                    file_path = _markdown_escape_cell(row.get("file", ""))
                    lines.append(f"| `{file_path}` | {row.get('line_no', '')} | `{text}` |")
                remaining = entry["gap_count"] - len(sample_gaps)
                if remaining > 0:
                    lines.extend(
                        [
                            "",
                            (
                                f"*…and {remaining} more line(s). See "
                                f"`{entry['output_dir']}/commit_lines_report/target_lines_uncovered.csv`*"
                            ),
                        ]
                    )
            lines.append("")

    failed_entries = report.get("failed_entries", [])
    if failed_entries:
        lines.extend(["## Failed checks", ""])
        for entry in failed_entries:
            lines.append(
                f"- #{entry['pr_number']} ({entry['backend']}): {entry.get('error') or 'unknown error'}"
            )
        lines.append("")

    if not entries_with_gaps and not failed_entries:
        lines.append("No PRs with coverage gaps or failed checks in the current state.")
        lines.append("")

    return "\n".join(lines)


def write_reports(
    report_dir: Path,
    payload: dict[str, Any],
    *,
    write_run_snapshot: bool = True,
) -> dict[str, Path]:
    """Write latest.json, latest.md, and an optional timestamped snapshot."""
    report_dir.mkdir(parents=True, exist_ok=True)

    latest_json = report_dir / "latest.json"
    latest_md = report_dir / "latest.md"
    latest_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest_md.write_text(render_report_markdown(payload) + "\n", encoding="utf-8")

    written = {"latest_json": latest_json, "latest_md": latest_md}
    if write_run_snapshot:
        runs_dir = report_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        snapshot_name = payload["generated_at"].replace(":", "").replace("+00:00", "Z")
        snapshot_path = runs_dir / f"{snapshot_name}.json"
        snapshot_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written["run_snapshot"] = snapshot_path

    log.info("Wrote report files under %s", report_dir)
    for name, path in written.items():
        log.info("  %s: %s", name, path)

    return written


def cmd_discover(args: argparse.Namespace) -> int:
    discovered = discover_prs(
        github_repo=args.github_repo,
        limit=args.limit,
        max_age_days=args.max_age_days,
    )
    payload = _discovered_to_json(discovered)
    log.info("Writing %d discovered PR(s) to stdout as JSON", len(payload))
    print(json.dumps(payload, indent=2))
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    discovered = discover_prs(
        github_repo=args.github_repo,
        limit=args.limit,
        max_age_days=args.max_age_days,
    )
    state = load_state(args.state_file)
    work = plan_work(discovered, state)
    if args.max_items is not None:
        if len(work) > args.max_items:
            log.info(
                "Capping planned work from %d item(s) to %d (--max-items)",
                len(work),
                args.max_items,
            )
        work = work[: args.max_items]
    log.info("Writing %d planned work item(s) to stdout as JSON", len(work))
    print(json.dumps(_work_to_json(work), indent=2))
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    state = load_state(args.state_file)
    record_result(
        state,
        pr_number=args.pr_number,
        backend=args.backend,
        title=args.title,
        head_sha=args.head_sha,
        status=args.status,
        gap_count=args.gap_count,
        lit_failure_count=args.lit_failure_count,
        output_dir=args.output_dir,
        error=args.error,
    )
    save_state(args.state_file, state)
    return 0


def cmd_evaluate_output(args: argparse.Namespace) -> int:
    log.info("Evaluating output directory: %s", args.output_dir)
    payload = evaluate_output_dir(args.output_dir)
    log.info(
        "Evaluation: status=%s gap_count=%d lit_failures=%d",
        payload["status"],
        payload["gap_count"],
        payload["lit_failure_count"],
    )
    print(json.dumps(payload, indent=2))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    log.info("Generating coverage gap report")
    state = load_state(args.state_file)
    payload = build_report_payload(
        state,
        github_repo=args.github_repo,
        max_gap_lines=args.max_gap_lines,
    )
    summary = payload["summary"]
    log.info(
        "Report summary: %d total, %d with gaps, %d clean, %d failed",
        summary["total_entries"],
        summary["with_gaps"],
        summary["clean"],
        summary["failed"],
    )
    written = write_reports(
        args.report_dir,
        payload,
        write_run_snapshot=not args.no_run_snapshot,
    )
    print(
        json.dumps(
            {key: str(path) for key, path in written.items()},
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    logging_parent = argparse.ArgumentParser(add_help=False)
    logging_parent.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Log level for progress messages on stderr (default: info)",
    )
    logging_parent.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        const="debug",
        dest="log_level",
        help="Shorthand for --log-level debug",
    )

    github_repo_parent = argparse.ArgumentParser(add_help=False)
    github_repo_parent.add_argument(
        "--github-repo",
        default=DEFAULT_GITHUB_REPO,
        help=f"GitHub repo hosting PRs (default: {DEFAULT_GITHUB_REPO})",
    )

    search_parent = argparse.ArgumentParser(add_help=False)
    search_parent.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_SEARCH_LIMIT,
        help=f"Max PRs per backend search (default: {DEFAULT_SEARCH_LIMIT})",
    )
    search_parent.add_argument(
        "--max-age-days",
        type=int,
        default=DEFAULT_MAX_PR_AGE_DAYS,
        help=(
            "Only include PRs opened within this many days "
            f"(default: {DEFAULT_MAX_PR_AGE_DAYS})"
        ),
    )

    discover_parser = subparsers.add_parser(
        "discover",
        help="List open target PRs",
        parents=[logging_parent, github_repo_parent, search_parent],
    )
    discover_parser.set_defaults(func=cmd_discover)

    plan_parser = subparsers.add_parser(
        "plan",
        help="List PR/backend pairs needing a run",
        parents=[logging_parent, github_repo_parent, search_parent],
    )
    plan_parser.add_argument(
        "--state-file",
        type=Path,
        required=True,
        help="Path to state.json",
    )
    plan_parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Cap the number of planned work items",
    )
    plan_parser.set_defaults(func=cmd_plan)

    record_parser = subparsers.add_parser(
        "record",
        help="Persist one check result",
        parents=[logging_parent],
    )
    record_parser.add_argument("--state-file", type=Path, required=True)
    record_parser.add_argument("--pr-number", type=int, required=True)
    record_parser.add_argument("--backend", choices=sorted(BACKEND_SEARCH_QUERIES), required=True)
    record_parser.add_argument("--title", default="")
    record_parser.add_argument("--head-sha", required=True)
    record_parser.add_argument(
        "--status",
        choices=["gaps", "clean", "failed"],
        required=True,
    )
    record_parser.add_argument("--gap-count", type=int, default=0)
    record_parser.add_argument("--lit-failure-count", type=int, default=0)
    record_parser.add_argument("--output-dir", required=True)
    record_parser.add_argument("--error", default=None)
    record_parser.set_defaults(func=cmd_record)

    evaluate_parser = subparsers.add_parser(
        "evaluate-output",
        help="Summarize gap and LIT failure counts from a run output directory",
        parents=[logging_parent],
    )
    evaluate_parser.add_argument("--output-dir", type=Path, required=True)
    evaluate_parser.set_defaults(func=cmd_evaluate_output)

    report_parser = subparsers.add_parser(
        "report",
        help="Write latest.json and latest.md from state",
        parents=[logging_parent, github_repo_parent],
    )
    report_parser.add_argument("--state-file", type=Path, required=True)
    report_parser.add_argument(
        "--report-dir",
        type=Path,
        required=True,
        help="Directory for latest.json, latest.md, and runs/ snapshots",
    )
    report_parser.add_argument(
        "--max-gap-lines",
        type=int,
        default=20,
        help="Max uncovered lines to include per PR in the report (default: 20)",
    )
    report_parser.add_argument(
        "--no-run-snapshot",
        action="store_true",
        help="Skip writing report_dir/runs/<timestamp>.json",
    )
    report_parser.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        configure_logging(args.log_level)
    except PrCheckerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        return args.func(args)
    except PrCheckerError as exc:
        log.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
