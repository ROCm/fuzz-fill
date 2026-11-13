# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Mutable session state shared by fill-line tools and the harness."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fill_line_agent.oracle import (
    CoverageOracle,
    MeasureResult,
    RunResult,
    TargetLine,
    ToolName,
)
from fill_line_agent.responses import ResponseLog
from fill_line_agent.steps import StepTracker

ProgressKey = tuple[int, int, int]
# (target_n_hit, function_n_hit, inverted closest distance; higher is better)

LLM_IDLE_TIMEOUT_S = 180.0
LLM_HEARTBEAT_S = 30.0
LLM_IDLE_RETRIES = 1
MIN_VALID_RUNS_FOR_UNREACHABLE = 3
ANALYSIS_STALE_AFTER_RUNS = 3
POLISH_RUNS_AFTER_COVER = 5

VERDICTS = frozenset({"likely_reachable", "likely_unreachable", "unknown"})
CONDITION_STATUSES = frozenset({"satisfied", "unsatisfied", "unknown"})


def progress_key(measure: MeasureResult | None) -> ProgressKey:
    if measure is None:
        return (0, 0, 0)
    closeness = 0
    if measure.closest_hit_distance is not None:
        closeness = max(0, 10_000 - measure.closest_hit_distance)
    return (measure.n_hit, measure.function_n_hit, closeness)


def _as_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


