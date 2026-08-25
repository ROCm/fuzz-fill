#!/usr/bin/env python3
# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Discover, plan, and record periodic LLVM PR coverage-gap checks."""

from __future__ import annotations

import argparse
import json
import logging
import os
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
DEFAULT_MAX_PR_AGE_DAYS = 14

BACKEND_SEARCH_QUERIES: dict[str, list[str]] = {
    "amdgpu": [
        'label:"backend:AMDGPU"',
    ],
    "spirv": [
        'label:"backend:SPIR-V"',
    ],
}

BACKEND_TARGET_PATH_PREFIXES: dict[str, str] = {
    "amdgpu": "llvm/lib/Target/AMDGPU/",
    "spirv": "llvm/lib/Target/SPIRV/",
}

SEARCH_JSON_FIELDS = ["number", "title", "updatedAt"]
PR_VIEW_JSON_FIELDS = ["number", "title", "headRefOid", "updatedAt", "files"]
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
    updated_at: str = ""


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


def _parse_backends_arg(raw: str | None) -> list[str] | None:
    """Parse a comma-separated backend list from CLI input."""
    if raw is None:
        return None
    names = [part.strip() for part in raw.split(",") if part.strip()]
    if not names:
        raise PrCheckerError("backends must list at least one backend when provided")
    return _validate_backends(names)


def _validate_backends(backends: list[str]) -> list[str]:
    unknown = sorted(set(backends) - set(BACKEND_SEARCH_QUERIES))
    if unknown:
        raise PrCheckerError(
            f"unknown backend(s): {', '.join(unknown)} "
            f"(known: {', '.join(sorted(BACKEND_SEARCH_QUERIES))})"
        )
    seen: set[str] = set()
    resolved: list[str] = []
    for backend in backends:
        if backend not in seen:
            seen.add(backend)
            resolved.append(backend)
    return resolved


def _backends_to_search(backends: list[str] | None) -> list[str]:
    if backends is None:
        return list(BACKEND_SEARCH_QUERIES)
    return _validate_backends(backends)


def _search_created_since(max_age_days: int) -> str:
    """Return a YYYY-MM-DD date for GitHub ``created:>`` search qualifiers."""
    _validate_max_age_days(max_age_days)
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=max_age_days)
    return cutoff.isoformat()


def _backend_search_terms(backend: str, *, max_age_days: int) -> list[str]:
    """Build gh search terms for one backend, limited to recently opened PRs."""
    created_since = _search_created_since(max_age_days)
    age_filter = f"created:>{created_since}"
    return [f"{term} {age_filter}" for term in BACKEND_SEARCH_QUERIES[backend]]


def _pr_changed_paths(pr_view: dict[str, Any]) -> list[str]:
    files = pr_view.get("files")
    if not isinstance(files, list):
        return []
    paths: list[str] = []
    for entry in files:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if isinstance(path, str) and path:
            paths.append(path)
    return paths


def _pr_touches_backend_path(pr_view: dict[str, Any], backend: str) -> bool:
    prefix = BACKEND_TARGET_PATH_PREFIXES[backend]
    return any(path.startswith(prefix) for path in _pr_changed_paths(pr_view))


