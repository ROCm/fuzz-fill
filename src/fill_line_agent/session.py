# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Claude Agent SDK session loop for fill-line."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from fill_line_agent.oracle import CoverageOracle, TargetLine, ToolName
from fill_line_agent.responses import ResponseLog
from fill_line_agent.session_state import (
    LLM_HEARTBEAT_S,
    LLM_IDLE_RETRIES,
    LLM_IDLE_TIMEOUT_S,
    POLISH_RUNS_AFTER_COVER,
    SessionState,
)
from fill_line_agent.tools import build_fill_tools
from fill_line_agent.ping import gateway_settings
from fuzz_fill.log import get_logger

logger = get_logger("fill_line_agent.session")

CONTINUE_PROMPT = (
    "Continue from the latest tool results; do not repeat finished work."
)


SNIPPET_RADIUS = 20
FUNCTION_MAX_LINES = 250
FUNCTION_SIGNATURE_LINES = 4
DIFF_MAX_LINES = 250


def _source_snippet(
    llvm_src: Path,
    target: TargetLine,
    *,
    radius: int = 20,
    start: int | None = None,
    end: int | None = None,
) -> str:
    path = llvm_src / target.rel_path
    if not path.is_file():
        alt = llvm_src / Path(target.rel_path).name
        if alt.is_file():
            path = alt
        else:
            return f"(source not found at {path})"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    lo = max(1, start if start is not None else target.line - radius)
    hi = min(len(lines), end if end is not None else target.line + radius)
    out = []
    for i in range(lo, hi + 1):
        mark = ">>>" if i == target.line else "   "
        out.append(f"{mark} {i}:{lines[i - 1]}")
    return "\n".join(out)


def _diff_for_file(diff_path: Path | None, rel_path: str) -> str | None:
    """Return the PR diff section for *rel_path*, capped at DIFF_MAX_LINES."""
    if diff_path is None or not diff_path.is_file():
        return None
    text = diff_path.read_text(encoding="utf-8", errors="replace")
    section: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("diff --git "):
            inside = line.endswith(f" b/{rel_path}")
        if inside:
            section.append(line)
    if not section:
        return None
    if len(section) > DIFF_MAX_LINES:
        extra = len(section) - DIFF_MAX_LINES
        section = section[:DIFF_MAX_LINES] + [
            f"... ({extra} more diff lines; use read_diff for the rest)"
        ]
    return "\n".join(section)


