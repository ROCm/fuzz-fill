# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""CLI entry point for usher-test."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fill_line_agent.context_json import read_context_json
from fill_line_agent.instrumented import load_instrumented
from fill_line_agent.lit_file import (
    filecheckify_coverage_run,
    parse_all_runs,
    pass_hint_from_test,
)
from fill_line_agent.oracle import CoverageOracle, TargetLine
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
from fill_line_agent.responses import ResponseLog
from fill_line_agent.session import run_session
from fill_line_agent.session_state import SessionState
from fill_line_agent.steps import StepTracker
from fill_line_agent.tool_runner import ToolRunner
from fill_line_agent.usher_session import (
    build_usher_system_prompt,
    build_usher_user_prompt,
    usher_fallback_picker,
)
from fill_line_agent.usher_state import DeclaredStyle, StandaloneProposal, UsherState
from fill_line_agent.usher_tools import (
    build_usher_tools,
    ensure_usher_comment,
    list_pr_tests_info,
    proposal_matches_pr_style,
    rank_candidate_tests,
    run_update_checks_on_standalone,
    validate_standalone,
)
from fuzz_fill.log import (
    add_log_level_argument,
    add_log_to_file_argument,
    configure_logging,
    get_logger,
    resolve_log_file,
)

logger = get_logger("fill_line_agent.usher")


@dataclass
class CoveringCase:
    """One unique covering fill-line test (possibly multiple targets)."""

    case_id: str
    test_text: str
    test_fmt: str
    targets: list[TargetLine]
    source_dirs: list[Path]
    result_payloads: list[dict[str, Any]]


def resolve_filecheck(explicit: Path | None) -> Path:
    if explicit is not None:
        path = explicit.expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"FileCheck not found: {path}")
        return path
    found = shutil.which("FileCheck")
    if not found:
        raise SystemExit(
            "FileCheck not found on PATH; pass --filecheck /path/to/FileCheck"
        )
    return Path(found).resolve()


def _load_result(dir_path: Path) -> dict[str, Any] | None:
    path = dir_path / "result.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_test_text(dir_path: Path, payload: dict[str, Any]) -> tuple[str, str] | None:
    name = payload.get("test")
    candidates: list[Path] = []
    if isinstance(name, str):
        candidates.append(dir_path / name)
    candidates.extend([dir_path / "test.ll", dir_path / "test.mir"])
    for path in candidates:
        if path.is_file():
            fmt = path.suffix.lstrip(".")
            return path.read_text(encoding="utf-8"), fmt
    return None


def discover_covering_cases(from_dir: Path) -> list[CoveringCase]:
    """Walk fill-line out dir; return deduped covering cases."""
    dirs: list[Path] = []
    lines_root = from_dir / "lines"
    if lines_root.is_dir():
        dirs.extend(sorted(p for p in lines_root.iterdir() if p.is_dir()))
    else:
        dirs.append(from_dir)

    by_fp: dict[str, CoveringCase] = {}
    order: list[str] = []

    for d in dirs:
        payload = _load_result(d)
        if not payload or payload.get("status") != "covered":
            continue
        loaded = _load_test_text(d, payload)
        if loaded is None:
            continue
        text, fmt = loaded
        target = TargetLine.parse(str(payload["target"]))
        fp = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if fp not in by_fp:
            by_fp[fp] = CoveringCase(
                case_id=fp[:12],
                test_text=text,
                test_fmt=fmt,
                targets=[target],
                source_dirs=[d],
                result_payloads=[payload],
            )
            order.append(fp)
        else:
            case = by_fp[fp]
            if target not in case.targets:
                case.targets.append(target)
            case.source_dirs.append(d)
            case.result_payloads.append(payload)
    return [by_fp[fp] for fp in order]


