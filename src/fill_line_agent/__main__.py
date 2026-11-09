# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""CLI entry point for fill-line."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path

from fill_line_agent.batch import (
    BatchBudget,
    LineOutcome,
    credit_pending_lines,
    line_out_dir,
    multi_line_exit_code,
    parse_targets,
    tools_instrumenting_target,
    write_summary,
)
from fill_line_agent.check_line import validate_test
from fill_line_agent.instrumented import load_instrumented
from fill_line_agent.oracle import CoverageOracle, RunResult, TargetLine, ToolName
from fill_line_agent.render import write_outputs
from fill_line_agent.session import make_state, run_session
from fill_line_agent.session_state import SessionState
from fill_line_agent.steps import StepTracker
from fill_line_agent.tool_runner import ToolRunner
from fill_line_agent.ping import (
    add_api_key_arguments,
    add_base_url_arguments,
    add_user_ntid_arguments,
    install_secret_redaction,
    ping_gateway,
    resolve_api_key,
    resolve_base_url,
    resolve_user_ntid,
)
from fuzz_fill.log import (
    DEFAULT_LOG_FILENAME,
    add_log_level_argument,
    add_log_to_file_argument,
    configure_logging,
    get_logger,
    resolve_log_file,
)

logger = get_logger("fill_line_agent")

_SESSION_OUTPUTS = (
    "result.json",
    "analysis.json",
    "responses.jsonl",
    "test.ll",
    "test.mir",
    DEFAULT_LOG_FILENAME,
)


def _clear_previous_outputs(out_dir: Path) -> None:
    """Remove files a previous session left in *out_dir* so outputs never mix."""
    if not out_dir.is_dir():
        return
    for name in _SESSION_OUTPUTS:
        (out_dir / name).unlink(missing_ok=True)
    shutil.rmtree(out_dir / "attempts", ignore_errors=True)


def _clear_batch_outputs(out_dir: Path) -> None:
    _clear_previous_outputs(out_dir)
    (out_dir / "summary.json").unlink(missing_ok=True)
    shutil.rmtree(out_dir / "lines", ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Find lit tests that cover one or more LLVM source lines."
    )
    parser.add_argument(
        "--target",
        action="append",
        required=True,
        help="path:line under llvm/ (repeatable; each line gets its own session)",
    )
    parser.add_argument("--llvm-src", type=Path, required=True)
    parser.add_argument("--diff", type=Path, required=True)
    add_api_key_arguments(parser)
    add_base_url_arguments(parser)
    add_user_ntid_arguments(parser)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--instrumented-bin-dir",
        type=Path,
        required=True,
        help="Directory containing instrumented opt and/or llc plus sancov",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=None,
        help="Per-session run_candidate cap (default: 40 when no --max-runs-total)",
    )
    parser.add_argument(
        "--max-runs-total",
        type=int,
        default=None,
        help="Cap on run_candidate calls across all sessions (unset = disabled)",
    )
    parser.add_argument(
        "--max-stale-runs",
        type=int,
        default=0,
        help="Stop a session after this many runs without progress (0 = disabled)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Per-session Agent SDK turn cap (default: 80 when no --max-turns-total)",
    )
    parser.add_argument(
        "--max-turns-total",
        type=int,
        default=None,
        help="Cap on SDK turns across all sessions (unset = disabled)",
    )
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument(
        "--max-wall-s",
        type=float,
        default=0.0,
        help="Per-session wall-clock budget in seconds (0 = disabled)",
    )
    parser.add_argument(
        "--max-wall-s-total",
        type=float,
        default=None,
        help="Wall-clock budget for the whole batch in seconds (unset = disabled)",
    )
    parser.add_argument(
        "--max-budget-usd",
        type=float,
        default=None,
        help="Per-session USD cost cap passed to the Agent SDK (unset = disabled)",
    )
    parser.add_argument(
        "--max-budget-usd-total",
        type=float,
        default=None,
        help="USD cost cap across all sessions (unset = disabled)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model alias or name, e.g. sonnet, haiku, opus (default: gateway setting)",
    )
    parser.add_argument(
        "--effort",
        choices=("low", "medium", "high", "xhigh", "max"),
        default=None,
        help="Reasoning effort; lower is faster (default: model default)",
    )
    parser.add_argument(
        "--thinking-tokens",
        type=int,
        default=None,
        help="Extended-thinking token budget; 0 disables thinking (default: model default)",
    )
    parser.add_argument(
        "--tools-runner",
        choices=("host", "docker"),
        default=None,
        help="Run opt/llc/sancov on the host or in Docker (default: host / FUZZ_FILL_TOOLS_RUNNER)",
    )
    parser.add_argument(
        "--tools-image",
        default=None,
        help="Docker image for --tools-runner=docker (default: FUZZ_FILL_TOOLS_IMAGE)",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Directory for per-run artifacts (default: temporary)",
    )
    parser.add_argument(
        "--skip-gateway-ping",
        action="store_true",
        help="Skip the pong preflight against the LLM gateway",
    )
    add_log_level_argument(parser)
    add_log_to_file_argument(parser)
    return parser


