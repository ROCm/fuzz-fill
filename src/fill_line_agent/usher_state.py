# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Session state for the usher-test agent (composition, not fill-line subclass)."""

from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from fill_line_agent.lit_file import (
    RunShape,
    flags_from_argv,
    parse_all_runs,
    parse_run_body,
    run_shape,
    strip_lit_if_wrapper,
    triple_from_argv,
    verify_prefixes_from_argv,
)
from fill_line_agent.toolset import FORMAT_SUFFIX

_LEADING_NOT = re.compile(r"^not\s+(.*)$")
from fill_line_agent.oracle import CoverageOracle, RunResult, TargetLine, ToolName
from fill_line_agent.responses import ResponseLog
from fill_line_agent.session_state import LLM_IDLE_TIMEOUT_S, SessionState
from fill_line_agent.steps import StepTracker


@dataclass
class DeclaredStyle:
    """Agent-declared PR test style, grounded in files it actually read."""

    style_id: int
    suffix: str
    run_template: str
    shape: RunShape
    triple: str | None
    flags: list[str]
    evidence: list[str]
    rationale: str
    pr_grounded: bool
    extra_runs: list[str] = field(default_factory=list)
    verify_prefixes: list[str] | None = None

    def matches(self, test_text: str, fmt: str) -> tuple[bool, list[str]]:
        """Compare a proposal's primary RUN against this declaration."""
        reasons: list[str] = []
        if fmt != self.suffix:
            reasons.append(f"suffix {fmt} != {self.suffix}")
        runs = parse_all_runs(test_text)
        primary = next((r for r in runs if r.filecheck_args is not None), None)
        if primary is None and runs:
            primary = runs[0]
        if primary is None:
            reasons.append("no supported RUN")
            return False, reasons
        shape = run_shape(primary, fmt)
        if shape != self.shape:
            reasons.append(f"shape {shape} != {self.shape}")
        clang_shapes = ("clang_codegen", "clang_verify", "clang_ast", "clang_driver")
        # Clang: triple is variable; an extra RUN may use a different one.
        if self.triple and self.shape not in clang_shapes:
            triple = triple_from_argv(primary.argv)
            if triple != self.triple:
                reasons.append(f"triple {triple!r} != {self.triple!r}")
        if self.verify_prefixes is not None:
            got = verify_prefixes_from_argv(primary.argv)
            if got is None:
                reasons.append("missing -verify")
            elif sorted(got) != sorted(self.verify_prefixes):
                reasons.append(
                    f"verify prefixes {got!r} != {self.verify_prefixes!r}"
                )
        got_flags = set(flags_from_argv(primary.argv))
        required = [
            f for f in self.flags if f != "-verify" and not f.startswith("-verify=")
        ]
        missing = [f for f in required if f not in got_flags]
        if missing:
            reasons.append(f"missing flags {missing}")
        return (not reasons), reasons

    def to_json(self) -> dict[str, Any]:
        return {
            "style_id": self.style_id,
            "suffix": self.suffix,
            "run_template": self.run_template,
            "shape": self.shape,
            "triple": self.triple,
            "flags": list(self.flags),
            "evidence": list(self.evidence),
            "rationale": self.rationale,
            "pr_grounded": self.pr_grounded,
            "extra_runs": list(self.extra_runs),
            "verify_prefixes": (
                list(self.verify_prefixes) if self.verify_prefixes is not None else None
            ),
        }

def parse_run_template(template: str, suffix: str) -> DeclaredStyle | str:
    """Parse a declared RUN template; return a partial DeclaredStyle or an error string.

    The returned DeclaredStyle has placeholder style_id/evidence/rationale/pr_grounded;
    the caller fills those in.
    """
    body = strip_lit_if_wrapper(template.strip())
    # Drop a leading ``not `` so ``not llc …`` templates still classify.
    m_not = _LEADING_NOT.match(body)
    if m_not:
        body = m_not.group(1).strip()
    if suffix not in FORMAT_SUFFIX:
        return f"unsupported suffix {suffix!r}"
    parsed = parse_run_body(body)
    if parsed is None:
        return f"run_template does not parse as a supported RUN: {template!r}"
    shape = run_shape(parsed, suffix)
    return DeclaredStyle(
        style_id=0,
        suffix=suffix,
        run_template=template.strip(),
        shape=shape,
        triple=triple_from_argv(parsed.argv),
        flags=flags_from_argv(parsed.argv),
        evidence=[],
        rationale="",
        pr_grounded=False,
        verify_prefixes=verify_prefixes_from_argv(parsed.argv),
    )