def suggest_new_file_path(target: TargetLine, fmt: str) -> str:
    """Conventional new-file location mirroring the source path."""
    rel = target.rel_path.replace("\\", "/")
    parts = rel.split("/")
    if "lib" in parts:
        i = parts.index("lib")
        area = "/".join(parts[i + 1 : -1]) if i + 1 < len(parts) else "Misc"
        stem = Path(parts[-1]).stem
        prefix = parts[0] if parts[0] in ("llvm", "clang", "mlir") else "llvm"
        return f"{prefix}/test/{area}/usher_{stem}_{target.line}.{fmt}"
    return f"llvm/test/usher/usher_{Path(rel).stem}_{target.line}.{fmt}"


def pick_suggested_host(
    *,
    state: UsherState,
    target: TargetLine,
    fmt: str,
    pass_hint: str | None = None,
    prefer_hosts: list[str] | None = None,
    style: DeclaredStyle | None = None,
) -> str:
    """Prefer agent host (same fmt), else ranked same-suffix candidate, else new file."""
    suffix = f".{fmt}"
    for host in prefer_hosts or []:
        h = host.strip().replace("\\", "/")
        if h.endswith(suffix):
            return h

    search_dirs: list[str] | None = None
    active = style
    if active is None and hasattr(state, "active_style"):
        active = state.active_style()
    pr_paths = list(getattr(state, "pr_test_paths", []) or [])
    if active is not None:
        search_dirs = [str(Path(e).parent) for e in active.evidence]
    elif pr_paths:
        search_dirs = [str(Path(p).parent) for p in pr_paths]

    # For .ll proposals with a declared style, do not steer by MIR pass names.
    hint = pass_hint
    if active is not None and active.suffix == "ll" and fmt == "ll":
        hint = None

    rows = rank_candidate_tests(
        llvm_src=state.llvm_src,
        diff_path=state.diff_path,
        pass_hint=hint,
        limit=40,
        style=active if fmt == (active.suffix if active else None) else None,
        search_dirs=search_dirs,
    )
    matching = [r for r in rows if str(r["path"]).endswith(suffix)]
    if matching:
        return str(matching[0]["path"])
    return suggest_new_file_path(target, fmt)


def _style_mismatch_detail(state: UsherState, target: TargetLine) -> str:
    active = state.active_style()
    template = active.run_template if active else "PR-style"
    n = state.style_conforming_runs()
    unlocked = state.fallback_unlocked_by() or "fallback"
    return (
        f"No `{template}` test covered {target} after {n} style-conforming "
        f"run(s) ({unlocked}); this test uses a different format/shape. "
        "Ask the author whether the path is reachable in the PR's style."
    )


def harness_standalone_fallback(
    *,
    state: UsherState,
    case: CoveringCase,
) -> tuple[str, str, bool, bool] | None:
    """Build a standalone file + suggested_host without an accepted proposal.

    Returns ``(suggested_host, text, covered_ok, style_mismatch)`` or None if unusable.
    """
    target = case.targets[0]
    prefer = [
        p.suggested_host
        for p in reversed(state.proposals)
        if p.suggested_host
    ]
    # Fallback always starts from the fill-line case format.
    fmt = case.test_fmt
    host = pick_suggested_host(
        state=state,
        target=target,
        fmt=fmt,
        pass_hint=pass_hint_from_test(case.test_text),
        prefer_hosts=prefer,
    )
    text = filecheckify_coverage_run(case.test_text)
    upd = run_update_checks_on_standalone(state, test_text=text, fmt=fmt)
    if upd.get("ok") and isinstance(upd.get("test_text"), str):
        text = upd["test_text"]
    else:
        logger.info(
            "harness annotate soft-failed: %s",
            upd.get("error") or upd.get("stderr_tail"),
        )

    style_mismatch = False
    if state.declared_styles:
        style_mismatch = not proposal_matches_pr_style(state, text, fmt)

    text = ensure_usher_comment(
        text,
        suggested_host=host,
        note="harness fallback; paste manually",
        fmt=fmt,
        style_mismatch=style_mismatch,
        style_mismatch_detail=(
            _style_mismatch_detail(state, target) if style_mismatch else None
        ),
    )
    validation = validate_standalone(state, test_text=text, fmt=fmt)
    covered = bool(validation.get("covered"))
    if not covered:
        logger.warning(
            "harness standalone fallback does not cover target: %s",
            validation.get("coverage"),
        )
        return host, text, False, style_mismatch
    return host, text, True, style_mismatch


