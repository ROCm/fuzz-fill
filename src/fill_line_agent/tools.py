# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""In-process MCP tools for the fill-line agent."""

from __future__ import annotations

import json
from typing import Any

from fill_line_agent.args_policy import validate_argv
from fill_line_agent.oracle import stream_page, stream_tail
from fill_line_agent.render import command_line, write_analysis, write_attempt
from fill_line_agent.toolset import (
    TOOL_NAMES,
    InputFormat,
    ToolName,
    allowed_source_formats,
    formats_for_tool,
    is_clang_tool,
    is_source_format,
    target_area_for_path,
)
from fill_line_agent.session_state import (
    CONDITION_STATUSES,
    MIN_VALID_RUNS_FOR_UNREACHABLE,
    POLISH_RUNS_AFTER_COVER,
    VERDICTS,
    SessionState,
)
from fill_line_agent.source_tools import source_tool_specs
from fill_line_agent.tool_common import build_mcp_server, error_payload, text_payload
from fuzz_fill.log import get_logger

logger = get_logger("fill_line_agent.tools")


def _nearby_payload(result) -> list[dict[str, Any]]:
    if result.measure is None:
        return []
    return [
        {
            "line": n.line,
            "distance": n.distance,
            "status": n.status,
            "n_hit": n.n_hit,
            "n_points": n.n_points,
        }
        for n in result.measure.nearby[:60]
    ]


def _summarize_args(name: str, args: dict[str, Any]) -> str:
    if name == "run_candidate":
        fmt = args.get("format", "ll")
        argv = args.get("args") or []
        inp = str(args.get("input") or "")
        return (
            f"format={fmt} testing={args.get('testing')!r} "
            f"args={argv!r} input_bytes={len(inp)}"
        )
    if name == "read_source":
        if args.get("ranges"):
            spans = ",".join(
                f"{r[0]}-{r[1]}"
                for r in args["ranges"]
                if isinstance(r, list) and len(r) == 2
            )
            return f"{args.get('path')}:{spans}"
        return f"{args.get('path')}:{args.get('start')}-{args.get('end')}"
    if name == "grep_source":
        return f"pattern={args.get('pattern')!r} glob={args.get('path_glob')!r}"
    if name == "select_tool":
        return f"tool={args.get('tool')!r}"
    if name == "instrumented_lines":
        return (
            f"{args.get('tool')} {args.get('path')}:"
            f"{args.get('start')}-{args.get('end')}"
        )
    if name == "show_streams":
        return f"stream={args.get('stream')} offset={args.get('offset')}"
    if name == "give_up":
        return f"reason={args.get('reason')!r}"
    if name == "read_diff":
        return f"offset={args.get('offset')}"
    if name == "record_analysis":
        return (
            f"verdict={args.get('verdict')!r} "
            f"conditions={len(args.get('conditions') or [])}"
        )
    return ""