def build_system_prompt(
    *,
    target: TargetLine,
    llvm_src: Path,
    allowed_tools: list[ToolName],
    max_runs: int,
    max_stale_runs: int,
    function_range: tuple[str, int, int] | None = None,
    diff_path: Path | None = None,
) -> str:
    source_title = "Source context"
    lo = target.line - SNIPPET_RADIUS
    hi = target.line + SNIPPET_RADIUS
    if function_range is not None:
        fn, fn_lo, fn_hi = function_range
        fn_lo = fn_lo - FUNCTION_SIGNATURE_LINES
        fn_hi = fn_hi + 1
        if fn_hi - fn_lo + 1 <= FUNCTION_MAX_LINES:
            lo, hi = min(lo, fn_lo), max(hi, fn_hi)
            source_title = f"Source context (includes all of {fn})"
    snippet = _source_snippet(llvm_src, target, start=lo, end=hi)
    diff_section = _diff_for_file(diff_path, target.rel_path)
    diff_block = (
        f"\nPR diff for {target.rel_path}:\n{diff_section}\n" if diff_section else ""
    )
    tools = ", ".join(allowed_tools) if allowed_tools else "(none)"
    budget = f"at most {max_runs} run_candidate calls"
    if max_stale_runs > 0:
        budget += f"; give up after {max_stale_runs} runs with no progress"
    return f"""You are fill-line, an agent that writes one lit test covering a single LLVM source line.

Target: {target}
Tools that instrument this line: {tools}
Budget: {budget}.

{source_title}:
{snippet}
{diff_block}
Working efficiently:
Every reply you send costs time, so do more per reply. Issue independent tool calls together in one reply (for example several read_source or grep_source calls). read_source accepts a list of ranges. Do not re-read code already shown above. Keep reasoning focused on the next input to try.

Reachability:
Being asked to fill a line does not mean it is reachable. Your job is to cover it, or to show it cannot be reached with these tools.
Before the first run_candidate, call record_analysis with the conditions needed to execute the target line (pass entry, callers, guards and branch directions). Each condition needs a status (satisfied, unsatisfied, or unknown) and evidence.
Use coverage as evidence: a guard line hit while the line after it is missed tells you which way the branch went.
Each run_candidate must set testing to the condition it tries to make true.
Update the analysis when a run changes your view or when a reply includes analysis_stale.
A likely_unreachable verdict needs at least 3 valid runs (exit 0) as evidence, plus conditions showing why. Then call give_up (capability-gap fields are not required for that verdict).

Rules:
1. You may only use the provided MCP tools. There is no Bash, Read, Edit, or Write.
2. First call select_tool with opt, llc, or none. If none of the available tools can reach this line, select none and include missing_action and why_needed feedback.
3. Prefer format=ll for opt. MIR (format=mir) is only valid with llc.
4. Call record_analysis before the first run_candidate and before give_up.
5. After each run_candidate, use the nearby-line window as a closeness hint. Read the source of the closest newly hit lines and adjust the input toward the branch that reaches the target. Use instrumented_lines for a wider static range.
6. Each run_candidate reply has a target field (status, n_hit, n_points) and changed. Only target.status == "covered" means the target was reached; a nearby hit is not success.
7. A non-zero exit (or timeout) is a failed invocation. Read stdout/stderr tails for unknown flags, usage errors, or IR/MIR verifier messages, fix the input or flags, and do not treat that run as evidence about the pass. Use show_streams for more of either stream.
8. After a run that exited 0, call compare_output to see what the compiler did.
9. When the target line is inside a pass, prefer a positive test when possible: the pass is applied, changed is true, and the diff shows the change that pass exists to make. For llc, prefer asking for IR/MIR after that pass (-stop-after=<pass> on .ll, -run-pass=<pass> on .mir) so the diff is the pass output rather than final assembly. A run that covers the line only on a bailout with an empty diff is a negative test; try a variant that makes the pass fire before accept. If you cannot build a positive test, you may accept the negative one.
10. Accept is your decision. Call accept(run=N) with any run whose target.status was "covered" (default: the latest run). Once a run covers the target, accept right away if it is a positive test. Otherwise try at most {POLISH_RUNS_AFTER_COVER} more runs to make it positive (the reply shows polish_runs_left and covered_runs), then accept the best covering run.
11. Call give_up when stuck. Unless the latest analysis verdict is likely_unreachable, give_up also requires missing_action and why_needed. If you select_tool(none), provide the same missing_action and why_needed fields.

Coverage rule: the target line is covered only when every SanitizerCoverage point on that line is hit in one run.
"""


def _is_assistant(message: object) -> bool:
    mtype = getattr(message, "type", None)
    return mtype == "assistant" or type(message).__name__ == "AssistantMessage"


def _is_result(message: object) -> bool:
    mtype = getattr(message, "type", None)
    return mtype == "result" or type(message).__name__ == "ResultMessage"


def _is_stream(message: object) -> bool:
    mtype = getattr(message, "type", None)
    return mtype == "stream_event" or type(message).__name__ == "StreamEvent"


def _log_sdk_message(message: object) -> bool:
    """Log an SDK message. Return True if quota/stats should be printed."""
    mtype = getattr(message, "type", None) or type(message).__name__
    if _is_stream(message):
        logger.debug("sdk stream event")
        return False
    if _is_assistant(message):
        content = getattr(message, "content", None)
        if content is None and hasattr(message, "message"):
            content = getattr(getattr(message, "message", None), "content", None)
        names: list[str] = []
        texts = 0
        for block in content or []:
            name = getattr(block, "name", None)
            if name:
                names.append(str(name))
            elif hasattr(block, "text") or (isinstance(block, dict) and "text" in block):
                texts += 1
            elif isinstance(block, dict) and block.get("name"):
                names.append(str(block["name"]))
        if names:
            logger.info("sdk assistant tool_use: %s", ", ".join(names))
        elif texts:
            logger.info("sdk assistant text (%d block(s))", texts)
        else:
            logger.info("sdk assistant message")
        return True
    if _is_result(message):
        logger.info(
            "sdk result: subtype=%s error=%s",
            getattr(message, "subtype", None),
            getattr(message, "is_error", None),
        )
        return True
    if mtype == "user" or type(message).__name__ == "UserMessage":
        logger.debug("sdk user/tool_result message")
        return False
    if mtype == "system" or type(message).__name__ == "SystemMessage":
        logger.debug("sdk message: %s", mtype)
        return False
    logger.debug("sdk message: %s", mtype)
    return False


def _record_message_usage(state: SessionState, message: object) -> None:
    if _is_assistant(message):
        state.note_usage(getattr(message, "usage", None))
        return
    if _is_result(message):
        state.note_result_usage(
            usage=getattr(message, "usage", None),
            model_usage=getattr(message, "model_usage", None),
            total_cost_usd=getattr(message, "total_cost_usd", None),
            duration_api_ms=getattr(message, "duration_api_ms", None),
        )