@dataclass
class SessionState:
    oracle: CoverageOracle
    target: TargetLine
    llvm_src: Path
    diff_path: Path
    max_runs: int
    max_stale_runs: int
    max_turns: int
    allowed_tools: list[ToolName]
    steps: StepTracker = field(default_factory=StepTracker)
    out_dir: Path | None = None
    max_wall_s: float = 0.0
    max_budget_usd: float | None = None
    model: str | None = None
    effort: str | None = None
    thinking_tokens: int | None = None
    responses: ResponseLog = field(default_factory=lambda: ResponseLog(None))

    selected_tool: ToolName | None = None
    selected_rationale: str | None = None
    runs: list[RunResult] = field(default_factory=list)
    latest: RunResult | None = None
    best_progress: ProgressKey = (0, 0, 0)
    stale_runs: int = 0
    gave_up: bool = False
    give_up_reason: str | None = None
    capability_gap: dict[str, object] | None = None
    likely_unreachable: bool = False
    accepted: bool = False
    accepted_by: str | None = None
    first_covered_run: int | None = None
    stop_requested: bool = False
    history: list[dict[str, object]] = field(default_factory=list)

    analysis: dict[str, object] | None = None
    analysis_calls: int = 0
    runs_at_analysis: int = 0
    progress_at_analysis: ProgressKey = (0, 0, 0)

    sdk_turns: int = 0
    tool_calls: int = 0
    tool_calls_by_name: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    runs_ok: int = 0
    runs_nonzero: int = 0
    runs_timeout: int = 0
    llm_wait_s: float = 0.0
    llm_idle_retries_used: int = 0
    tool_busy: bool = False
    session_started_at: float = field(default_factory=time.perf_counter)

    tokens_in: int = 0
    tokens_out: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    total_cost_usd: float | None = None
    usage_raw: dict[str, Any] | None = None
    model_usage: dict[str, Any] | None = None
    duration_api_ms: int | None = None

    def wall_elapsed_s(self) -> float:
        return time.perf_counter() - self.session_started_at

    def record_run(
        self,
        result: RunResult,
        *,
        attempt_path: str | None = None,
        testing: str | None = None,
    ) -> None:
        self.runs.append(result)
        self.latest = result
        if (
            self.first_covered_run is None
            and result.measure is not None
            and result.measure.status == "covered"
        ):
            self.first_covered_run = len(self.runs)
        if result.timed_out:
            self.runs_timeout += 1
        elif result.exit_code == 0:
            self.runs_ok += 1
        else:
            self.runs_nonzero += 1
        key = progress_key(result.measure)
        if key > self.best_progress:
            self.best_progress = key
            self.stale_runs = 0
        else:
            self.stale_runs += 1
        entry: dict[str, object] = {
            "run": len(self.runs),
            "tool": result.tool,
            "fmt": result.fmt,
            "argv": result.argv,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "changed": result.changed,
            "target_status": result.measure.status if result.measure else None,
            "target_hit": result.measure.n_hit if result.measure else None,
            "target_points": result.measure.n_points if result.measure else None,
            "function_hit": result.measure.function_n_hit if result.measure else None,
            "function_points": (
                result.measure.function_n_points if result.measure else None
            ),
            "closest_hit_distance": (
                result.measure.closest_hit_distance if result.measure else None
            ),
        }
        if attempt_path is not None:
            entry["attempt"] = attempt_path
        if testing is not None:
            entry["testing"] = testing
        self.history.append(entry)

    def note_tool_call(self, name: str) -> None:
        self.tool_calls += 1
        self.tool_calls_by_name[name] += 1

    def note_capability_gap(
        self,
        *,
        missing_action: str,
        why_needed: str,
        workaround: str | None = None,
    ) -> None:
        gap: dict[str, object] = {
            "missing_action": missing_action.strip(),
            "why_needed": why_needed.strip(),
        }
        if workaround and workaround.strip():
            gap["workaround"] = workaround.strip()
        self.capability_gap = gap
        self.history.append({"event": "capability_gap", **gap})

    def valid_runs(self) -> list[RunResult]:
        return [r for r in self.runs if r.exit_code == 0 and not r.timed_out]

    def note_analysis(self, analysis: dict[str, object]) -> None:
        self.analysis = dict(analysis)
        self.analysis_calls += 1
        self.runs_at_analysis = len(self.runs)
        self.progress_at_analysis = progress_key(
            self.latest.measure if self.latest is not None else None
        )
        self.history.append({"event": "analysis", **dict(analysis)})

    def analysis_entries(self) -> list[dict[str, object]]:
        """Every recorded analysis, oldest first, with the run count at the time."""
        out: list[dict[str, object]] = []
        runs_seen = 0
        for entry in self.history:
            if "run" in entry:
                runs_seen = int(entry["run"])  # type: ignore[arg-type]
            elif entry.get("event") == "analysis":
                item = {k: v for k, v in entry.items() if k != "event"}
                out.append({"after_runs": runs_seen, **item})
        return out

    def analysis_stale_reason(
        self, latest_measure: MeasureResult | None = None
    ) -> str | None:
        if self.analysis is None:
            return None
        if latest_measure is None and self.latest is not None:
            latest_measure = self.latest.measure
        key = progress_key(latest_measure)
        if key > self.progress_at_analysis:
            return "new coverage near the target since your last analysis"
        if len(self.runs) - self.runs_at_analysis >= ANALYSIS_STALE_AFTER_RUNS:
            return f"{ANALYSIS_STALE_AFTER_RUNS} runs since your last analysis"
        return None

    def note_usage(self, usage: dict[str, Any] | None) -> None:
        if not usage:
            return
        # Accept both snake_case and camelCase keys from SDK messages.
        self.tokens_in += _as_int(
            usage.get("input_tokens", usage.get("inputTokens", 0))
        )
        self.tokens_out += _as_int(
            usage.get("output_tokens", usage.get("outputTokens", 0))
        )
        self.cache_read_tokens += _as_int(
            usage.get(
                "cache_read_input_tokens",
                usage.get("cacheReadInputTokens", 0),
            )
        )
        self.cache_creation_tokens += _as_int(
            usage.get(
                "cache_creation_input_tokens",
                usage.get("cacheCreationInputTokens", 0),
            )
        )

    def note_result_usage(
        self,
        *,
        usage: dict[str, Any] | None,
        model_usage: dict[str, Any] | None,
        total_cost_usd: float | None,
        duration_api_ms: int | None,
    ) -> None:
        if usage:
            self.usage_raw = dict(usage)
            # Prefer final totals over accumulated per-turn sums.
            self.tokens_in = _as_int(
                usage.get("input_tokens", usage.get("inputTokens", self.tokens_in))
            )
            self.tokens_out = _as_int(
                usage.get("output_tokens", usage.get("outputTokens", self.tokens_out))
            )
            self.cache_read_tokens = _as_int(
                usage.get(
                    "cache_read_input_tokens",
                    usage.get("cacheReadInputTokens", self.cache_read_tokens),
                )
            )
            self.cache_creation_tokens = _as_int(
                usage.get(
                    "cache_creation_input_tokens",
                    usage.get("cacheCreationInputTokens", self.cache_creation_tokens),
                )
            )
        if model_usage is not None:
            self.model_usage = dict(model_usage)
        if total_cost_usd is not None:
            self.total_cost_usd = float(total_cost_usd)
        if duration_api_ms is not None:
            self.duration_api_ms = int(duration_api_ms)

    def covered_runs(self) -> list[RunResult]:
        return [
            r
            for r in self.runs
            if r.measure is not None and r.measure.status == "covered"
        ]

    def covered_run_numbers(self) -> list[int]:
        """1-based run numbers that fully covered the target."""
        return [
            i
            for i, r in enumerate(self.runs, start=1)
            if r.measure is not None and r.measure.status == "covered"
        ]

    def runs_since_first_cover(self) -> int | None:
        if self.first_covered_run is None:
            return None
        return len(self.runs) - self.first_covered_run

    def pick_fallback_candidate(self) -> RunResult | None:
        covered = self.covered_runs()
        if not covered:
            return None
        changed = [r for r in covered if r.changed]
        return changed[-1] if changed else covered[-1]

    def budget_exhausted(self, *, idle_s: float = 0.0) -> str | None:
        if len(self.runs) >= self.max_runs:
            return f"max_runs reached ({self.max_runs})"
        if (
            self.max_stale_runs > 0
            and self.runs
            and self.stale_runs >= self.max_stale_runs
        ):
            return f"max_stale_runs reached ({self.max_stale_runs})"
        if self.max_turns > 0 and self.sdk_turns >= self.max_turns:
            return f"max_turns reached ({self.max_turns})"
        if self.max_wall_s > 0 and self.wall_elapsed_s() >= self.max_wall_s:
            return f"max_wall_s reached ({self.max_wall_s:g})"
        if idle_s >= LLM_IDLE_TIMEOUT_S:
            return f"llm_idle_timeout reached ({LLM_IDLE_TIMEOUT_S:g}s)"
        return None

    def quota_dict(self) -> dict[str, object]:
        q: dict[str, object] = {
            "runs": len(self.runs),
            "max_runs": self.max_runs,
            "runs_remaining": max(0, self.max_runs - len(self.runs)),
            "stale_runs": self.stale_runs,
            "max_stale_runs": self.max_stale_runs,
            "stale_remaining": (
                max(0, self.max_stale_runs - self.stale_runs)
                if self.max_stale_runs > 0
                else None
            ),
            "sdk_turns": self.sdk_turns,
            "max_turns": self.max_turns,
            "turns_remaining": (
                max(0, self.max_turns - self.sdk_turns) if self.max_turns > 0 else None
            ),
        }
        if self.max_wall_s > 0:
            elapsed = self.wall_elapsed_s()
            q["wall_s"] = round(elapsed, 1)
            q["max_wall_s"] = self.max_wall_s
            q["wall_remaining_s"] = round(max(0.0, self.max_wall_s - elapsed), 1)
        if self.max_budget_usd is not None:
            q["max_budget_usd"] = self.max_budget_usd
            q["cost_usd"] = self.total_cost_usd
        return q

    def stats_dict(self) -> dict[str, object]:
        return {
            "tool_calls": self.tool_calls,
            "tool_calls_by_name": dict(self.tool_calls_by_name),
            "sdk_turns": self.sdk_turns,
            "runs_ok": self.runs_ok,
            "runs_fail": self.runs_nonzero,
            "runs_timeout": self.runs_timeout,
            "covered_runs": len(self.covered_runs()),
            "llm_wait_s": round(self.llm_wait_s, 3),
            "llm_idle_retries_used": self.llm_idle_retries_used,
            "analysis_calls": self.analysis_calls,
            "valid_runs": len(self.valid_runs()),
            "llm_responses": self.responses.summary(),
        }

    def usage_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
        }
        if self.total_cost_usd is not None:
            out["total_cost_usd"] = self.total_cost_usd
        if self.duration_api_ms is not None:
            out["duration_api_ms"] = self.duration_api_ms
        if self.usage_raw is not None:
            out["raw"] = self.usage_raw
        if self.model_usage is not None:
            out["model_usage"] = self.model_usage
        return out

    def usage_line(self) -> str:
        bits = [f"tokens_in={self.tokens_in}", f"tokens_out={self.tokens_out}"]
        if self.total_cost_usd is not None:
            bits.append(f"cost=${self.total_cost_usd:.4f}")
        return " ".join(bits)

    def quota_line(self) -> str:
        q = self.quota_dict()
        parts = [f"quota runs={q['runs']}/{q['max_runs']}"]
        if self.max_stale_runs > 0:
            parts.append(f"stale={q['stale_runs']}/{q['max_stale_runs']}")
        else:
            parts.append(f"stale={q['stale_runs']}")
        parts.append(f"turns={q['sdk_turns']}/{q['max_turns']}")
        if self.max_wall_s > 0:
            parts.append(f"wall={q['wall_s']:.0f}/{self.max_wall_s:g}")
        if self.max_budget_usd is not None:
            cost = self.total_cost_usd
            cost_s = f"{cost:.2f}" if cost is not None else "?"
            parts.append(f"cost=${cost_s}/${self.max_budget_usd:g}")
        return " ".join(parts)

    def stats_line(self) -> str:
        s = self.stats_dict()
        return (
            f"stats tools={s['tool_calls']} "
            f"runs_ok={s['runs_ok']} runs_fail={s['runs_fail']} "
            f"covered={s['covered_runs']} llm_wait={s['llm_wait_s']:.1f}s"
        )

    def progress_line(self) -> str:
        return f"{self.quota_line()} | {self.stats_line()}"