def make_fill_handlers(state: SessionState) -> dict[str, Any]:
    """Return fill-line tool handlers closed over *state* (no MCP wrapping)."""

    async def select_tool(args: dict[str, Any]) -> dict[str, Any]:
        choice = str(args["tool"])
        rationale = str(args.get("rationale") or "")
        if choice == "none":
            missing = str(args.get("missing_action") or "").strip()
            why = str(args.get("why_needed") or "").strip()
            if not missing or not why:
                return error_payload(
                    "select_tool(none) requires missing_action and why_needed "
                    "(what capability would have helped and why)"
                )
            state.note_capability_gap(
                missing_action=missing,
                why_needed=why,
                workaround=str(args.get("workaround") or "") or None,
            )
            state.gave_up = True
            state.give_up_reason = rationale or "select_tool(none)"
            state.stop_requested = True
            logger.info(
                "capability gap: missing_action=%r why=%r",
                missing,
                why,
            )
            return text_payload(
                {
                    "ok": True,
                    "selected": "none",
                    "gave_up": True,
                    "capability_gap": state.capability_gap,
                }
            )
        if choice not in TOOL_NAMES:
            return error_payload(
                "tool must be opt, llc, clang_cc1, clang, clangxx, or none"
            )
        if choice not in state.allowed_tools:
            return error_payload(
                f"{choice} does not instrument the target; "
                f"allowed: {state.allowed_tools}"
            )
        selected: ToolName = choice  # type: ignore[assignment]
        state.selected_tool = selected
        state.selected_rationale = rationale
        state.history.append(
            {"event": "select_tool", "tool": choice, "rationale": rationale}
        )
        area = target_area_for_path(state.target.rel_path)
        diff_text = ""
        try:
            if state.diff_path is not None and state.diff_path.is_file():
                diff_text = state.diff_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            diff_text = ""
        src_fmts = (
            allowed_source_formats(rel_path=state.target.rel_path, diff_text=diff_text)
            if is_clang_tool(selected)
            else []
        )
        return text_payload(
            {
                "ok": True,
                "selected": choice,
                "rationale": rationale,
                "target_area": area,
                "allowed_formats": list(formats_for_tool(selected)),
                "allowed_source_formats": src_fmts,
                "hint": (
                    "clang/ targets: prefer clang_cc1/clang/clangxx. "
                    "llvm/ targets: prefer opt/llc; use clang only when the gap "
                    "depends on frontend-produced IR/MIR that would be contrived "
                    "to write by hand."
                    if is_clang_tool(selected) or area == "clang"
                    else "Prefer opt/llc for llvm/ mid-end and backend gaps."
                ),
            }
        )

    async def record_analysis(args: dict[str, Any]) -> dict[str, Any]:
        verdict = str(args.get("verdict") or "").strip()
        if verdict not in VERDICTS:
            return error_payload(
                f"verdict must be one of {sorted(VERDICTS)}; got {verdict!r}"
            )
        conditions_raw = args.get("conditions")
        if not isinstance(conditions_raw, list) or not conditions_raw:
            return error_payload("conditions must be a non-empty list")
        conditions: list[dict[str, str]] = []
        for i, item in enumerate(conditions_raw):
            if not isinstance(item, dict):
                return error_payload(f"conditions[{i}] must be an object")
            condition = str(item.get("condition") or "").strip()
            status = str(item.get("status") or "").strip()
            evidence = str(item.get("evidence") or "").strip()
            if not condition:
                return error_payload(f"conditions[{i}].condition is required")
            if status not in CONDITION_STATUSES:
                return error_payload(
                    f"conditions[{i}].status must be one of "
                    f"{sorted(CONDITION_STATUSES)}; got {status!r}"
                )
            conditions.append(
                {
                    "condition": condition,
                    "status": status,
                    "evidence": evidence,
                }
            )
        if verdict == "likely_unreachable":
            n_valid = len(state.valid_runs())
            if n_valid < MIN_VALID_RUNS_FOR_UNREACHABLE:
                return error_payload(
                    f"likely_unreachable needs at least "
                    f"{MIN_VALID_RUNS_FOR_UNREACHABLE} valid runs (exit 0); "
                    f"have {n_valid}"
                )
        analysis: dict[str, object] = {
            "verdict": verdict,
            "conditions": conditions,
        }
        next_step = str(args.get("next_step") or "").strip()
        if next_step:
            analysis["next_step"] = next_step
        state.note_analysis(analysis)
        n_sat = sum(1 for c in conditions if c["status"] == "satisfied")
        lines = [
            f"analysis {state.analysis_calls} (after {len(state.runs)} runs): "
            f"verdict={verdict} conditions={n_sat}/{len(conditions)} satisfied"
        ]
        for c in conditions:
            line = f"  [{c['status']}] {c['condition']}"
            if c["evidence"]:
                line += f"\n      evidence: {c['evidence']}"
            lines.append(line)
        if next_step:
            lines.append(f"  next_step: {next_step}")
        logger.info("%s", "\n".join(lines))
        if state.out_dir is not None:
            try:
                write_analysis(state.out_dir, state.analysis_entries())
            except OSError as exc:
                logger.warning("failed to write analysis.json: %s", exc)
        return text_payload(
            {
                "ok": True,
                "verdict": verdict,
                "valid_runs": len(state.valid_runs()),
                "conditions_satisfied": n_sat,
                "conditions_total": len(conditions),
            }
        )

    async def run_candidate(args: dict[str, Any]) -> dict[str, Any]:
        if state.selected_tool is None:
            return error_payload("call select_tool before run_candidate")
        if state.analysis is None:
            return error_payload("call record_analysis before run_candidate")
        testing = str(args.get("testing") or "").strip()
        if not testing:
            return error_payload(
                "testing is required: which condition this attempt tries to make true"
            )
        reason = state.budget_exhausted()
        if reason:
            state.gave_up = True
            state.give_up_reason = reason
            state.stop_requested = True
            return error_payload(reason)
        tool = state.selected_tool
        default_fmt = "c" if is_clang_tool(tool) else "ll"
        fmt_raw = str(args.get("format") or default_fmt)
        allowed_fmts = formats_for_tool(tool)
        if fmt_raw not in allowed_fmts:
            return error_payload(
                f"format must be one of {allowed_fmts} for {tool}; got {fmt_raw!r}"
            )
        fmt: InputFormat = fmt_raw  # type: ignore[assignment]
        if is_source_format(fmt):
            diff_text = ""
            try:
                if state.diff_path is not None and state.diff_path.is_file():
                    diff_text = state.diff_path.read_text(
                        encoding="utf-8", errors="replace"
                    )
            except OSError:
                diff_text = ""
            gate = allowed_source_formats(
                rel_path=state.target.rel_path, diff_text=diff_text
            )
            if fmt not in gate:
                return error_payload(
                    f"format={fmt} is not allowed for this target; "
                    f"allowed_source_formats={gate}"
                )
        argv_in = args.get("args") or []
        if not isinstance(argv_in, list):
            return error_payload("args must be a list of strings")
        try:
            argv = validate_argv(tool, list(argv_in), fmt)
        except ValueError as exc:
            return error_payload(str(exc))
        input_text = str(args.get("input") or "")
        if not input_text.strip():
            return error_payload("input must be non-empty source, IR, or MIR")

        run_no = len(state.runs) + 1
        argv_s = " ".join(argv)
        logger.info(
            "run %s: %s %s (%s, %s bytes) testing=%r",
            run_no,
            state.selected_tool,
            argv_s,
            fmt,
            len(input_text.encode("utf-8")),
            testing,
        )
        logger.info("run %s input:\n%s", run_no, input_text.rstrip("\n"))

        with state.steps.step(
            "oracle.run",
            f"{state.selected_tool} {argv_s} ({fmt})",
        ):
            result = state.oracle.run(state.selected_tool, argv, input_text, fmt)

        attempt_path: str | None = None
        if state.out_dir is not None:
            try:
                attempt_path = write_attempt(
                    state.out_dir,
                    result=result,
                    target=state.target,
                    attempt=run_no,
                    testing=testing,
                )
            except OSError as exc:
                logger.warning("failed to write attempt %s: %s", run_no, exc)
        state.record_run(result, attempt_path=attempt_path, testing=testing)
        logger.debug("run %s command: %s", run_no, command_line(result))

        m = result.measure
        nearby_hits = sum(
            1 for n in (m.nearby if m else []) if n.status != "missed"
        )
        if m is not None:
            logger.info(
                "run %s: exit=%s target=%s %s/%s fn=%s/%s nearby_hits=%s",
                run_no,
                result.exit_code,
                m.status,
                m.n_hit,
                m.n_points,
                m.function_n_hit,
                m.function_n_points,
                nearby_hits,
            )
        payload: dict[str, Any] = {
            "ok": True,
            "run": len(state.runs),
            "tool": result.tool,
            "format": result.fmt,
            "testing": testing,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "changed": result.changed,
            "target": {
                "line": str(state.target),
                "status": m.status if m else "uncovered",
                "n_hit": m.n_hit if m else 0,
                "n_points": m.n_points if m else 0,
            },
            "function": result.measure.function if result.measure else None,
            "function_n_hit": result.measure.function_n_hit if result.measure else 0,
            "function_n_points": (
                result.measure.function_n_points if result.measure else 0
            ),
            "nearby": _nearby_payload(result),
            "closest_hit_distance": (
                result.measure.closest_hit_distance if result.measure else None
            ),
            "runs_remaining": max(0, state.max_runs - len(state.runs)),
            "stale_runs": state.stale_runs,
        }
        if attempt_path is not None:
            payload["attempt"] = attempt_path
        since = state.runs_since_first_cover()
        if since is not None:
            payload["covered_runs"] = state.covered_run_numbers()
            payload["polish_runs_left"] = max(0, POLISH_RUNS_AFTER_COVER - since)
        if result.exit_code != 0 or result.timed_out:
            payload["stdout_tail"] = stream_tail(result.stdout)
            payload["stderr_tail"] = stream_tail(result.stderr)
        stale = state.analysis_stale_reason(result.measure)
        if stale:
            payload["analysis_stale"] = stale
        budget = state.budget_exhausted()
        if budget:
            state.gave_up = True
            state.give_up_reason = budget
            state.stop_requested = True
            payload["budget_exhausted"] = budget
        return text_payload(payload)

    async def compare_output(args: dict[str, Any]) -> dict[str, Any]:
        del args
        if state.latest is None:
            return text_payload({"ok": False, "changed": False, "reason": "no_run"})
        latest = state.latest
        return text_payload(
            {
                "ok": True,
                "changed": latest.changed,
                "exit_code": latest.exit_code,
                "timed_out": latest.timed_out,
                "capture_present": latest.capture is not None,
                "diff": latest.diff,
            }
        )

    async def show_streams(args: dict[str, Any]) -> dict[str, Any]:
        if state.latest is None:
            return text_payload({"ok": False, "reason": "no_run"})
        stream = str(args.get("stream") or "stderr")
        if stream not in ("stdout", "stderr"):
            return error_payload("stream must be stdout or stderr")
        text = state.latest.stdout if stream == "stdout" else state.latest.stderr
        page = stream_page(text, offset=int(args.get("offset") or 0))
        return text_payload({"ok": True, "stream": stream, **page})

    async def accept(args: dict[str, Any]) -> dict[str, Any]:
        if not state.runs:
            return error_payload("no_run")
        raw = args.get("run")
        if raw is None:
            run_no = len(state.runs)
        else:
            try:
                run_no = int(raw)
            except (TypeError, ValueError):
                return error_payload("run must be an integer run number")
            if not 1 <= run_no <= len(state.runs):
                return error_payload(f"run must be between 1 and {len(state.runs)}")
        chosen = state.runs[run_no - 1]
        m = chosen.measure
        if m is None or m.status != "covered":
            status = m.status if m else "uncovered"
            hit = f"{m.n_hit}/{m.n_points}" if m else "0/0"
            return error_payload(
                f"run {run_no} is {status} ({hit}); cannot accept. "
                f"Covering runs: {state.covered_run_numbers()}"
            )
        state.latest = chosen
        state.accepted = True
        state.accepted_by = "agent"
        state.stop_requested = True
        state.history.append(
            {"event": "accept", "run": run_no, "changed": chosen.changed}
        )
        return text_payload(
            {
                "ok": True,
                "accepted": True,
                "run": run_no,
                "changed": chosen.changed,
                "format": chosen.fmt,
                "tool": chosen.tool,
            }
        )

    async def give_up(args: dict[str, Any]) -> dict[str, Any]:
        if state.analysis is None:
            return error_payload("call record_analysis before give_up")
        verdict = str(state.analysis.get("verdict") or "")
        unreachable = verdict == "likely_unreachable"
        if unreachable:
            n_valid = len(state.valid_runs())
            if n_valid < MIN_VALID_RUNS_FOR_UNREACHABLE:
                return error_payload(
                    f"likely_unreachable needs at least "
                    f"{MIN_VALID_RUNS_FOR_UNREACHABLE} valid runs (exit 0); "
                    f"have {n_valid}"
                )
            state.likely_unreachable = True
        else:
            missing = str(args.get("missing_action") or "").strip()
            why = str(args.get("why_needed") or "").strip()
            if not missing or not why:
                return error_payload(
                    "give_up requires missing_action and why_needed "
                    "(one concrete action that was unavailable and why it would "
                    "have helped), unless the latest analysis verdict is "
                    "likely_unreachable"
                )
            state.note_capability_gap(
                missing_action=missing,
                why_needed=why,
                workaround=str(args.get("workaround") or "") or None,
            )
            logger.info(
                "capability gap: missing_action=%r why=%r",
                missing,
                why,
            )
        state.gave_up = True
        state.give_up_reason = str(args.get("reason") or "agent gave up")
        state.stop_requested = True
        payload: dict[str, Any] = {
            "ok": True,
            "gave_up": True,
            "reason": state.give_up_reason,
            "verdict": verdict,
            "analysis": state.analysis,
        }
        if state.capability_gap is not None:
            payload["capability_gap"] = state.capability_gap
        if unreachable:
            payload["likely_unreachable"] = True
        return text_payload(payload)

    return {
        "select_tool": select_tool,
        "record_analysis": record_analysis,
        "run_candidate": run_candidate,
        "compare_output": compare_output,
        "show_streams": show_streams,
        "accept": accept,
        "give_up": give_up,
    }