async def _give_up(state: SessionState, reason: str, client) -> None:
    state.gave_up = True
    state.give_up_reason = reason
    state.stop_requested = True
    logger.info("budget exhausted: %s", reason)
    try:
        await client.interrupt()
    except Exception as exc:  # pragma: no cover - best effort
        logger.debug("interrupt after give_up failed: %s", exc)


async def run_session(
    *,
    state: SessionState,
    api_key: str,
    base_url: str,
    user_ntid: str,
    max_turns: int | None,
) -> SessionState:
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage

    with state.steps.step("build_mcp_tools"):
        server, allowed_tools = build_fill_tools(state)
    system_prompt = build_system_prompt(
        target=state.target,
        llvm_src=state.llvm_src,
        allowed_tools=state.allowed_tools,
        max_runs=state.max_runs,
        max_stale_runs=state.max_stale_runs,
        function_range=state.oracle.function_line_range(state.target),
        diff_path=state.diff_path,
    )
    options_kwargs: dict = {
        "setting_sources": [],
        "settings": gateway_settings(
            api_key=api_key, base_url=base_url, user_ntid=user_ntid
        ),
        "tools": [],
        "mcp_servers": {"cover": server},
        "allowed_tools": allowed_tools,
        "system_prompt": system_prompt,
        "permission_mode": "dontAsk",
        "max_turns": max_turns,
        "cwd": str(state.llvm_src),
        "include_partial_messages": True,
    }
    if state.max_budget_usd is not None:
        options_kwargs["max_budget_usd"] = state.max_budget_usd
    if state.model:
        options_kwargs["model"] = state.model
    if state.effort:
        options_kwargs["effort"] = state.effort
    if state.thinking_tokens is not None:
        options_kwargs["thinking"] = (
            {"type": "disabled"}
            if state.thinking_tokens == 0
            else {"type": "enabled", "budget_tokens": state.thinking_tokens}
        )
    logger.info(
        "llm options: model=%s effort=%s thinking=%s",
        state.model or "(gateway default)",
        state.effort or "(default)",
        (
            "(default)"
            if state.thinking_tokens is None
            else "disabled"
            if state.thinking_tokens == 0
            else f"{state.thinking_tokens} tokens"
        ),
    )
    options = ClaudeAgentOptions(**options_kwargs)

    user_prompt = (
        f"Write a lit test that covers {state.target}. "
        f"Available instrumenting tools: {state.allowed_tools}. "
        "Inspect the diff and source, select a tool, then iterate with coverage feedback."
    )

    if max_turns is not None:
        state.max_turns = max_turns
    state.session_started_at = time.perf_counter()
    logger.info(
        "starting agent session target=%s tools=%s max_turns=%s",
        state.target,
        state.allowed_tools,
        state.max_turns,
    )
    logger.info("%s", state.progress_line())
    with state.steps.step("agent_session"):
        async with ClaudeSDKClient(options=options) as client:
            with state.steps.step("sdk_query_submit"):
                await client.query(user_prompt)

            idle_s = 0.0
            responses = state.responses
            aiter = client.receive_response().__aiter__()
            while True:
                wall = state.budget_exhausted()
                if wall and not state.accepted:
                    await _give_up(state, wall, client)
                    break

                try:
                    message = await asyncio.wait_for(
                        aiter.__anext__(),
                        timeout=LLM_HEARTBEAT_S,
                    )
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    if state.tool_busy:
                        # MCP tool is running inside the SDK; do not treat as LLM idle.
                        continue
                    idle_s += LLM_HEARTBEAT_S
                    state.llm_wait_s += LLM_HEARTBEAT_S
                    logger.info("waiting for llm (idle=%.0fs)", idle_s)
                    reason = state.budget_exhausted(idle_s=idle_s)
                    if reason is None:
                        continue
                    if reason.startswith("llm_idle_timeout") and (
                        state.llm_idle_retries_used < LLM_IDLE_RETRIES
                    ):
                        state.llm_idle_retries_used += 1
                        logger.info(
                            "llm idle; retrying once (%s/%s)",
                            state.llm_idle_retries_used,
                            LLM_IDLE_RETRIES,
                        )
                        try:
                            await client.interrupt()
                        except Exception as exc:  # pragma: no cover
                            logger.debug("interrupt before retry failed: %s", exc)
                        # Drain the aborted turn so the next query starts cleanly.
                        while True:
                            try:
                                drained = await asyncio.wait_for(
                                    aiter.__anext__(),
                                    timeout=LLM_HEARTBEAT_S,
                                )
                            except (StopAsyncIteration, asyncio.TimeoutError):
                                break
                            _record_message_usage(state, drained)
                            if _is_result(drained):
                                break
                        try:
                            await client.query(CONTINUE_PROMPT)
                        except Exception as exc:
                            await _give_up(
                                state,
                                f"llm_idle_retry_failed: {exc}",
                                client,
                            )
                            break
                        idle_s = 0.0
                        responses.finalize()
                        aiter = client.receive_response().__aiter__()
                        continue
                    await _give_up(state, reason, client)
                    break

                waited_note = idle_s
                idle_s = 0.0
                if _is_stream(message):
                    if responses.on_stream_event(getattr(message, "event", None)):
                        logger.info(
                            "llm streaming response %d...", len(responses.records) + 1
                        )
                    _log_sdk_message(message)
                    continue

                if _is_assistant(message):
                    responses.on_assistant(message)
                else:
                    responses.finalize()

                _record_message_usage(state, message)
                notable = _log_sdk_message(message)
                if notable and waited_note > 0:
                    logger.info("sdk event after %.0fs idle", waited_note)
                if _is_assistant(message):
                    state.sdk_turns += 1
                if notable:
                    logger.info("%s", state.progress_line())

                if state.stop_requested:
                    logger.info("stop requested; leaving receive loop")
                    break
                if isinstance(message, ResultMessage):
                    subtype = getattr(message, "subtype", None) or ""
                    if subtype == "error_max_budget_usd" or (
                        message.is_error
                        and "budget" in str(subtype)
                        and not state.accepted
                        and not state.gave_up
                    ):
                        cap = state.max_budget_usd
                        state.gave_up = True
                        state.give_up_reason = (
                            f"max_budget_usd reached (${cap:g})"
                            if cap is not None
                            else f"sdk_result_error:{subtype}"
                        )
                    elif message.is_error and not state.accepted and not state.gave_up:
                        state.gave_up = True
                        state.give_up_reason = f"sdk_result_error:{subtype}"
                    break
                budget = state.budget_exhausted()
                if budget and not state.accepted:
                    await _give_up(state, budget, client)
                    break
            responses.finalize()
            summary = responses.summary()
            if summary.get("responses"):
                logger.info(
                    "responses: n=%s total=%ss mean=%ss max=%ss (response %s) "
                    "out_tokens=%s thinking=%sch",
                    summary["responses"],
                    summary["total_s"],
                    summary["mean_s"],
                    summary["max_s"],
                    summary["slowest_response"],
                    summary["output_tokens"],
                    summary["thinking_chars"],
                )

    if state.accepted:
        return state
    # A covering run exists even when the session stopped on budget or give_up.
    fallback = state.pick_fallback_candidate()
    if fallback is not None:
        run_no = state.runs.index(fallback) + 1
        state.latest = fallback
        state.accepted = True
        state.accepted_by = "harness_fallback"
        state.likely_unreachable = False
        state.history.append(
            {
                "event": "fallback_accept",
                "run": run_no,
                "changed": fallback.changed,
                "stop_reason": state.give_up_reason,
            }
        )
        logger.info(
            "fallback accept run=%s changed=%s (stop reason: %s)",
            run_no,
            fallback.changed,
            state.give_up_reason,
        )
        return state
    if state.gave_up:
        return state
    if not state.gave_up:
        state.gave_up = True
        state.give_up_reason = state.give_up_reason or "session ended without accept"
    return state


def make_state(
    *,
    oracle: CoverageOracle,
    target: TargetLine,
    llvm_src: Path,
    diff_path: Path,
    max_runs: int,
    max_stale_runs: int,
    max_turns: int,
    max_wall_s: float = 0.0,
    max_budget_usd: float | None = None,
    out_dir: Path | None = None,
    model: str | None = None,
    effort: str | None = None,
    thinking_tokens: int | None = None,
) -> SessionState:
    allowed = oracle.tools_instrumenting()
    return SessionState(
        oracle=oracle,
        target=target,
        llvm_src=llvm_src,
        diff_path=diff_path,
        max_runs=max_runs,
        max_stale_runs=max_stale_runs,
        max_turns=max_turns,
        allowed_tools=allowed,
        max_wall_s=max_wall_s,
        max_budget_usd=max_budget_usd,
        out_dir=out_dir,
        model=model,
        effort=effort,
        thinking_tokens=thinking_tokens,
        responses=ResponseLog(out_dir),
    )