def write_case_outputs(
    *,
    case_dir: Path,
    status: str,
    standalone: str,
    fmt: str,
    suggested_host: str | None,
    run_lines: list[str],
    harness_recheck: bool | None,
    extra: dict[str, Any] | None = None,
) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    test_name = f"test.{fmt}"
    (case_dir / test_name).write_text(standalone, encoding="utf-8")
    payload: dict[str, Any] = {
        "status": status,
        "suggested_host": suggested_host,
        "destination": suggested_host,
        "run_lines": run_lines,
        "harness_recheck": harness_recheck,
        "test": test_name,
        "format": fmt,
    }
    if extra:
        payload.update(extra)
    (case_dir / "result.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def recheck_proposal_coverage(
    state: UsherState, proposal: StandaloneProposal, fmt: str | None = None
) -> bool:
    use_fmt = fmt or proposal.fmt or "ll"
    validation = validate_standalone(
        state, test_text=proposal.test_text, fmt=use_fmt
    )
    return bool(validation.get("covered") and validation.get("filecheck_ok"))


def _style_result_extra(
    state: UsherState, *, proposal: StandaloneProposal | None, status: str
) -> dict[str, Any]:
    active = state.active_style()
    proposals = [
        {
            "proposal": p.proposal_id,
            "fmt": p.fmt,
            "covered": p.covered,
            "filecheck_ok": p.filecheck_ok,
            "style_ok": p.style_ok,
            "pr_style_ok": p.pr_style_ok,
            "style_reasons": list(p.style_reasons),
        }
        for p in state.proposals
    ]
    discovery_extra: dict[str, Any] = {}
    if state.discovery is not None:
        disc = state.discovery
        discovery_extra = {
            **disc.quota_dict(),
            "runs": len(disc.runs),
            "covered_runs": disc.covered_run_numbers(),
            "analysis_verdict": (
                (disc.analysis or {}).get("verdict") if disc.analysis else None
            ),
            "style_conforming_runs": state.style_conforming_runs(),
            "run_style_ok": dict(state.run_style_ok),
        }
    extra: dict[str, Any] = {
        "declared_styles": [s.to_json() for s in state.declared_styles],
        "declared_style": active.to_json() if active else None,
        "proposals": proposals,
        "style_reason": state.accepted_style_reason
        or (proposal.style_reason if proposal else None),
        "discovery": discovery_extra,
        "fallback_unlocked_by": state.fallback_unlocked_by(),
    }
    if proposal is not None:
        extra["style"] = {
            "match": proposal.pr_style_ok,
            "style_ok": proposal.style_ok,
            "reasons": list(proposal.style_reasons),
            "fmt": proposal.fmt,
        }
    if status == "style_mismatch":
        extra["reachability"] = "not_shown_in_pr_style"
    return extra


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Polish fill-line covering tests into standalone lit files with a "
            "suggested host path for a human to paste into llvm-project."
        )
    )
    parser.add_argument(
        "--from",
        dest="from_dir",
        type=Path,
        required=True,
        help="fill-line out dir (result.json + test.ll + optional context.json)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: <from>/usher/)",
    )
    parser.add_argument("--llvm-src", type=Path, default=None)
    parser.add_argument("--diff", type=Path, default=None)
    parser.add_argument("--instrumented-bin-dir", type=Path, default=None)
    parser.add_argument(
        "--filecheck",
        type=Path,
        default=None,
        help="Path to FileCheck (default: FileCheck on PATH)",
    )
    add_api_key_arguments(parser)
    add_base_url_arguments(parser)
    add_user_ntid_arguments(parser)
    parser.add_argument(
        "--max-placements",
        type=int,
        default=10,
        help="Max finalize_standalone + annotate_checks calls (default 10)",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=40,
        help="Discovery run_candidate budget in the declared PR style (default 40)",
    )
    parser.add_argument(
        "--max-stale-runs",
        type=int,
        default=0,
        help="Stop discovery after this many consecutive non-improving runs (0=off)",
    )
    parser.add_argument("--max-turns", type=int, default=200)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument("--max-wall-s", type=float, default=0.0)
    parser.add_argument("--max-budget-usd", type=float, default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--effort",
        choices=("low", "medium", "high", "xhigh", "max"),
        default=None,
    )
    parser.add_argument("--thinking-tokens", type=int, default=None)
    parser.add_argument(
        "--tools-runner",
        choices=("host", "docker"),
        default=None,
    )
    parser.add_argument("--tools-image", default=None)
    parser.add_argument("--work-dir", type=Path, default=None)
    parser.add_argument("--skip-gateway-ping", action="store_true")
    add_log_level_argument(parser)
    add_log_to_file_argument(parser)
    return parser