def _session_status(state: SessionState) -> str:
    if state.accepted and state.latest is not None:
        return "covered"
    if state.likely_unreachable:
        return "likely_unreachable"
    return "gave_up"


def _finish_session_outputs(
    *,
    state: SessionState,
    target: TargetLine,
    out_dir: Path,
    tools: dict[ToolName, Path],
    indexes: dict,
    sancov,
    timeout_s: float,
    runner: ToolRunner,
    steps: StepTracker,
) -> tuple[str, RunResult | None]:
    """Write session outputs; return ``(status, accepted_result_or_none)``."""
    status = _session_status(state)
    usage_bit = state.usage_line()
    finished = f"fill-line finished: status={status} target={target} | {state.progress_line()}"
    if usage_bit:
        finished = f"{finished} | {usage_bit}"
    logger.info("%s", finished)

    extra = {
        "steps": steps.as_dicts(),
        "quota": state.quota_dict(),
        "stats": state.stats_dict(),
        "usage": state.usage_dict(),
        "analysis": state.analysis,
        "covered_by": "session" if status == "covered" else None,
    }

    if state.accepted and state.latest is not None:
        with steps.step("write_outputs"):
            test_path = write_outputs(
                out_dir,
                target=target,
                status="covered",
                result=state.latest,
                history=state.history,
                extra={
                    "output_changed": state.latest.changed,
                    "give_up_reason": state.give_up_reason,
                    **extra,
                },
            )
        assert test_path is not None
        with steps.step("check_line_validate"):
            rc = validate_test(
                test_path=test_path,
                target=target,
                tools=tools,
                indexes=indexes,
                sancov_bin=sancov,
                timeout_s=timeout_s,
                runner=runner,
            )
        result_path = out_dir / "result.json"
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        payload["validated"] = rc == 0
        payload["steps"] = steps.as_dicts()
        payload["quota"] = state.quota_dict()
        payload["stats"] = state.stats_dict()
        payload["usage"] = state.usage_dict()
        payload["analysis"] = state.analysis
        result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        if rc != 0:
            logger.error("check-line failed after accept for %s", target)
            write_outputs(
                out_dir,
                target=target,
                status="gave_up",
                result=None,
                history=state.history,
                extra={
                    "reason": "check-line failed after accept",
                    "capability_gap": state.capability_gap,
                    **{k: v for k, v in extra.items() if k != "covered_by"},
                    "covered_by": None,
                },
            )
            return "gave_up", None
        print(f"covered: wrote {test_path}")
        return "covered", state.latest

    if state.capability_gap:
        logger.info(
            "capability gap recorded: %s",
            state.capability_gap.get("missing_action"),
        )
    write_outputs(
        out_dir,
        target=target,
        status=status,
        result=None,
        history=state.history,
        extra={
            "reason": state.give_up_reason or "gave up",
            "capability_gap": state.capability_gap,
            **{k: v for k, v in extra.items() if k != "covered_by"},
        },
    )
    if status == "likely_unreachable":
        print(f"likely_unreachable: {target}", file=sys.stderr)
    else:
        print(f"gave_up: {state.give_up_reason}", file=sys.stderr)
        if state.capability_gap:
            print(
                f"capability_gap: {state.capability_gap.get('missing_action')}",
                file=sys.stderr,
            )
    return status, None


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.thinking_tokens is not None and 0 < args.thinking_tokens < 1024:
        parser.error("--thinking-tokens must be 0 (disabled) or at least 1024")

    targets = parse_targets(args.target)
    if not targets:
        parser.error("pass at least one --target")
    multi = len(targets) > 1

    out_dir = args.out_dir.expanduser().resolve()
    # Always drop prior batch leftovers so single- and multi-target runs do not mix.
    _clear_batch_outputs(out_dir)
    configure_logging(
        args.log_level,
        log_file=resolve_log_file(out_dir, args.log_to_file),
    )
    steps = StepTracker()

    llvm_src = args.llvm_src.expanduser().resolve()
    diff_path = args.diff.expanduser().resolve()
    bin_dir = args.instrumented_bin_dir.expanduser().resolve()
    api_key = resolve_api_key(api_key=args.api_key, key_file=args.key_file)
    base_url = resolve_base_url(base_url=args.base_url, base_url_file=args.base_url_file)
    user_ntid = resolve_user_ntid(user_ntid=args.user_ntid)
    install_secret_redaction(api_key, base_url, user_ntid)
    if args.api_key is not None:
        args.api_key = "<redacted>"
    if args.base_url is not None:
        args.base_url = "<redacted>"
    if args.user_ntid is not None:
        args.user_ntid = "<redacted>"

    if not llvm_src.is_dir():
        raise SystemExit(f"llvm-src not found: {llvm_src}")
    if not diff_path.is_file():
        raise SystemExit(f"diff not found: {diff_path}")

    logger.info(
        "fill-line targets=%s runner=%s",
        [str(t) for t in targets],
        args.tools_runner or "host",
    )
    runner = ToolRunner.from_cli(mode=args.tools_runner, image=args.tools_image)
    logger.info("tools-runner mode=%s image=%s", runner.mode, runner.image)

    work_ctx = (
        tempfile.TemporaryDirectory(prefix="fill-line-")
        if args.work_dir is None
        else None
    )
    work_root = (
        Path(work_ctx.name) if work_ctx is not None else args.work_dir.resolve()
    )
    work_root.mkdir(parents=True, exist_ok=True)

    budget = BatchBudget(
        max_runs=args.max_runs,
        max_runs_total=args.max_runs_total,
        max_turns=args.max_turns,
        max_turns_total=args.max_turns_total,
        max_wall_s=args.max_wall_s,
        max_wall_s_total=args.max_wall_s_total,
        max_budget_usd=args.max_budget_usd,
        max_budget_usd_total=args.max_budget_usd_total,
        max_stale_runs=args.max_stale_runs,
    )

    try:
        tools, indexes, sancov = load_instrumented(
            bin_dir=bin_dir,
            work_dir=work_root / "symcov",
            runner=runner,
            steps=steps,
        )

        outcomes: list[LineOutcome] = []
        pending: list[tuple[int, TargetLine]] = []
        for i, target in enumerate(targets):
            with steps.step("precheck_instrumented", str(target)):
                instrumenting = tools_instrumenting_target(indexes, target)
            logger.info("instrumenting tools for %s: %s", target, instrumenting)
            if not instrumenting:
                line_dir = line_out_dir(out_dir, i, target) if multi else out_dir
                write_outputs(
                    line_dir,
                    target=target,
                    status="not_instrumented",
                    result=None,
                    history=[],
                    extra={
                        "reason": "target has no points in provided symcov files",
                        "steps": steps.as_dicts(),
                    },
                )
                print(f"not_instrumented: {target}", file=sys.stderr)
                outcomes.append(
                    LineOutcome(
                        target=target,
                        index=i,
                        status="not_instrumented",
                        out_dir=line_dir,
                        reason="target has no points in provided symcov files",
                    )
                )
            else:
                pending.append((i, target))

        if not pending:
            if multi:
                write_summary(out_dir, outcomes)
            raise SystemExit(2 if outcomes else 1)

        if not args.skip_gateway_ping:
            with steps.step("gateway_ping", "expect pong"):
                try:
                    asyncio.run(
                        ping_gateway(
                            api_key=api_key, base_url=base_url, user_ntid=user_ntid
                        )
                    )
                except Exception as exc:
                    logger.error("gateway ping failed: %s", exc)
                    for index, target in pending:
                        line_dir = (
                            line_out_dir(out_dir, index, target) if multi else out_dir
                        )
                        write_outputs(
                            line_dir,
                            target=target,
                            status="gave_up",
                            result=None,
                            history=[],
                            extra={
                                "reason": f"gateway_ping_failed: {exc}",
                                "steps": steps.as_dicts(),
                            },
                        )
                        outcomes.append(
                            LineOutcome(
                                target=target,
                                index=index,
                                status="gave_up",
                                out_dir=line_dir,
                                reason=f"gateway_ping_failed: {exc}",
                            )
                        )
                    pending.clear()
                    if multi:
                        write_summary(out_dir, outcomes)
                        raise SystemExit(multi_line_exit_code(outcomes)) from exc
                    print(f"gateway ping failed: {exc}", file=sys.stderr)
                    raise SystemExit(1) from exc
            logger.info("gateway ping ok")

        corpus: list[RunResult] = []
        run_counter_base = 0

        while pending:
            limits = budget.session_limits()
            if limits is None:
                reason = budget.totals_exhausted() or "batch budget exhausted"
                logger.info("skipping remaining targets: %s", reason)
                for index, target in pending:
                    line_dir = line_out_dir(out_dir, index, target) if multi else out_dir
                    write_outputs(
                        line_dir,
                        target=target,
                        status="skipped_budget",
                        result=None,
                        history=[],
                        extra={"reason": reason, "steps": steps.as_dicts()},
                    )
                    outcomes.append(
                        LineOutcome(
                            target=target,
                            index=index,
                            status="skipped_budget",
                            out_dir=line_dir,
                            reason=reason,
                        )
                    )
                pending.clear()
                break

            index, target = pending.pop(0)
            line_dir = line_out_dir(out_dir, index, target) if multi else out_dir
            if multi:
                _clear_previous_outputs(line_dir)
            line_dir.mkdir(parents=True, exist_ok=True)

            # Fresh oracle per session so measure_hits nearby window is for this target.
            # Keep run dirs under a shared tree; counter continues via work_root subdirs.
            session_work = work_root / "runs" / f"line_{index:03d}"
            oracle = CoverageOracle(
                tools=tools,
                indexes=indexes,
                sancov_bin=sancov,
                target=target,
                work_root=session_work,
                timeout_s=args.timeout_s,
                runner=runner,
            )
            oracle.set_run_counter(run_counter_base)

            state = make_state(
                oracle=oracle,
                target=target,
                llvm_src=llvm_src,
                diff_path=diff_path,
                out_dir=line_dir,
                model=args.model,
                effort=args.effort,
                thinking_tokens=args.thinking_tokens,
                **limits,
            )
            state.steps = steps
            state = asyncio.run(
                run_session(
                    state=state,
                    api_key=api_key,
                    base_url=base_url,
                    user_ntid=user_ntid,
                    max_turns=limits["max_turns"],
                )
            )
            budget.note_session(
                runs=len(state.runs),
                turns=state.sdk_turns,
                cost_usd=state.total_cost_usd,
            )
            corpus.extend(state.runs)
            run_counter_base = oracle.run_counter

            status, accepted = _finish_session_outputs(
                state=state,
                target=target,
                out_dir=line_dir,
                tools=tools,
                indexes=indexes,
                sancov=sancov,
                timeout_s=args.timeout_s,
                runner=runner,
                steps=steps,
            )
            covering_run = None
            if accepted is not None:
                try:
                    covering_run = corpus.index(accepted) + 1
                except ValueError:
                    covering_run = None
            outcomes.append(
                LineOutcome(
                    target=target,
                    index=index,
                    status=status,
                    covered_by="session" if status == "covered" else None,
                    out_dir=line_dir,
                    reason=None if status == "covered" else state.give_up_reason,
                    covering_run=covering_run,
                    covering_tool=accepted.tool if accepted is not None else None,
                )
            )

            credited = credit_pending_lines(
                pending=pending,
                runs=corpus,
                indexes=indexes,
                out_dir=out_dir,
                prefer=accepted,
                multi=multi,
            )
            for outcome in credited:
                logger.info(
                    "collateral cover %s via run %s (%s)",
                    outcome.target,
                    outcome.covering_run,
                    outcome.covering_tool,
                )
                print(
                    f"covered (collateral): {outcome.target} "
                    f"via run {outcome.covering_run}",
                )
            outcomes.extend(credited)

        outcomes.sort(key=lambda o: o.index)

        if multi:
            write_summary(out_dir, outcomes)
            code = multi_line_exit_code(outcomes)
            covered_n = sum(1 for o in outcomes if o.status == "covered")
            print(
                f"summary: {covered_n}/{len(outcomes)} covered "
                f"(exit {code}); wrote {out_dir / 'summary.json'}"
            )
            raise SystemExit(code)

        # Single-target exit codes (unchanged).
        assert len(outcomes) == 1
        status = outcomes[0].status
        if status == "covered":
            raise SystemExit(0)
        if status == "not_instrumented":
            raise SystemExit(2)
        if status == "likely_unreachable":
            raise SystemExit(3)
        raise SystemExit(1)
    finally:
        if work_ctx is not None:
            work_ctx.cleanup()


if __name__ == "__main__":
    main()
