#!/usr/bin/env python3
# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Discover, plan, and record periodic LLVM PR coverage-gap checks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STATE_VERSION = 1
DEFAULT_GITHUB_REPO = "llvm/llvm-project"
DEFAULT_SEARCH_LIMIT = 100

BACKEND_SEARCH_QUERIES: dict[str, str] = {
    "amdgpu": "path:llvm/lib/Target/AMDGPU",
    "spirv": "path:llvm/lib/Target/SPIRV",
}

SEARCH_JSON_FIELDS = ["number", "title", "updatedAt"]
PR_VIEW_JSON_FIELDS = ["number", "title", "headRefOid", "updatedAt"]


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


def _require_gh() -> str:
    from shutil import which

    gh_path = which("gh")
    if gh_path is None:
        raise PrCheckerError("required command not found: gh")
    return gh_path


def _run_gh(args: list[str], *, timeout: int = 120) -> str:
    gh_path = _require_gh()
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
) -> list[dict[str, Any]]:
    query = BACKEND_SEARCH_QUERIES[backend]
    payload = _gh_json(
        [
            "search",
            "prs",
            query,
            "--repo",
            github_repo,
            "--state",
            "open",
            "--limit",
            str(limit),
        ]
    )
    if not isinstance(payload, list):
        raise PrCheckerError(f"unexpected gh search payload for {backend}: {type(payload)!r}")
    return payload


def _view_pr(pr_number: int, github_repo: str) -> dict[str, Any]:
    payload = _gh_json(["pr", "view", str(pr_number), "--repo", github_repo])
    if not isinstance(payload, dict):
        raise PrCheckerError(f"unexpected gh pr view payload for #{pr_number}: {type(payload)!r}")
    return payload


def _search_results_dataframe(
    *,
    github_repo: str = DEFAULT_GITHUB_REPO,
    limit: int = DEFAULT_SEARCH_LIMIT,
) -> pd.DataFrame:
    """Run backend searches and return one row per (PR, backend) match."""
    frames: list[pd.DataFrame] = []
    for backend in BACKEND_SEARCH_QUERIES:
        items = _search_backend_prs(backend, github_repo=github_repo, limit=limit)
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


def discover_prs(*, github_repo: str = DEFAULT_GITHUB_REPO, limit: int = DEFAULT_SEARCH_LIMIT) -> list[DiscoveredPr]:
    """Find open PRs touching AMDGPU and/or SPIR-V target paths."""
    grouped = _aggregate_search_results(
        _search_results_dataframe(github_repo=github_repo, limit=limit)
    )
    if grouped.empty:
        return []

    discovered: list[DiscoveredPr] = []
    for row in grouped.itertuples(index=False):
        pr_number = int(row.pr_number)
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

    return discovered


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
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

    return payload


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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

    for pr in discovered:
        for backend in pr.backends:
            key = entry_key(pr.pr_number, backend)
            existing = entries.get(key)
            if existing is None:
                work.append(
                    WorkItem(
                        pr_number=pr.pr_number,
                        backend=backend,
                        title=pr.title,
                        head_sha=pr.head_sha,
                        reason="new",
                    )
                )
                continue

            previous = _state_entry_from_dict(existing)
            if previous.head_sha != pr.head_sha:
                work.append(
                    WorkItem(
                        pr_number=pr.pr_number,
                        backend=backend,
                        title=pr.title,
                        head_sha=pr.head_sha,
                        reason="head_changed",
                    )
                )

    work.sort(key=lambda item: (item.pr_number, item.backend))
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


def cmd_discover(args: argparse.Namespace) -> int:
    discovered = discover_prs(github_repo=args.github_repo, limit=args.limit)
    payload = _discovered_to_json(discovered)
    print(json.dumps(payload, indent=2))
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    discovered = discover_prs(github_repo=args.github_repo, limit=args.limit)
    state = load_state(args.state_file)
    work = plan_work(discovered, state)
    if args.max_items is not None:
        work = work[: args.max_items]
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--github-repo",
        default=DEFAULT_GITHUB_REPO,
        help=f"GitHub repo hosting PRs (default: {DEFAULT_GITHUB_REPO})",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover", help="List open target PRs")
    discover_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_SEARCH_LIMIT,
        help=f"Max PRs per backend search (default: {DEFAULT_SEARCH_LIMIT})",
    )
    discover_parser.set_defaults(func=cmd_discover)

    plan_parser = subparsers.add_parser("plan", help="List PR/backend pairs needing a run")
    plan_parser.add_argument(
        "--state-file",
        type=Path,
        required=True,
        help="Path to state.json",
    )
    plan_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_SEARCH_LIMIT,
        help=f"Max PRs per backend search (default: {DEFAULT_SEARCH_LIMIT})",
    )
    plan_parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Cap the number of planned work items",
    )
    plan_parser.set_defaults(func=cmd_plan)

    record_parser = subparsers.add_parser("record", help="Persist one check result")
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except PrCheckerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