def _resolve_paths(
    args: argparse.Namespace,
) -> tuple[Path, Path, Path, Path, Path]:
    from_dir = args.from_dir.expanduser().resolve()
    if not from_dir.is_dir():
        raise SystemExit(f"--from not a directory: {from_dir}")

    ctx: dict[str, Any] = {}
    ctx_path = from_dir / "context.json"
    if ctx_path.is_file():
        try:
            ctx = read_context_json(ctx_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("ignoring context.json: %s", exc)

    def pick(cli: Path | None, key: str) -> Path:
        if cli is not None:
            return cli.expanduser().resolve()
        if key in ctx and ctx[key]:
            return Path(str(ctx[key])).expanduser().resolve()
        raise SystemExit(
            f"missing {key}: pass CLI flag or provide it in {ctx_path}"
        )

    llvm_src = pick(args.llvm_src, "llvm_src")
    diff_path = pick(args.diff, "diff")
    bin_dir = pick(args.instrumented_bin_dir, "instrumented_bin_dir")

    if args.tools_runner is None and ctx.get("tools_runner"):
        args.tools_runner = str(ctx["tools_runner"])
    if args.tools_image is None and ctx.get("tools_image"):
        args.tools_image = str(ctx["tools_image"])

    out_dir = (
        args.out_dir.expanduser().resolve()
        if args.out_dir is not None
        else (from_dir / "usher").resolve()
    )
    return from_dir, out_dir, llvm_src, diff_path, bin_dir


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.thinking_tokens is not None and 0 < args.thinking_tokens < 1024:
        parser.error("--thinking-tokens must be 0 (disabled) or at least 1024")

    from_dir, out_dir, llvm_src, diff_path, bin_dir = _resolve_paths(args)
    out_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(
        args.log_level,
        log_file=resolve_log_file(out_dir, args.log_to_file),
    )
    steps = StepTracker()

    if not llvm_src.is_dir():
        raise SystemExit(f"llvm-src not found: {llvm_src}")
    if not diff_path.is_file():
        raise SystemExit(f"diff not found: {diff_path}")

    filecheck = resolve_filecheck(args.filecheck)
    api_key = resolve_api_key(api_key=args.api_key, key_file=args.key_file)
    base_url = resolve_base_url(base_url=args.base_url, base_url_file=args.base_url_file)
    user_ntid = resolve_user_ntid(user_ntid=args.user_ntid)
    install_secret_redaction(api_key, base_url, user_ntid)

    runner = ToolRunner.from_cli(mode=args.tools_runner, image=args.tools_image)
    cases = discover_covering_cases(from_dir)
    if not cases:
        raise SystemExit(f"no covered fill-line results under {from_dir}")

    work_ctx = (
        tempfile.TemporaryDirectory(prefix="usher-test-")
        if args.work_dir is None
        else None
    )
    work_root = (
        Path(work_ctx.name) if work_ctx is not None else args.work_dir.resolve()
    )
    work_root.mkdir(parents=True, exist_ok=True)

    case_summaries: list[dict[str, Any]] = []
    batch_ok = True

    try:
        tools, indexes, sancov, resource_include = load_instrumented(
            bin_dir=bin_dir,
            work_dir=work_root / "symcov",
            runner=runner,
            steps=steps,
        )
        if not shutil.which("python3"):
            raise SystemExit("python3 required for update_*_test_checks.py")

        if not args.skip_gateway_ping:
            with steps.step("gateway_ping"):
                asyncio.run(
                    ping_gateway(
                        api_key=api_key, base_url=base_url, user_ntid=user_ntid
                    )
                )

        for i, case in enumerate(cases):
            case_dir = out_dir / "cases" / f"{i:03d}-{case.case_id}"
            target = case.targets[0]
            logger.info(
                "usher case %s targets=%s",
                case.case_id,
                [str(t) for t in case.targets],
            )
            oracle = CoverageOracle(
                tools=tools,
                indexes=indexes,
                sancov_bin=sancov,
                target=target,
                work_root=work_root / f"case_{i:03d}",
                timeout_s=args.timeout_s,
                runner=runner,
                resource_include=resource_include,
            )
            allowed = oracle.tools_instrumenting()
            if not allowed:
                host = suggest_new_file_path(target, case.test_fmt)
                standalone = ensure_usher_comment(
                    case.test_text,
                    suggested_host=host,
                    note="target not instrumented",
                    fmt=case.test_fmt,
                )
                write_case_outputs(
                    case_dir=case_dir,
                    status="gave_up",
                    standalone=standalone,
                    fmt=case.test_fmt,
                    suggested_host=host,
                    run_lines=[],
                    harness_recheck=False,
                    extra={
                        "reason": "target not instrumented",
                        "targets": [str(t) for t in case.targets],
                    },
                )
                case_summaries.append(
                    {
                        "case": case.case_id,
                        "status": "gave_up",
                        "suggested_host": host,
                    }
                )
                batch_ok = False
                continue

            # Pre-load PR test paths so declare_test_style / ranking can use them.
            diff_text = (
                diff_path.read_text(encoding="utf-8", errors="replace")
                if diff_path.is_file()
                else ""
            )
            pr_info = list_pr_tests_info(
                diff_text=diff_text, target_rel=target.rel_path
            )

            discovery_dir = case_dir / "discovery"
            discovery_dir.mkdir(parents=True, exist_ok=True)
            discovery = SessionState(
                oracle=oracle,
                target=target,
                llvm_src=llvm_src,
                diff_path=diff_path,
                max_runs=max(0, int(args.max_runs)),
                max_stale_runs=max(0, int(args.max_stale_runs)),
                max_turns=args.max_turns,
                allowed_tools=allowed,
                max_wall_s=args.max_wall_s,
                max_budget_usd=args.max_budget_usd,
                out_dir=discovery_dir,
                model=args.model,
                effort=args.effort,
                thinking_tokens=args.thinking_tokens,
                responses=ResponseLog(discovery_dir),
                steps=steps,
            )
            state = UsherState(
                oracle=oracle,
                target=target,
                llvm_src=llvm_src,
                diff_path=diff_path,
                fill_test_text=case.test_text,
                fill_test_fmt=case.test_fmt,
                filecheck_bin=filecheck,
                max_placements=args.max_placements,
                max_turns=args.max_turns,
                allowed_tools=allowed,
                steps=steps,
                out_dir=case_dir,
                max_wall_s=args.max_wall_s,
                max_budget_usd=args.max_budget_usd,
                model=args.model,
                effort=args.effort,
                thinking_tokens=args.thinking_tokens,
                max_runs=max(0, int(args.max_runs)),
                max_stale_runs=max(0, int(args.max_stale_runs)),
                discovery=discovery,
                pr_test_paths=[t["path"] for t in pr_info["tests"]],
                mapped_test_dir=pr_info.get("mapped_test_dir"),
            )

            system_prompt = build_usher_system_prompt(
                target=target,
                llvm_src=llvm_src,
                fill_test_text=case.test_text,
                fill_test_fmt=case.test_fmt,
                allowed_tools=list(allowed),
                max_placements=args.max_placements,
                max_runs=state.max_runs,
                max_stale_runs=state.max_stale_runs,
                diff_path=diff_path,
                function_range=oracle.function_line_range(target),
            )
            user_prompt = build_usher_user_prompt(state)

            asyncio.run(
                run_session(
                    state=state,
                    api_key=api_key,
                    base_url=base_url,
                    user_ntid=user_ntid,
                    max_turns=args.max_turns,
                    build_tools=build_usher_tools,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    mcp_server_name="usher",
                    fallback_picker=usher_fallback_picker,
                )
            )

            status = "gave_up"
            suggested_host: str | None = None
            proposal = state.accepted_proposal
            harness_ok: bool | None = None
            run_lines: list[str] = []
            standalone = ""
            out_fmt = case.test_fmt

            if state.accepted and proposal is not None:
                harness_ok = recheck_proposal_coverage(state, proposal)
                if harness_ok:
                    out_fmt = proposal.fmt or case.test_fmt
                    suggested_host = proposal.suggested_host
                    standalone = proposal.test_text
                    run_lines = [r.raw for r in parse_all_runs(standalone)]
                    from fill_line_agent.usher_tools import proposal_shape_matches

                    if (
                        proposal.pr_style_ok
                        or not state.declared_styles
                        or proposal_shape_matches(
                            state, standalone, out_fmt
                        )
                    ):
                        # Shape match alone is enough for moved-code host choice.
                        status = "standalone"
                    else:
                        status = "style_mismatch"
                        standalone = ensure_usher_comment(
                            standalone,
                            suggested_host=suggested_host or "",
                            note=proposal.note,
                            fmt=out_fmt,
                            style_mismatch=True,
                            style_mismatch_detail=_style_mismatch_detail(
                                state, target
                            ),
                        )
                        proposal.test_text = standalone
                else:
                    proposal = None
                    logger.error("harness re-check failed for proposal")

            if status == "gave_up":
                fb = harness_standalone_fallback(state=state, case=case)
                if fb is not None:
                    host, text, covered_ok, style_mismatch = fb
                    suggested_host = host
                    standalone = text
                    out_fmt = case.test_fmt
                    run_lines = [r.raw for r in parse_all_runs(text)]
                    if covered_ok:
                        status = (
                            "style_mismatch" if style_mismatch else "standalone"
                        )
                        harness_ok = True
                    else:
                        status = "gave_up"
                        harness_ok = False
                else:
                    suggested_host = suggest_new_file_path(target, case.test_fmt)
                    standalone = ensure_usher_comment(
                        case.test_text,
                        suggested_host=suggested_host,
                        note="gave up; paste manually",
                        fmt=case.test_fmt,
                    )
                    out_fmt = case.test_fmt
                    harness_ok = False
                    status = "gave_up"

            write_case_outputs(
                case_dir=case_dir,
                status=status,
                standalone=standalone,
                fmt=out_fmt,
                suggested_host=suggested_host,
                run_lines=run_lines,
                harness_recheck=harness_ok,
                extra={
                    "targets": [str(t) for t in case.targets],
                    "accepted_by": state.accepted_by,
                    "give_up_reason": state.give_up_reason,
                    "note": (
                        state.accepted_proposal.note
                        if state.accepted_proposal is not None
                        else None
                    ),
                    "quota": state.quota_dict(),
                    "stats": state.stats_dict(),
                    "usage": state.usage_dict(),
                    **_style_result_extra(
                        state, proposal=state.accepted_proposal, status=status
                    ),
                },
            )
            case_summaries.append(
                {
                    "case": case.case_id,
                    "status": status,
                    "suggested_host": suggested_host,
                    "targets": [str(t) for t in case.targets],
                    "format": out_fmt,
                }
            )
            if status in ("gave_up", "style_mismatch"):
                batch_ok = False
            print(f"{status}: case {case.case_id} -> {suggested_host}")

        summary = {
            "cases": case_summaries,
        }
        (out_dir / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
    finally:
        if work_ctx is not None:
            work_ctx.cleanup()

    if not batch_ok:
        raise SystemExit(1)
    print(f"usher-test done: wrote {out_dir}")


if __name__ == "__main__":
    main()