def fill_tool_specs(
    state: SessionState, handlers: dict[str, Any]
) -> list[tuple[str, str, dict[str, Any] | type, Any]]:
    """MCP tool specs for fill-line discovery handlers."""
    return [
        (
            "select_tool",
            "Select opt, llc, clang_cc1, clang, clangxx, or none before running "
            "candidates. none gives up and requires missing_action and why_needed "
            "feedback. Returns target_area and allowed formats.",
            {
                "type": "object",
                "properties": {
                    "tool": {
                        "type": "string",
                        "description": (
                            "opt, llc, clang_cc1, clang, clangxx, or none"
                        ),
                    },
                    "rationale": {"type": "string"},
                    "missing_action": {
                        "type": "string",
                        "description": (
                            "Required when tool=none: unavailable action that would help"
                        ),
                    },
                    "why_needed": {
                        "type": "string",
                        "description": (
                            "Required when tool=none: why that action would help"
                        ),
                    },
                    "workaround": {
                        "type": "string",
                        "description": "Optional: what you tried instead",
                    },
                },
                "required": ["tool"],
            },
            handlers["select_tool"],
        ),
        (
            "record_analysis",
            "Record reachability analysis: verdict, path conditions with status/"
            "evidence, and optional next_step. Required before the first "
            "run_candidate and before give_up. likely_unreachable needs at least "
            f"{MIN_VALID_RUNS_FOR_UNREACHABLE} valid (exit 0) runs.",
            {
                "type": "object",
                "properties": {
                    "verdict": {
                        "type": "string",
                        "description": (
                            "likely_reachable, likely_unreachable, or unknown"
                        ),
                    },
                    "conditions": {
                        "type": "array",
                        "description": (
                            "Path conditions needed to reach the target line"
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "condition": {"type": "string"},
                                "status": {
                                    "type": "string",
                                    "description": (
                                        "satisfied, unsatisfied, or unknown"
                                    ),
                                },
                                "evidence": {"type": "string"},
                            },
                            "required": ["condition", "status"],
                        },
                    },
                    "next_step": {
                        "type": "string",
                        "description": "What the next attempt will try to change",
                    },
                },
                "required": ["verdict", "conditions"],
            },
            handlers["record_analysis"],
        ),
        (
            "run_candidate",
            "Run the selected tool on IR/MIR or C/C++/HIP/OpenCL source. Requires "
            "prior record_analysis and a testing field naming the condition under "
            "test. Reports target coverage, changed, and nearby coverage.",
            {
                "type": "object",
                "properties": {
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tool argv after the binary name",
                    },
                    "input": {
                        "type": "string",
                        "description": "Full IR, MIR, or source text",
                    },
                    "format": {
                        "type": "string",
                        "description": "ll, mir, c, cpp, hip, or cl",
                    },
                    "testing": {
                        "type": "string",
                        "description": (
                            "Which analysis condition this attempt tries to make true"
                        ),
                    },
                },
                "required": ["args", "input", "testing"],
            },
            handlers["run_candidate"],
        ),
        (
            "compare_output",
            "Compare the latest run's captured compiler output to its input.",
            {},
            handlers["compare_output"],
        ),
        (
            "show_streams",
            "Page stdout or stderr from the latest run.",
            {"stream": str, "offset": int},
            handlers["show_streams"],
        ),
        (
            "accept",
            "Accept a run that covered the target line (default: the latest run).",
            {
                "type": "object",
                "properties": {
                    "run": {
                        "type": "integer",
                        "description": (
                            "Run number to accept; must have covered the target"
                        ),
                    },
                },
            },
            handlers["accept"],
        ),
        (
            "give_up",
            "Stop the search. Requires a prior record_analysis. "
            "Unless the latest verdict is likely_unreachable, also require "
            "missing_action and why_needed.",
            {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why the search is stopping",
                    },
                    "missing_action": {
                        "type": "string",
                        "description": (
                            "Unavailable action that would have helped "
                            "(not required when verdict is likely_unreachable)"
                        ),
                    },
                    "why_needed": {
                        "type": "string",
                        "description": (
                            "Why that action would have unblocked progress"
                        ),
                    },
                    "workaround": {
                        "type": "string",
                        "description": "Optional: what you tried instead",
                    },
                },
                "required": ["reason"],
            },
            handlers["give_up"],
        ),
    ]


def build_fill_tools(state: SessionState):
    """Create MCP tool callables closed over *state* (fill-line contracts)."""
    handlers = make_fill_handlers(state)
    return build_mcp_server(
        name="cover",
        version="1.0.0",
        state=state,
        tools=source_tool_specs(state) + fill_tool_specs(state, handlers),
        summarize=_summarize_args,
    )
