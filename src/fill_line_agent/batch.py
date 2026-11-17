# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Multi-target fill-line: collateral credit and batch budgets."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fill_line_agent.oracle import (
    RunResult,
    SymcovIndex,
    TargetLine,
    ToolName,
    measure_hits,
)
from fill_line_agent.render import write_outputs

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def parse_targets(values: list[str]) -> list[TargetLine]:
    """Parse ``path:line`` targets, keeping the first occurrence of each."""
    out: list[TargetLine] = []
    seen: set[str] = set()
    for raw in values:
        target = TargetLine.parse(raw)
        key = str(target)
        if key in seen:
            continue
        seen.add(key)
        out.append(target)
    return out


def line_out_dir(out_dir: Path, index: int, target: TargetLine) -> Path:
    """Return ``lines/<index>-<basename>-<line>/`` under *out_dir*."""
    base = _SAFE_NAME.sub("_", Path(target.rel_path).name)
    return out_dir / "lines" / f"{index:03d}-{base}-{target.line}"


def resolve_int_cap(
    per_session: int | None,
    total: int | None,
    used: int,
    *,
    default: int,
) -> int | None:
    """Return the session cap, or ``None`` if the batch total is already exhausted.

    ``None`` for *per_session* means the flag was unset. When only *total* is
    set, the session receives the remaining total (no separate per-session cap).
    """
    remaining = None if total is None else max(0, total - used)
    if remaining is not None and remaining == 0:
        return None
    if per_session is None and total is None:
        return default
    if per_session is None:
        assert remaining is not None
        return remaining
    if total is None:
        return per_session
    assert remaining is not None
    return min(per_session, remaining)


def resolve_wall_cap(
    per_session: float,
    total: float | None,
    elapsed_s: float,
) -> float | None:
    """Return session wall seconds (0 = disabled), or ``None`` if exhausted."""
    remaining = None if total is None or total <= 0 else max(0.0, total - elapsed_s)
    if remaining is not None and remaining <= 0:
        return None
    if per_session > 0 and remaining is not None:
        return min(per_session, remaining)
    if per_session > 0:
        return per_session
    if remaining is not None:
        return remaining
    return 0.0


def resolve_usd_cap(
    per_session: float | None,
    total: float | None,
    used: float,
) -> float | None | bool:
    """Return session USD cap, ``False`` if exhausted, or ``None`` if disabled."""
    remaining = None if total is None else max(0.0, total - used)
    if remaining is not None and remaining <= 0:
        return False
    if per_session is None and total is None:
        return None
    if per_session is None:
        assert remaining is not None
        return remaining
    if total is None:
        return per_session
    assert remaining is not None
    return min(per_session, remaining)


@dataclass
class BatchBudget:
    """Accumulated usage across fill-line sessions for optional total caps."""

    max_runs: int | None = None
    max_runs_total: int | None = None
    max_turns: int | None = None
    max_turns_total: int | None = None
    max_wall_s: float = 0.0
    max_wall_s_total: float | None = None
    max_budget_usd: float | None = None
    max_budget_usd_total: float | None = None
    max_stale_runs: int = 0

    runs_used: int = 0
    turns_used: int = 0
    cost_used: float = 0.0
    started_at: float = field(default_factory=time.perf_counter)

    def wall_elapsed_s(self) -> float:
        return time.perf_counter() - self.started_at

    def totals_exhausted(self) -> str | None:
        if self.max_runs_total is not None and self.runs_used >= self.max_runs_total:
            return f"max_runs_total reached ({self.max_runs_total})"
        if self.max_turns_total is not None and self.turns_used >= self.max_turns_total:
            return f"max_turns_total reached ({self.max_turns_total})"
        if (
            self.max_wall_s_total is not None
            and self.max_wall_s_total > 0
            and self.wall_elapsed_s() >= self.max_wall_s_total
        ):
            return f"max_wall_s_total reached ({self.max_wall_s_total:g})"
        if (
            self.max_budget_usd_total is not None
            and self.cost_used >= self.max_budget_usd_total
        ):
            return f"max_budget_usd_total reached (${self.max_budget_usd_total:g})"
        return None

    def session_limits(self) -> dict[str, Any] | None:
        """Return kwargs for ``make_state`` / ``run_session``, or ``None`` if done."""
        reason = self.totals_exhausted()
        if reason is not None:
            return None

        max_runs = resolve_int_cap(
            self.max_runs, self.max_runs_total, self.runs_used, default=40
        )
        if max_runs is None:
            return None

        max_turns = resolve_int_cap(
            self.max_turns, self.max_turns_total, self.turns_used, default=80
        )
        if max_turns is None:
            return None

        max_wall_s = resolve_wall_cap(
            self.max_wall_s, self.max_wall_s_total, self.wall_elapsed_s()
        )
        if max_wall_s is None:
            return None

        max_budget_usd = resolve_usd_cap(
            self.max_budget_usd, self.max_budget_usd_total, self.cost_used
        )
        if max_budget_usd is False:
            return None

        return {
            "max_runs": max_runs,
            "max_stale_runs": self.max_stale_runs,
            "max_turns": max_turns,
            "max_wall_s": max_wall_s,
            "max_budget_usd": max_budget_usd,
        }

    def note_session(self, *, runs: int, turns: int, cost_usd: float | None) -> None:
        self.runs_used += runs
        self.turns_used += turns
        if cost_usd is not None:
            self.cost_used += cost_usd