def _merge_search_items(items_list: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Merge GitHub search hits, keeping one row per PR number."""
    merged: dict[int, dict[str, Any]] = {}
    for items in items_list:
        for item in items:
            number = item.get("number")
            if number is None:
                continue
            pr_number = int(number)
            existing = merged.get(pr_number)
            if existing is None:
                merged[pr_number] = dict(item)
                continue
            if item.get("title") and not existing.get("title"):
                existing["title"] = item["title"]
            if (item.get("updatedAt") or "") > (existing.get("updatedAt") or ""):
                existing["updatedAt"] = item["updatedAt"]
    return [merged[pr_number] for pr_number in sorted(merged)]


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


def _search_issues(
    search_query: str,
    *,
    limit: int,
) -> list[dict[str, Any]]:
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
        raise PrCheckerError(f"unexpected gh api search payload: {type(payload)!r}")
    return _normalize_search_items(payload.get("items", []))


def _search_backend_prs(
    backend: str,
    *,
    github_repo: str = DEFAULT_GITHUB_REPO,
    limit: int = DEFAULT_SEARCH_LIMIT,
    max_age_days: int = DEFAULT_MAX_PR_AGE_DAYS,
) -> list[dict[str, Any]]:
    search_terms = _backend_search_terms(backend, max_age_days=max_age_days)
    per_term_results: list[list[dict[str, Any]]] = []
    for term in search_terms:
        search_query = f"repo:{github_repo} is:pr is:open {term}"
        log.info(
            "Searching %s PRs on %s (query=%r, limit=%d, max_age_days=%d)",
            backend,
            github_repo,
            search_query,
            limit,
            max_age_days,
        )
        items = _search_issues(search_query, limit=limit)
        log.info("Found %d open %s PR(s) for search term", len(items), backend)
        per_term_results.append(items)

    items = _merge_search_items(per_term_results)[:limit]
    log.info("Found %d unique open %s PR(s) after merging search terms", len(items), backend)
    return items


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
    backends: list[str] | None = None,
) -> pd.DataFrame:
    """Run backend searches and return one row per (PR, backend) match."""
    frames: list[pd.DataFrame] = []
    for backend in _backends_to_search(backends):
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
    backends: list[str] | None = None,
) -> list[DiscoveredPr]:
    """Find open PRs with changed files under AMDGPU/SPIR-V target directories."""
    search_backends = _backends_to_search(backends)
    log.info(
        "Discovering open PRs on %s (limit=%d per backend, max_age_days=%d, backends=%s)",
        github_repo,
        limit,
        max_age_days,
        ", ".join(search_backends),
    )
    search_df = _search_results_dataframe(
        github_repo=github_repo,
        limit=limit,
        max_age_days=max_age_days,
        backends=backends,
    )
    grouped = _aggregate_search_results(search_df)
    if grouped.empty:
        log.info("No matching open PRs found")
        return []

    total = len(grouped)
    log.info(
        "Search returned %d unique PR(s); resolving PR metadata and filtering by target paths",
        total,
    )

    discovered: list[DiscoveredPr] = []
    skipped_without_target_paths = 0
    for index, row in enumerate(grouped.itertuples(index=False), start=1):
        pr_number = int(row.pr_number)
        if index == 1 or index == total or index % 10 == 0:
            log.info("Inspecting PR %d/%d: #%d", index, total, pr_number)
        else:
            log.debug("Inspecting PR %d/%d: #%d", index, total, pr_number)

        pr_view = _view_pr(pr_number, github_repo)
        head_sha = pr_view.get("headRefOid")
        if not head_sha:
            raise PrCheckerError(f"could not resolve headRefOid for {github_repo}#{pr_number}")

        matched_backends = [
            backend
            for backend in row.backends
            if _pr_touches_backend_path(pr_view, backend)
        ]
        if not matched_backends:
            skipped_without_target_paths += 1
            log.debug(
                "Skipping #%d: no changed files under tracked target path(s) for %s",
                pr_number,
                ", ".join(row.backends),
            )
            continue

        discovered.append(
            DiscoveredPr(
                pr_number=pr_number,
                title=pr_view.get("title") or row.title or "",
                head_sha=head_sha,
                updated_at=pr_view.get("updatedAt") or row.updated_at or "",
                backends=matched_backends,
            )
        )

    log.info(
        "Discovery complete: %d PR(s) with target-path changes (%d skipped without target-path changes)",
        len(discovered),
        skipped_without_target_paths,
    )
    return discovered


def _parse_state_payload(payload: Any, path: Path) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PrCheckerError(f"invalid state file {path}: expected object at top level")
    if payload.get("version") != STATE_VERSION:
        raise PrCheckerError(
            f"unsupported state version in {path}: {payload.get('version')!r} (expected {STATE_VERSION})"
        )
    if not isinstance(payload.get("entries"), dict):
        raise PrCheckerError(f"invalid state file {path}: missing entries object")
    return payload


def _read_state_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise PrCheckerError(f"invalid state file {path}: file not found")
    if path.stat().st_size == 0:
        raise PrCheckerError(f"invalid state file {path}: empty file")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PrCheckerError(f"invalid state file {path}: {exc.msg}") from exc

    return _parse_state_payload(payload, path)


def _state_backup_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".bak")


def _maybe_backup_state_file(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        return
    try:
        _read_state_file(path)
    except PrCheckerError:
        log.warning("Skipping backup of invalid state file %s", path)
        return

    backup_path = _state_backup_path(path)
    backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    log.info("Backed up existing state to %s", backup_path)


def load_state(
    path: Path,
    *,
    recover: bool = False,
    output_root: Path | None = None,
    report_dir: Path | None = None,
    github_repo: str = DEFAULT_GITHUB_REPO,
    fetch_missing_pr_metadata: bool = True,
) -> dict[str, Any]:
    if not path.exists():
        log.info("State file not found, starting fresh: %s", path)
        return {"version": STATE_VERSION, "entries": {}}

    try:
        state = _read_state_file(path)
    except PrCheckerError as exc:
        if not recover:
            raise
        log.warning("%s; attempting recovery", exc)
        state = None
    else:
        log.info("Loaded state from %s (%d entries)", path, len(state["entries"]))
        return state

    backup_path = _state_backup_path(path)
    if backup_path.is_file() and backup_path.stat().st_size > 0:
        try:
            state = _read_state_file(backup_path)
        except PrCheckerError as backup_exc:
            log.warning("Could not recover state from backup %s: %s", backup_path, backup_exc)
        else:
            log.warning(
                "Recovered state from backup %s (%d entries)",
                backup_path,
                len(state["entries"]),
            )
            save_state(path, state, backup=False)
            return state

    root = output_root or (path.parent / "runs")
    reports = report_dir or (path.parent / "reports")
    if root.is_dir():
        state, stats = rebuild_state_from_runs(
            output_root=root,
            github_repo=github_repo,
            report_dir=reports if reports.is_dir() else None,
            existing_state=None,
            fetch_missing_pr_metadata=fetch_missing_pr_metadata,
        )
        if state["entries"]:
            log.warning(
                "Recovered state by rebuilding from run artifacts "
                "(%d entries from %d evaluated run(s))",
                len(state["entries"]),
                stats["runs_evaluated"],
            )
            save_state(path, state, backup=False)
            return state
        log.warning("Rebuild from %s found no completed runs to recover", root)

    raise PrCheckerError(f"invalid state file {path} and recovery failed")


def save_state(path: Path, state: dict[str, Any], *, backup: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup:
        _maybe_backup_state_file(path)

    content = json.dumps(state, indent=2, sort_keys=True) + "\n"
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)
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
                        updated_at=pr.updated_at,
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
                        updated_at=pr.updated_at,
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

    work.sort(key=lambda item: item.backend)
    work.sort(key=lambda item: item.pr_number, reverse=True)
    work.sort(key=lambda item: item.updated_at or "", reverse=True)
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


_STATE_ENTRY_FIELDS = (
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
)


def parse_run_dir_name(name: str) -> tuple[int, str]:
    """Parse a run directory name ``<pr_number>-<backend>``."""
    if "-" not in name:
        raise PrCheckerError(f"invalid run directory name (expected <pr>-<backend>): {name!r}")
    backend = name.rsplit("-", 1)[1]
    if backend not in BACKEND_SEARCH_QUERIES:
        raise PrCheckerError(
            f"invalid run directory name {name!r}: unknown backend {backend!r}"
        )
    try:
        pr_number = int(name[: -(len(backend) + 1)])
    except ValueError as exc:
        raise PrCheckerError(f"invalid run directory name (bad PR number): {name!r}") from exc
    if pr_number <= 0:
        raise PrCheckerError(f"invalid run directory name (bad PR number): {name!r}")
    return pr_number, backend


def is_evaluable_run(output_dir: Path) -> bool:
    """Return True when *output_dir* has the artifacts produced by a completed check."""
    return (output_dir / "commit_lines_report" / "target_lines_uncovered.csv").is_file()


def output_dir_checked_at(output_dir: Path) -> str:
    """Approximate check completion time from the newest artifact under *output_dir*."""
    newest_mtime = output_dir.stat().st_mtime
    for path in output_dir.rglob("*"):
        if path.is_file():
            newest_mtime = max(newest_mtime, path.stat().st_mtime)
    return datetime.fromtimestamp(newest_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()


def _report_entry_to_state_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {field: entry.get(field) for field in _STATE_ENTRY_FIELDS}


def _checked_at_sort_key(checked_at: str) -> str:
    return checked_at or ""


def load_report_entry_index(report_dir: Path | None) -> dict[str, dict[str, Any]]:
    """Load PR/backend metadata from ``latest.json`` and ``runs/*.json`` report snapshots."""
    if report_dir is None:
        return {}

    candidates: list[Path] = []
    latest_json = report_dir / "latest.json"
    if latest_json.is_file():
        candidates.append(latest_json)
    runs_dir = report_dir / "runs"
    if runs_dir.is_dir():
        candidates.extend(sorted(runs_dir.glob("*.json")))

    indexed: dict[str, dict[str, Any]] = {}
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            log.warning("Skipping invalid report file %s: %s", path, exc.msg)
            continue
        if not isinstance(payload, dict):
            log.warning("Skipping invalid report file %s: expected object at top level", path)
            continue

        for raw in payload.get("all_entries", []):
            if not isinstance(raw, dict):
                continue
            try:
                key = _entry_key_from_record(raw)
                state_entry = _report_entry_to_state_entry(raw)
            except (KeyError, TypeError, ValueError):
                log.warning("Skipping malformed report entry in %s", path)
                continue

            existing = indexed.get(key)
            if existing is None or _checked_at_sort_key(state_entry["checked_at"]) >= _checked_at_sort_key(
                existing.get("checked_at", "")
            ):
                indexed[key] = state_entry

    log.info(
        "Loaded metadata for %d PR/backend pair(s) from report files under %s",
        len(indexed),
        report_dir,
    )
    return indexed


def fetch_pr_metadata(pr_number: int, *, github_repo: str) -> tuple[str, str]:
    """Return ``(title, head_sha)`` for an open PR via ``gh pr view``."""
    payload = _view_pr(pr_number, github_repo)
    head_sha = payload.get("headRefOid")
    if not head_sha:
        raise PrCheckerError(f"could not resolve headRefOid for {github_repo}#{pr_number}")
    title = str(payload.get("title") or "")
    return title, str(head_sha)


def rebuild_state_from_runs(
    *,
    output_root: Path,
    github_repo: str = DEFAULT_GITHUB_REPO,
    report_dir: Path | None = None,
    existing_state: dict[str, Any] | None = None,
    fetch_missing_pr_metadata: bool = True,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Rebuild ``state.json`` entries from on-disk run artifacts.

    Completed runs under *output_root* are re-evaluated with
    :func:`evaluate_output_dir`. ``title``, ``head_sha``, and ``checked_at`` are
    taken from prior report snapshots when available; remaining PRs can optionally
    be resolved via ``gh pr view`` (current head SHA — see README caveat).
    """
    if not output_root.is_dir():
        raise PrCheckerError(f"output root is not a directory: {output_root}")

    entries: dict[str, dict[str, Any]] = {}
    if existing_state is not None:
        for key, raw in existing_state.get("entries", {}).items():
            if isinstance(raw, dict):
                entries[key] = dict(raw)

    report_index = load_report_entry_index(report_dir)
    stats = {
        "runs_seen": 0,
        "runs_evaluated": 0,
        "runs_skipped_incomplete": 0,
        "metadata_from_reports": 0,
        "metadata_from_existing_state": 0,
        "metadata_from_github": 0,
        "metadata_missing": 0,
    }

    for run_dir in sorted(output_root.iterdir()):
        if not run_dir.is_dir():
            continue
        stats["runs_seen"] += 1
        if not is_evaluable_run(run_dir):
            stats["runs_skipped_incomplete"] += 1
            log.info("Skipping incomplete run directory (no gap report): %s", run_dir.name)
            continue

        pr_number, backend = parse_run_dir_name(run_dir.name)
        key = entry_key(pr_number, backend)
        evaluation = evaluate_output_dir(run_dir)
        output_dir = str(run_dir.resolve())

        entry: dict[str, Any] = {
            "pr_number": pr_number,
            "backend": backend,
            "title": "",
            "head_sha": "",
            "status": evaluation["status"],
            "gap_count": evaluation["gap_count"],
            "lit_failure_count": evaluation["lit_failure_count"],
            "checked_at": output_dir_checked_at(run_dir),
            "output_dir": output_dir,
            "error": None,
        }

        metadata_source = report_index.get(key)
        metadata_origin: str | None = None
        if metadata_source is not None:
            metadata_origin = "reports"
        elif key in entries:
            metadata_source = entries[key]
            metadata_origin = "existing_state"

        if metadata_source is not None:
            entry["title"] = str(metadata_source.get("title") or "")
            entry["head_sha"] = str(metadata_source.get("head_sha") or "")
            if metadata_source.get("checked_at"):
                entry["checked_at"] = str(metadata_source["checked_at"])
            if metadata_source.get("status") == "failed":
                entry["status"] = "failed"
                entry["error"] = metadata_source.get("error")
            if metadata_source.get("output_dir"):
                entry["output_dir"] = str(metadata_source["output_dir"])
            if metadata_origin == "reports":
                stats["metadata_from_reports"] += 1
            elif metadata_origin == "existing_state":
                stats["metadata_from_existing_state"] += 1

        if fetch_missing_pr_metadata and not entry["head_sha"]:
            try:
                title, head_sha = fetch_pr_metadata(pr_number, github_repo=github_repo)
            except PrCheckerError as exc:
                stats["metadata_missing"] += 1
                log.warning(
                    "Skipping %s: could not resolve PR metadata (%s)",
                    run_dir.name,
                    exc,
                )
                continue
            entry["title"] = title
            entry["head_sha"] = head_sha
            stats["metadata_from_github"] += 1
            log.info(
                "Resolved PR metadata from GitHub for #%d (%s): head=%s",
                pr_number,
                backend,
                head_sha[:12],
            )
        elif not entry["head_sha"]:
            stats["metadata_missing"] += 1
            log.warning(
                "Skipping %s: missing head_sha (pass --fetch-pr-metadata or provide report snapshots)",
                run_dir.name,
            )
            continue

        entries[key] = entry
        stats["runs_evaluated"] += 1

    state = {"version": STATE_VERSION, "entries": entries}
    log.info(
        "Rebuild summary: %d run dir(s) seen, %d evaluated, %d incomplete skipped, "
        "%d metadata from reports, %d from GitHub, %d missing",
        stats["runs_seen"],
        stats["runs_evaluated"],
        stats["runs_skipped_incomplete"],
        stats["metadata_from_reports"],
        stats["metadata_from_github"],
        stats["metadata_missing"],
    )
    return state, stats


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


def _entry_key_from_record(entry: dict[str, Any]) -> str:
    return entry_key(int(entry["pr_number"]), str(entry["backend"]))


def _index_report_entries(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Map ``"<pr>:<backend>"`` keys to entries from a report payload."""
    if payload is None:
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for entry in payload.get("all_entries", []):
        if isinstance(entry, dict):
            indexed[_entry_key_from_record(entry)] = entry
    return indexed


def diff_report_entries(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
) -> set[str]:
    """Return keys for entries that are new or updated since the previous report."""
    current_index = _index_report_entries(current)
    if previous is None:
        return set(current_index)

    previous_index = _index_report_entries(previous)
    changed: set[str] = set()
    for key, entry in current_index.items():
        prior = previous_index.get(key)
        if prior is None:
            changed.add(key)
            continue
        if entry.get("checked_at") != prior.get("checked_at"):
            changed.add(key)
            continue
        if entry.get("head_sha") != prior.get("head_sha"):
            changed.add(key)
    return changed


def filter_report_payload(payload: dict[str, Any], keys: set[str]) -> dict[str, Any]:
    """Return a copy of a report payload limited to the given entry keys."""
    if not keys:
        return {
            "generated_at": payload["generated_at"],
            "github_repo": payload["github_repo"],
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

    def keep(entry: dict[str, Any]) -> bool:
        return _entry_key_from_record(entry) in keys

    entries_with_gaps = [
        entry for entry in payload.get("entries_with_gaps", []) if keep(entry)
    ]
    failed_entries = [entry for entry in payload.get("failed_entries", []) if keep(entry)]
    all_entries = [entry for entry in payload.get("all_entries", []) if keep(entry)]

    status_counts = {"gaps": 0, "clean": 0, "failed": 0}
    for entry in all_entries:
        status = entry.get("status")
        if status in status_counts:
            status_counts[status] += 1

    return {
        "generated_at": payload["generated_at"],
        "github_repo": payload["github_repo"],
        "summary": {
            "total_entries": len(all_entries),
            "with_gaps": status_counts["gaps"],
            "clean": status_counts["clean"],
            "failed": status_counts["failed"],
        },
        "entries_with_gaps": entries_with_gaps,
        "failed_entries": failed_entries,
        "all_entries": all_entries,
    }


def load_previous_report(latest_json: Path) -> dict[str, Any] | None:
    """Load the previous latest.json report snapshot, if it exists."""
    if not latest_json.is_file():
        return None
    try:
        payload = json.loads(latest_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PrCheckerError(f"invalid report file {latest_json}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise PrCheckerError(f"invalid report file {latest_json}: expected object at top level")
    return payload


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


def render_report_markdown(report: dict[str, Any], *, delta: bool = False) -> str:
    """Render a human-readable Markdown summary."""
    title = (
        "# LLVM PR coverage gap report — new checks"
        if delta
        else "# LLVM PR coverage gap report"
    )
    lines = [
        title,
        "",
        f"Generated: {report['generated_at']}",
        f"Repository: {report['github_repo']}",
    ]
    summary = report["summary"]
    if delta:
        summary_line = (
            "New or updated since last report: "
            f"{summary['total_entries']} PR/backend pair(s) "
            f"({summary['with_gaps']} with gaps, "
            f"{summary['clean']} clean, "
            f"{summary['failed']} failed)"
        )
    else:
        summary_line = (
            "Entries: "
            f"{summary['total_entries']} total, "
            f"{summary['with_gaps']} with gaps, "
            f"{summary['clean']} clean, "
            f"{summary['failed']} failed"
        )
    lines.extend([summary_line, ""])

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
        if delta:
            lines.append(
                "No PRs with coverage gaps or failed checks since the last report."
            )
        else:
            lines.append("No PRs with coverage gaps or failed checks in the current state.")
        lines.append("")

    return "\n".join(lines)


def write_reports(
    report_dir: Path,
    payload: dict[str, Any],
    *,
    write_run_snapshot: bool = True,
) -> dict[str, Path]:
    """Write latest.json, latest.md, new-prs.md, and an optional timestamped snapshot."""
    report_dir.mkdir(parents=True, exist_ok=True)

    latest_json = report_dir / "latest.json"
    latest_md = report_dir / "latest.md"
    new_prs_md = report_dir / "new-prs.md"

    previous_payload = load_previous_report(latest_json)
    changed_keys = diff_report_entries(payload, previous_payload)
    delta_payload = filter_report_payload(payload, changed_keys)
    log.info(
        "Report delta: %d new or updated PR/backend pair(s) since last report",
        len(changed_keys),
    )

    latest_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest_md.write_text(render_report_markdown(payload) + "\n", encoding="utf-8")
    new_prs_md.write_text(render_report_markdown(delta_payload, delta=True) + "\n", encoding="utf-8")

    written = {
        "latest_json": latest_json,
        "latest_md": latest_md,
        "new_prs_md": new_prs_md,
    }
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
        backends=_parse_backends_arg(args.backends),
    )
    payload = _discovered_to_json(discovered)
    log.info("Writing %d discovered PR(s) to stdout as JSON", len(payload))
    print(json.dumps(payload, indent=2))
    return 0


def _load_state_from_args(args: argparse.Namespace) -> dict[str, Any]:
    report_dir = getattr(args, "report_dir", None)
    if report_dir is None:
        report_dir = args.state_file.parent / "reports"
    output_root = args.output_root
    if output_root is None:
        output_root = args.state_file.parent / "runs"
    return load_state(
        args.state_file,
        recover=args.recover_state,
        output_root=output_root,
        report_dir=report_dir,
        github_repo=getattr(args, "github_repo", DEFAULT_GITHUB_REPO),
    )


def cmd_plan(args: argparse.Namespace) -> int:
    discovered = discover_prs(
        github_repo=args.github_repo,
        limit=args.limit,
        max_age_days=args.max_age_days,
        backends=_parse_backends_arg(args.backends),
    )
    state = _load_state_from_args(args)
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
    state = _load_state_from_args(args)
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


def cmd_rebuild_state(args: argparse.Namespace) -> int:
    existing_state: dict[str, Any] | None = None
    if args.merge_existing_state and args.state_file.is_file():
        try:
            existing_state = load_state(args.state_file)
        except PrCheckerError as exc:
            log.warning("Ignoring invalid existing state file %s: %s", args.state_file, exc)

    report_dir = args.report_dir
    if report_dir is None:
        report_dir = args.state_file.parent / "reports"

    state, stats = rebuild_state_from_runs(
        output_root=args.output_root,
        github_repo=args.github_repo,
        report_dir=report_dir,
        existing_state=existing_state,
        fetch_missing_pr_metadata=args.fetch_pr_metadata,
    )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "entry_count": len(state["entries"]),
                    "stats": stats,
                },
                indent=2,
            )
        )
        return 0

    if args.state_file.is_file() and args.backup:
        _maybe_backup_state_file(args.state_file)

    save_state(args.state_file, state)
    print(
        json.dumps(
            {
                "state_file": str(args.state_file),
                "entry_count": len(state["entries"]),
                "stats": stats,
            },
            indent=2,
        )
    )
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
    state = _load_state_from_args(args)
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
    search_parent.add_argument(
        "--backends",
        default=None,
        help=(
            "Comma-separated backend names to search "
            f"(default: {', '.join(sorted(BACKEND_SEARCH_QUERIES))})"
        ),
    )

    state_recovery_parent = argparse.ArgumentParser(add_help=False)
    state_recovery_parent.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Run artifact root for state recovery (default: <state-file-parent>/runs)",
    )
    state_recovery_parent.add_argument(
        "--recover-state",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Recover from state.json.bak or run artifacts when state.json is invalid "
            "(default: enabled)"
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
        parents=[logging_parent, github_repo_parent, search_parent, state_recovery_parent],
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
        parents=[logging_parent, state_recovery_parent],
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

    rebuild_parser = subparsers.add_parser(
        "rebuild-state",
        help="Rebuild state.json from run artifacts and saved reports",
        parents=[logging_parent, github_repo_parent],
    )
    rebuild_parser.add_argument(
        "--state-file",
        type=Path,
        required=True,
        help="Path to write rebuilt state.json",
    )
    rebuild_parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Directory containing per-run output folders (<pr>-<backend>)",
    )
    rebuild_parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help=(
            "Directory with latest.json and runs/*.json snapshots "
            "(default: <state-file-parent>/reports)"
        ),
    )
    rebuild_parser.add_argument(
        "--fetch-pr-metadata",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Resolve title/head_sha via gh for runs missing report metadata "
            "(default: enabled)"
        ),
    )
    rebuild_parser.add_argument(
        "--merge-existing-state",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reuse metadata from an existing state file when valid (default: enabled)",
    )
    rebuild_parser.add_argument(
        "--backup",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Back up the existing state file to state.json.bak (default: enabled)",
    )
    rebuild_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print rebuild stats without writing state.json",
    )
    rebuild_parser.set_defaults(func=cmd_rebuild_state)

    report_parser = subparsers.add_parser(
        "report",
        help="Write latest.json and latest.md from state",
        parents=[logging_parent, github_repo_parent, state_recovery_parent],
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