@dataclass
class StandaloneProposal:
    """One proposed standalone lit test for a human to paste into llvm-project."""

    proposal_id: int
    test_text: str
    suggested_host: str
    note: str | None = None
    covered: bool = False
    filecheck_ok: bool = False
    coverage: dict[str, Any] = field(default_factory=dict)
    filecheck: dict[str, Any] = field(default_factory=dict)
    fmt: str = "ll"
    style_id: int | None = None
    style_ok: bool = False
    style_reasons: list[str] = field(default_factory=list)
    pr_style_ok: bool = False
    style_reason: str | None = None


@dataclass
class UsherState:
    """Usher session: standalone proposals + shared bookkeeping for run_session."""

    oracle: CoverageOracle
    target: TargetLine
    llvm_src: Path
    diff_path: Path
    fill_test_text: str
    fill_test_fmt: str
    filecheck_bin: Path
    max_placements: int
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
    update_scripts_dir: Path | None = None
    discovery: SessionState | None = None

    proposals: list[StandaloneProposal] = field(default_factory=list)
    latest_proposal: StandaloneProposal | None = None
    dump_results: list[RunResult] = field(default_factory=list)
    # run_no (1-based discovery run) -> whether the run matched the declared style
    run_style_ok: dict[int, bool] = field(default_factory=dict)

    accepted: bool = False
    accepted_by: str | None = None
    accepted_proposal: StandaloneProposal | None = None
    accepted_style_reason: str | None = None
    gave_up: bool = False
    give_up_reason: str | None = None
    stop_requested: bool = False
    history: list[dict[str, object]] = field(default_factory=list)

    read_paths: set[str] = field(default_factory=set)
    declared_styles: list[DeclaredStyle] = field(default_factory=list)
    pr_test_paths: list[str] = field(default_factory=list)
    mapped_test_dir: str | None = None

    sdk_turns: int = 0
    tool_calls: int = 0
    tool_calls_by_name: dict[str, int] = field(default_factory=lambda: defaultdict(int))
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

    # Discovery budgets (mirrored onto discovery SessionState when built).
    max_runs: int = 40
    max_stale_runs: int = 0

    def wall_elapsed_s(self) -> float:
        return time.perf_counter() - self.session_started_at

    def note_tool_call(self, name: str) -> None:
        self.tool_calls += 1
        self.tool_calls_by_name[name] += 1

    def proposal_actions(self) -> int:
        return (
            self.tool_calls_by_name.get("finalize_standalone", 0)
            + self.tool_calls_by_name.get("annotate_checks", 0)
        )

    def active_style(self) -> DeclaredStyle | None:
        return self.declared_styles[-1] if self.declared_styles else None

    def style_conforming_runs(self) -> int:
        """Count discovery runs that matched the declared PR style."""
        return sum(1 for ok in self.run_style_ok.values() if ok)

    def fallback_unlocked_by(self) -> str | None:
        """Why style-mismatched finalize/accept is allowed, or None if locked."""
        disc = self.discovery
        if disc is None:
            return None
        if disc.max_runs > 0 and self.style_conforming_runs() >= disc.max_runs:
            return "budget"
        if (
            disc.max_stale_runs > 0
            and disc.runs
            and disc.stale_runs >= disc.max_stale_runs
        ):
            return "stale"
        return None

    def fallback_unlocked(self) -> bool:
        return self.fallback_unlocked_by() is not None

    def budget_exhausted(self, *, idle_s: float = 0.0) -> str | None:
        if self.proposal_actions() >= self.max_placements:
            return f"max_placements reached ({self.max_placements})"
        if self.max_turns > 0 and self.sdk_turns >= self.max_turns:
            return f"max_turns reached ({self.max_turns})"
        if self.max_wall_s > 0 and self.wall_elapsed_s() >= self.max_wall_s:
            return f"max_wall_s reached ({self.max_wall_s:g})"
        if idle_s >= LLM_IDLE_TIMEOUT_S:
            return f"llm_idle_timeout reached ({LLM_IDLE_TIMEOUT_S:g}s)"
        # Also stop when discovery budget is exhausted and we already have a
        # covering proposal (or nothing more to try via placements).
        if self.discovery is not None:
            disc_reason = self.discovery.budget_exhausted()
            if disc_reason and self.fallback_unlocked():
                # Discovery can keep going for fallback-format runs; only
                # surface discovery exhaustion via fallback_unlocked, not as a
                # hard stop here (agent may still finalize + accept).
                pass
        return None

    def note_usage(self, usage: dict[str, Any] | None) -> None:
        if not usage:
            return
        self.tokens_in += _as_int(usage.get("input_tokens", usage.get("inputTokens", 0)))
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

    def valid_proposals(self) -> list[StandaloneProposal]:
        return [p for p in self.proposals if p.covered and p.filecheck_ok]

    def pick_fallback_proposal(self) -> StandaloneProposal | None:
        """Latest covered+FileCheck-ok proposal that would also pass accept's style gate."""
        unlocked = self.fallback_unlocked()
        eligible = [
            p for p in self.valid_proposals() if p.pr_style_ok or unlocked
        ]
        return eligible[-1] if eligible else None

    def apply_fallback(self) -> StandaloneProposal | None:
        proposal = self.pick_fallback_proposal()
        if proposal is None:
            return None
        self.accepted = True
        self.accepted_by = "harness_fallback"
        self.accepted_proposal = proposal
        self.latest_proposal = proposal
        self.history.append(
            {
                "event": "fallback_accept",
                "proposal": proposal.proposal_id,
                "suggested_host": proposal.suggested_host,
                "stop_reason": self.give_up_reason,
            }
        )
        return proposal

    def quota_dict(self) -> dict[str, object]:
        actions = self.proposal_actions()
        q: dict[str, object] = {
            "placements_actions": actions,
            "max_placements": self.max_placements,
            "placements_remaining": max(0, self.max_placements - actions),
            "sdk_turns": self.sdk_turns,
            "max_turns": self.max_turns,
            "turns_remaining": (
                max(0, self.max_turns - self.sdk_turns) if self.max_turns > 0 else None
            ),
            "style_conforming_runs": self.style_conforming_runs(),
            "fallback_unlocked": self.fallback_unlocked(),
            "fallback_unlocked_by": self.fallback_unlocked_by(),
        }
        if self.discovery is not None:
            q["discovery"] = self.discovery.quota_dict()
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
        out: dict[str, object] = {
            "tool_calls": self.tool_calls,
            "tool_calls_by_name": dict(self.tool_calls_by_name),
            "sdk_turns": self.sdk_turns,
            "proposals": len(self.proposals),
            "valid_proposals": len(self.valid_proposals()),
            "declared_styles": len(self.declared_styles),
            "llm_wait_s": round(self.llm_wait_s, 3),
            "llm_idle_retries_used": self.llm_idle_retries_used,
            "llm_responses": self.responses.summary(),
        }
        if self.discovery is not None:
            out["discovery_runs"] = len(self.discovery.runs)
            out["discovery_covered"] = self.discovery.covered_run_numbers()
        return out

    def progress_line(self) -> str:
        q = self.quota_dict()
        disc = ""
        if self.discovery is not None:
            disc = (
                f" runs={len(self.discovery.runs)}/{self.discovery.max_runs}"
                f" style_ok={self.style_conforming_runs()}"
            )
        return (
            f"quota actions={q['placements_actions']}/{q['max_placements']} "
            f"turns={q['sdk_turns']}/{q['max_turns']}{disc} | "
            f"stats tools={self.tool_calls} proposals={len(self.proposals)} "
            f"valid={len(self.valid_proposals())} styles={len(self.declared_styles)}"
        )

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


def _as_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
