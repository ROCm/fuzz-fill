# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""In-process MCP tools for the fill-line agent."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Awaitable, Callable

from fill_line_agent.args_policy import validate_argv
from fill_line_agent.oracle import (
    InputFormat,
    stream_page,
    stream_tail,
)
from fill_line_agent.render import command_line, write_analysis, write_attempt
from fill_line_agent.session_state import (
    CONDITION_STATUSES,
    MIN_VALID_RUNS_FOR_UNREACHABLE,
    VERDICTS,
    SessionState,
)
from fuzz_fill.log import get_logger

logger = get_logger("fill_line_agent.tools")

DIFF_PAGE_LINES = 200
GREP_MAX_MATCHES = 40
GREP_MAX_LINE_LEN = 240
SOURCE_MAX_LINES = 200

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


def _text(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(payload, indent=2, default=str)}]
    }


def _error(message: str) -> dict[str, Any]:
    return _text({"ok": False, "error": message})


def _resolve_under_root(root: Path, rel: str) -> Path:
    candidate = (root / rel).resolve()
    root_resolved = root.resolve()
    if root_resolved not in candidate.parents and candidate != root_resolved:
        raise ValueError(f"path escapes llvm-src root: {rel!r}")
    return candidate


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
                f"{r[0]}-{r[1]}" for r in args["ranges"] if isinstance(r, list) and len(r) == 2
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