@dataclass
class LineOutcome:
    target: TargetLine
    index: int
    status: str
    covered_by: str | None = None
    out_dir: Path | None = None
    reason: str | None = None
    covering_run: int | None = None
    covering_tool: str | None = None


def tools_instrumenting_target(
    indexes: dict[ToolName, SymcovIndex], target: TargetLine
) -> list[ToolName]:
    return [name for name, idx in indexes.items() if idx.is_instrumented(target)]


def find_covering_run(
    target: TargetLine,
    runs: list[RunResult],
    indexes: dict[ToolName, SymcovIndex],
    *,
    prefer: RunResult | None = None,
) -> tuple[RunResult, int] | None:
    """Return ``(run, 1-based index)`` that fully covers *target*, if any."""
    candidates: list[tuple[RunResult, int]] = []
    for i, run in enumerate(runs, start=1):
        index = indexes.get(run.tool)
        if index is None or not index.is_instrumented(target):
            continue
        measure = measure_hits(index, target, run.hit_points)
        if measure.status == "covered":
            candidates.append((run, i))
    if not candidates:
        return None
    if prefer is not None:
        for run, i in candidates:
            if run is prefer:
                return run, i
    return candidates[-1]


def credit_pending_lines(
    *,
    pending: list[tuple[int, TargetLine]],
    runs: list[RunResult],
    indexes: dict[ToolName, SymcovIndex],
    out_dir: Path,
    prefer: RunResult | None = None,
    multi: bool,
) -> list[LineOutcome]:
    """Mark pending lines covered by any run in *runs*; write their outputs."""
    credited: list[LineOutcome] = []
    still: list[tuple[int, TargetLine]] = []
    for index, target in pending:
        found = find_covering_run(target, runs, indexes, prefer=prefer)
        if found is None:
            still.append((index, target))
            continue
        run, run_i = found
        line_dir = line_out_dir(out_dir, index, target) if multi else out_dir
        write_outputs(
            line_dir,
            target=target,
            status="covered",
            result=run,
            history=[],
            extra={
                "covered_by": "collateral",
                "covering_run": run_i,
                "covering_tool": run.tool,
            },
        )
        credited.append(
            LineOutcome(
                target=target,
                index=index,
                status="covered",
                covered_by="collateral",
                out_dir=line_dir,
                covering_run=run_i,
                covering_tool=run.tool,
            )
        )
    pending[:] = still
    return credited


def write_summary(out_dir: Path, outcomes: list[LineOutcome]) -> Path:
    path = out_dir / "summary.json"
    payload = {
        "targets": [
            {
                "target": str(o.target),
                "index": o.index,
                "status": o.status,
                "covered_by": o.covered_by,
                "out_dir": (
                    str(o.out_dir.relative_to(out_dir))
                    if o.out_dir is not None and o.out_dir != out_dir
                    else (None if o.out_dir is None else ".")
                ),
                "reason": o.reason,
                "covering_run": o.covering_run,
                "covering_tool": o.covering_tool,
            }
            for o in outcomes
        ]
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def multi_line_exit_code(outcomes: list[LineOutcome]) -> int:
    if not outcomes:
        return 1
    statuses = [o.status for o in outcomes]
    if all(s == "covered" for s in statuses):
        return 0
    if all(s == "not_instrumented" for s in statuses):
        return 2
    instrumented = [s for s in statuses if s != "not_instrumented"]
    if instrumented and all(s == "likely_unreachable" for s in instrumented):
        return 3
    return 1