def build_fill_tools(state: SessionState):
    """Create MCP tool callables closed over *state*."""
    try:
        from claude_agent_sdk import create_sdk_mcp_server, tool
    except ImportError as exc:  # pragma: no cover - dependency optional
        raise RuntimeError(
            "claude-agent-sdk is required for fill-line; "
            "install with: pip install 'fuzz-fill[agent]'"
        ) from exc

    def tracked(
        name: str,
        description: str,
        schema: dict[str, Any] | type,
        handler: ToolHandler,
    ):
        @tool(name, description, schema)
        async def wrapped(args: dict[str, Any]) -> dict[str, Any]:
            detail = _summarize_args(name, args if isinstance(args, dict) else {})
            state.tool_busy = True
            try:
                with state.steps.step(f"tool:{name}", detail):
                    result = await handler(args)
            finally:
                state.tool_busy = False
            state.note_tool_call(name)
            if name == "run_candidate":
                try:
                    body = json.loads(result["content"][0]["text"])
                    nearby_hits = sum(
                        1
                        for n in body.get("nearby") or []
                        if n.get("status") != "missed"
                    )
                    m = state.latest.measure if state.latest else None
                    if m is not None:
                        logger.info(
                            "run %s: exit=%s target=%s %s/%s fn=%s/%s nearby_hits=%s",
                            body.get("run"),
                            body.get("exit_code"),
                            m.status,
                            m.n_hit,
                            m.n_points,
                            m.function_n_hit,
                            m.function_n_points,
                            nearby_hits,
                        )
                    else:
                        logger.info(
                            "run_candidate result: exit=%s nearby_hits=%s",
                            body.get("exit_code"),
                            nearby_hits,
                        )
                except (KeyError, TypeError, json.JSONDecodeError, IndexError):
                    pass
            logger.info("%s", state.progress_line())
            return result

        return wrapped

    async def read_diff(args: dict[str, Any]) -> dict[str, Any]:
        offset = int(args.get("offset") or 0)
        text = state.diff_path.read_text(encoding="utf-8", errors="replace")
        page = stream_page(text, offset=offset, n_lines=DIFF_PAGE_LINES)
        return _text({"ok": True, "path": str(state.diff_path), **page})

    async def read_source(args: dict[str, Any]) -> dict[str, Any]:
        rel = str(args.get("path") or "")
        if not rel:
            return _error("path is required")
        ranges_in = args.get("ranges")
        if ranges_in:
            if not isinstance(ranges_in, list):
                return _error("ranges must be a list of [start, end] pairs")
            raw = ranges_in
        elif args.get("start") is not None and args.get("end") is not None:
            raw = [[args["start"], args["end"]]]
        else:
            return _error("give start and end, or ranges")
        ranges: list[tuple[int, int]] = []
        for item in raw:
            try:
                if isinstance(item, dict):
                    lo, hi = int(item["start"]), int(item["end"])
                else:
                    lo, hi = int(item[0]), int(item[1])
            except (KeyError, IndexError, TypeError, ValueError):
                return _error(f"bad range {item!r}; use [start, end]")
            ranges.append((min(lo, hi), max(lo, hi)))
        total = sum(hi - lo + 1 for lo, hi in ranges)
        if total > SOURCE_MAX_LINES:
            return _error(
                f"ranges too large ({total} lines); max {SOURCE_MAX_LINES} per call"
            )
        try:
            path = _resolve_under_root(state.llvm_src, rel)
        except ValueError as exc:
            return _error(str(exc))
        if not path.is_file():
            return _error(f"file not found: {rel}")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        chunks: list[dict[str, Any]] = []
        for lo, hi in ranges:
            lo = max(1, lo)
            hi = min(len(lines), hi)
            numbered = [f"{i}:{lines[i - 1]}" for i in range(lo, hi + 1)]
            chunks.append({"start": lo, "end": hi, "text": "\n".join(numbered)})
        if len(chunks) == 1:
            return _text({"ok": True, "path": rel, **chunks[0]})
        return _text({"ok": True, "path": rel, "ranges": chunks})

    async def grep_source(args: dict[str, Any]) -> dict[str, Any]:
        pattern = str(args["pattern"])
        path_glob = str(args.get("path_glob") or "**/*.{cpp,h,c,inc,td,ll,mir}")
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            return _error(f"invalid regex: {exc}")
        root = state.llvm_src.resolve()
        hits: list[str] = []
        globs = [path_glob]
        if "{" in path_glob and "}" in path_glob:
            pre, rest = path_glob.split("{", 1)
            body, post = rest.split("}", 1)
            globs = [f"{pre}{part}{post}" for part in body.split(",")]
        files: list[Path] = []
        for g in globs:
            files.extend(p for p in root.glob(g) if p.is_file())
        for path in sorted(set(files)):
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    shown = (
                        line
                        if len(line) <= GREP_MAX_LINE_LEN
                        else line[:GREP_MAX_LINE_LEN] + "..."
                    )
                    hits.append(f"{rel}:{i}:{shown}")
                    if len(hits) >= GREP_MAX_MATCHES:
                        return _text({"ok": True, "truncated": True, "matches": hits})
        return _text({"ok": True, "truncated": False, "matches": hits})

    async def instrumented_lines(args: dict[str, Any]) -> dict[str, Any]:
        tool_name = str(args["tool"])
        if tool_name not in state.oracle.indexes:
            return _error(f"unknown or unavailable tool: {tool_name}")
        rows = state.oracle.indexes[tool_name].instrumented_lines(
            str(args["path"]),
            int(args["start"]),
            int(args["end"]),
        )
        return _text({"ok": True, "tool": tool_name, "lines": rows})

    async def select_tool(args: dict[str, Any]) -> dict[str, Any]:
        choice = str(args["tool"])
        rationale = str(args.get("rationale") or "")
        if choice == "none":
            missing = str(args.get("missing_action") or "").strip()
            why = str(args.get("why_needed") or "").strip()
            if not missing or not why:
                return _error(
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
            return _text(
                {
                    "ok": True,
                    "selected": "none",
                    "gave_up": True,
                    "capability_gap": state.capability_gap,
                }
            )
        if choice not in ("opt", "llc"):
            return _error("tool must be opt, llc, or none")
        if choice not in state.allowed_tools:
            return _error(
                f"{choice} does not instrument the target; "
                f"allowed: {state.allowed_tools}"
            )
        state.selected_tool = choice  # type: ignore[assignment]
        state.selected_rationale = rationale
        state.history.append(
            {"event": "select_tool", "tool": choice, "rationale": rationale}
        )
        return _text({"ok": True, "selected": choice, "rationale": rationale})

    async def record_analysis(args: dict[str, Any]) -> dict[str, Any]:
        verdict = str(args.get("verdict") or "").strip()
        if verdict not in VERDICTS:
            return _error(
                f"verdict must be one of {sorted(VERDICTS)}; got {verdict!r}"
            )
        conditions_raw = args.get("conditions")
        if not isinstance(conditions_raw, list) or not conditions_raw:
            return _error("conditions must be a non-empty list")
        conditions: list[dict[str, str]] = []
        for i, item in enumerate(conditions_raw):
            if not isinstance(item, dict):
                return _error(f"conditions[{i}] must be an object")
            condition = str(item.get("condition") or "").strip()
            status = str(item.get("status") or "").strip()
            evidence = str(item.get("evidence") or "").strip()
            if not condition:
                return _error(f"conditions[{i}].condition is required")
            if status not in CONDITION_STATUSES:
                return _error(
                    f"conditions[{i}].status must be one of "
                    f"{sorted(CONDITION_STATUSES)}; got {status!r}"
                )
            entry = {
                "condition": condition,
                "status": status,
                "evidence": evidence,
            }
            conditions.append(entry)
        if verdict == "likely_unreachable":
            n_valid = len(state.valid_runs())
            if n_valid < MIN_VALID_RUNS_FOR_UNREACHABLE:
                return _error(
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
        return _text(
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
            return _error("call select_tool before run_candidate")
        if state.analysis is None:
            return _error("call record_analysis before run_candidate")
        testing = str(args.get("testing") or "").strip()
        if not testing:
            return _error(
                "testing is required: which condition this attempt tries to make true"
            )
        reason = state.budget_exhausted()
        if reason:
            state.gave_up = True
            state.give_up_reason = reason
            state.stop_requested = True
            return _error(reason)
        fmt_raw = str(args.get("format") or "ll")
        if fmt_raw not in ("ll", "mir"):
            return _error("format must be ll or mir")
        fmt: InputFormat = fmt_raw  # type: ignore[assignment]
        argv_in = args.get("args") or []
        if not isinstance(argv_in, list):
            return _error("args must be a list of strings")
        try:
            argv = validate_argv(state.selected_tool, list(argv_in), fmt)
        except ValueError as exc:
            return _error(str(exc))
        input_text = str(args.get("input") or "")
        if not input_text.strip():
            return _error("input must be non-empty IR or MIR")

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

        payload: dict[str, Any] = {
            "ok": True,
            "run": len(state.runs),
            "tool": result.tool,
            "format": result.fmt,
            "testing": testing,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
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
        return _text(payload)

    async def compare_output(args: dict[str, Any]) -> dict[str, Any]:
        del args
        if state.latest is None:
            return _text({"ok": False, "changed": False, "reason": "no_run"})
        latest = state.latest
        return _text(
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
            return _text({"ok": False, "reason": "no_run"})
        stream = str(args.get("stream") or "stderr")
        if stream not in ("stdout", "stderr"):
            return _error("stream must be stdout or stderr")
        text = state.latest.stdout if stream == "stdout" else state.latest.stderr
        page = stream_page(text, offset=int(args.get("offset") or 0))
        return _text({"ok": True, "stream": stream, **page})

    async def target_line_covered(args: dict[str, Any]) -> dict[str, Any]:
        del args
        if state.latest is None or state.latest.measure is None:
            return _text(
                {
                    "ok": True,
                    "covered": False,
                    "reason": "no_run",
                    "target": str(state.target),
                }
            )
        m = state.latest.measure
        return _text(
            {
                "ok": True,
                "covered": m.status == "covered",
                "status": m.status,
                "n_hit": m.n_hit,
                "n_points": m.n_points,
                "target": str(state.target),
            }
        )

    async def accept(args: dict[str, Any]) -> dict[str, Any]:
        del args
        if state.latest is None or state.latest.measure is None:
            return _error("no_run")
        if state.latest.measure.status != "covered":
            return _error(
                f"latest run is {state.latest.measure.status} "
                f"({state.latest.measure.n_hit}/{state.latest.measure.n_points}); "
                "cannot accept"
            )
        state.accepted = True
        state.stop_requested = True
        return _text(
            {
                "ok": True,
                "accepted": True,
                "changed": state.latest.changed,
                "format": state.latest.fmt,
                "tool": state.latest.tool,
            }
        )

    async def give_up(args: dict[str, Any]) -> dict[str, Any]:
        if state.analysis is None:
            return _error("call record_analysis before give_up")
        verdict = str(state.analysis.get("verdict") or "")
        unreachable = verdict == "likely_unreachable"
        if unreachable:
            n_valid = len(state.valid_runs())
            if n_valid < MIN_VALID_RUNS_FOR_UNREACHABLE:
                return _error(
                    f"likely_unreachable needs at least "
                    f"{MIN_VALID_RUNS_FOR_UNREACHABLE} valid runs (exit 0); "
                    f"have {n_valid}"
                )
            state.likely_unreachable = True
        else:
            missing = str(args.get("missing_action") or "").strip()
            why = str(args.get("why_needed") or "").strip()
            if not missing or not why:
                return _error(
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
        return _text(payload)

    tool_list = [
        tracked(
            "read_diff",
            "Read a page of the PR diff. Use offset to page through large diffs.",
            {"offset": int},
            read_diff,
        ),
        tracked(
            "read_source",
            "Read LLVM source under --llvm-src. Give start/end (inclusive) for one "
            f"range, or ranges=[[start, end], ...] for several; max {SOURCE_MAX_LINES} "
            "lines per call.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start": {"type": "integer"},
                    "end": {"type": "integer"},
                    "ranges": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                        "description": "Several [start, end] ranges in the same file",
                    },
                },
                "required": ["path"],
            },
            read_source,
        ),
        tracked(
            "grep_source",
            "Search LLVM sources. Each hit is path:line:text.",
            {"pattern": str, "path_glob": str},
            grep_source,
        ),
        tracked(
            "instrumented_lines",
            "List instrumented lines for a tool in [start, end] of path.",
            {"tool": str, "path": str, "start": int, "end": int},
            instrumented_lines,
        ),
        tracked(
            "select_tool",
            "Select opt, llc, or none before running candidates. "
            "none gives up and requires missing_action and why_needed feedback.",
            {
                "type": "object",
                "properties": {
                    "tool": {
                        "type": "string",
                        "description": "opt, llc, or none",
                    },
                    "rationale": {"type": "string"},
                    "missing_action": {
                        "type": "string",
                        "description": "Required when tool=none: unavailable action that would help",
                    },
                    "why_needed": {
                        "type": "string",
                        "description": "Required when tool=none: why that action would help",
                    },
                    "workaround": {
                        "type": "string",
                        "description": "Optional: what you tried instead",
                    },
                },
                "required": ["tool"],
            },
            select_tool,
        ),
        tracked(
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
            record_analysis,
        ),
        tracked(
            "run_candidate",
            "Run the selected tool on LLVM IR or MIR. Requires prior "
            "record_analysis and a testing field naming the condition under test. "
            "Does not report the target line.",
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
                        "description": "Full IR or MIR text",
                    },
                    "format": {
                        "type": "string",
                        "description": "ll or mir",
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
            run_candidate,
        ),
        tracked(
            "compare_output",
            "Compare the latest run's captured compiler output to its input.",
            {},
            compare_output,
        ),
        tracked(
            "show_streams",
            "Page stdout or stderr from the latest run.",
            {"stream": str, "offset": int},
            show_streams,
        ),
        tracked(
            "target_line_covered",
            "Report whether the configured target line was fully covered in the latest run.",
            {},
            target_line_covered,
        ),
        tracked(
            "accept",
            "Accept the latest candidate if the target line is covered.",
            {},
            accept,
        ),
        tracked(
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
            give_up,
        ),
    ]
    server = create_sdk_mcp_server(name="cover", version="1.0.0", tools=tool_list)
    allowed = [f"mcp__cover__{t.name}" for t in tool_list]
    return server, allowed
