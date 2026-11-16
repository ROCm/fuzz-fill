# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Usher-owned MCP tools for standalone annotated lit tests (no host edits)."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from fill_line_agent.args_policy import validate_argv
from fill_line_agent.lit_file import (
    ParsedRun,
    ToolName,
    autogen_script,
    flags_from_argv,
    function_name_from_ir,
    parse_all_runs,
    run_shape,
    split_ll_functions,
    strip_header_comments_keep_run,
    triple_from_argv,
)
from fill_line_agent.oracle import InputFormat, stream_page
from fill_line_agent.source_tools import source_tool_specs
from fill_line_agent.tool_common import build_mcp_server, error_payload, text_payload
from fill_line_agent.tools import fill_tool_specs, make_fill_handlers
from fill_line_agent.usher_state import (
    DeclaredStyle,
    StandaloneProposal,
    UsherState,
    parse_run_template,
)
from fuzz_fill.log import get_logger

logger = get_logger("fill_line_agent.usher_tools")

TEST_SUFFIXES = (".ll", ".mir")
CANDIDATE_LIMIT = 40
CAPTURE_PAGE_LINES = 200
ADDED_RUNS_LIMIT = 6
SUPPORTED_UPDATE_SCRIPTS = frozenset(
    {
        "update_test_checks.py",
        "update_llc_test_checks.py",
        "update_mir_test_checks.py",
    }
)
_SPIRV_HINT = re.compile(r"spirv(32|64)?", re.IGNORECASE)
_RUN_IN_LINE = re.compile(r"^[+#;\s]*RUN:\s*(.*)$")


def _summarize(name: str, args: dict[str, Any]) -> str:
    if name == "list_candidate_tests":
        return f"pass_hint={args.get('pass_hint')!r}"
    if name == "list_pr_tests":
        return "pr tests"
    if name == "declare_test_style":
        return f"suffix={args.get('suffix')!r} evidence={args.get('evidence')!r}"
    if name == "finalize_standalone":
        return (
            f"host={args.get('suggested_host')!r} "
            f"run={args.get('run')!r}"
        )
    if name == "annotate_checks":
        return f"script={args.get('script')!r}"
    if name == "get_output":
        return f"run={args.get('run')} offset={args.get('offset')}"
    if name == "dump_ir":
        return f"tool={args.get('tool')} args={args.get('args')!r}"
    if name == "run_candidate":
        fmt = args.get("format", "ll")
        argv = args.get("args") or []
        inp = str(args.get("input") or "")
        return (
            f"format={fmt} testing={args.get('testing')!r} "
            f"args={argv!r} input_bytes={len(inp)}"
        )
    if name == "select_tool":
        return f"tool={args.get('tool')!r}"
    if name == "record_analysis":
        return (
            f"verdict={args.get('verdict')!r} "
            f"conditions={len(args.get('conditions') or [])}"
        )
    if name == "show_streams":
        return f"stream={args.get('stream')} offset={args.get('offset')}"
    if name == "accept":
        return f"proposal={args.get('proposal')}"
    if name == "give_up":
        return f"reason={args.get('reason')!r}"
    return ""


def _is_lit_test_path(rel: str) -> bool:
    lower = rel.replace("\\", "/")
    if not any(lower.endswith(s) for s in TEST_SUFFIXES):
        return False
    parts = lower.split("/")
    return "test" in parts


def _diff_touched_tests(diff_text: str) -> list[str]:
    return [e["path"] for e in touched_test_entries(diff_text)]


def mapped_test_dir_for_target(rel_path: str) -> str | None:
    """Map a source path under lib/ to a conventional llvm/test directory."""
    parts = rel_path.replace("\\", "/").split("/")
    if "lib" not in parts:
        return None
    i = parts.index("lib")
    after = parts[i + 1 : -1]
    if not after:
        return None
    prefix = parts[0] if parts[0] in ("llvm", "clang", "mlir") else "llvm"
    if after[0] == "Target" and len(after) >= 2:
        return f"{prefix}/test/CodeGen/{after[1]}"
    return f"{prefix}/test/{'/'.join(after)}"


def touched_test_entries(diff_text: str) -> list[dict[str, Any]]:
    """PR-touched lit tests with added/modified status and added RUN excerpts."""
    lines = diff_text.splitlines()
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("diff --git "):
            i += 1
            continue
        parts = line.split()
        if len(parts) < 4:
            i += 1
            continue
        b = parts[3]
        if b.startswith("b/"):
            b = b[2:]
        b = b.replace("\\", "/")
        i += 1
        if not _is_lit_test_path(b) or b in seen:
            continue
        status = "modified"
        added_runs: list[str] = []
        while i < len(lines) and not lines[i].startswith("diff --git "):
            cur = lines[i]
            if cur.startswith("new file mode"):
                status = "added"
            elif cur.startswith("deleted file mode"):
                status = "deleted"
            elif cur.startswith("+") and not cur.startswith("+++"):
                body = cur[1:]
                if "RUN:" in body:
                    m = _RUN_IN_LINE.match(body.strip())
                    if m:
                        added_runs.append(f"RUN: {m.group(1).strip()}")
                    else:
                        added_runs.append(body.strip())
                    if len(added_runs) >= ADDED_RUNS_LIMIT:
                        # Keep scanning for status / next file boundary.
                        pass
            i += 1
        if status == "deleted":
            continue
        seen.add(b)
        entries.append(
            {
                "path": b,
                "status": status,
                "added_runs": added_runs[:ADDED_RUNS_LIMIT],
            }
        )
    return entries


def list_pr_tests_info(
    *,
    diff_text: str,
    target_rel: str,
) -> dict[str, Any]:
    """Raw facts about PR-touched tests (no style conclusions)."""
    tests = touched_test_entries(diff_text)
    dirs: list[str] = []
    seen_dirs: set[str] = set()
    for t in tests:
        d = str(Path(t["path"]).parent).replace("\\", "/")
        if d not in seen_dirs:
            seen_dirs.add(d)
            dirs.append(d)
    mapped = mapped_test_dir_for_target(target_rel)
    return {
        "tests": tests,
        "dirs": dirs,
        "mapped_test_dir": mapped,
        "count": len(tests),
    }


def _function_names(text: str) -> list[str]:
    if "@" in text and "define " in text:
        return [f.name for f in split_ll_functions(text)]
    names: list[str] = []
    for m in re.finditer(r"^name:\s*([A-Za-z0-9_.$+-]+)", text, re.MULTILINE):
        names.append(m.group(1))
    return names


def looks_like_spirv(text: str, suggested_host: str = "") -> bool:
    """Heuristic: SPIRV triple/path — update scripts often fail here."""
    rel = suggested_host.replace("\\", "/")
    if re.search(r"(^|/)SPIRV(/|$)", rel) or "/spirv/" in rel.lower():
        return True
    return bool(_SPIRV_HINT.search(text))


def rank_candidate_tests(
    *,
    llvm_src: Path,
    diff_path: Path,
    pass_hint: str | None = None,
    limit: int = CANDIDATE_LIMIT,
    style: DeclaredStyle | None = None,
    search_dirs: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return candidate lit files with supported RUN lines (style / PR-touched first)."""
    diff_text = (
        diff_path.read_text(encoding="utf-8", errors="replace")
        if diff_path.is_file()
        else ""
    )
    ordered: list[str] = []
    seen: set[str] = set()
    for rel in _diff_touched_tests(diff_text):
        if rel not in seen:
            seen.add(rel)
            ordered.append(rel)

    evidence_dirs: list[str] = []
    if style is not None:
        for ev in style.evidence:
            d = str(Path(ev.replace("\\", "/")).parent)
            if d not in evidence_dirs:
                evidence_dirs.append(d)
    if search_dirs:
        for d in search_dirs:
            dn = d.replace("\\", "/")
            if dn not in evidence_dirs:
                evidence_dirs.append(dn)

    hint = (pass_hint or "").strip()
    # Prefer searching evidence / PR dirs when we have a declared .ll style.
    scoped_search = bool(style and style.suffix == "ll" and evidence_dirs)
    root = llvm_src.resolve()

    def _scan_path(path: Path) -> None:
        nonlocal ordered
        if not path.is_file():
            return
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            return
        if not _is_lit_test_path(rel) or rel in seen:
            return
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        # Whole-tree pass-hint search requires a hit; evidence-dir scan does not.
        if hint and not scoped_search and hint not in text:
            return
        seen.add(rel)
        ordered.append(rel)

    if hint or scoped_search:
        if scoped_search:
            for d in evidence_dirs:
                dir_path = root / d
                if not dir_path.is_dir():
                    continue
                for path in sorted(dir_path.iterdir()):
                    _scan_path(path)
                    if len(ordered) >= limit * 3:
                        break
        else:
            for path in root.rglob("*"):
                _scan_path(path)
                if len(ordered) >= limit * 3:
                    break

    out: list[dict[str, Any]] = []
    touched = set(_diff_touched_tests(diff_text))
    evidence_dir_set = set(evidence_dirs)
    for rel in ordered:
        path = llvm_src / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        runs = parse_all_runs(text)
        if not runs:
            continue
        suffix = Path(rel).suffix.lstrip(".")
        primary = next((r for r in runs if r.filecheck_args is not None), runs[0])
        shape = run_shape(primary, suffix)
        style_match = False
        if style is not None:
            style_match = suffix == style.suffix and shape == style.shape
        parent = str(Path(rel).parent).replace("\\", "/")
        out.append(
            {
                "path": rel,
                "pr_touched": rel in touched,
                "autogen_script": autogen_script(text),
                "functions": _function_names(text)[:40],
                "suffix": suffix,
                "shape": shape,
                "style_match": style_match,
                "same_dir": parent in evidence_dir_set,
                "pass_hint_hit": bool(hint and hint in text),
                "runs": [
                    {
                        "index": r.line_index,
                        "raw": r.raw,
                        "tool": r.tool,
                        "filecheck": r.filecheck_args is not None,
                    }
                    for r in runs
                ],
            }
        )
        if len(out) >= limit * 2:
            break

    out.sort(
        key=lambda r: (
            0 if r.get("style_match") else 1,
            0 if r.get("pr_touched") else 1,
            0 if r.get("same_dir") else 1,
            0 if r.get("pass_hint_hit") else 1,
            str(r["path"]),
        )
    )
    return out[:limit]


def _ir_body_for_oracle(edited_text: str, fmt: str) -> str:
    _header, body = strip_header_comments_keep_run(edited_text)
    if body.strip():
        return body
    return edited_text


def run_coverage_for_parsed(
    state: UsherState,
    parsed: ParsedRun,
    edited_text: str,
    fmt: InputFormat,
) -> dict[str, Any]:
    """Run instrumented tool half; report target coverage (no FileCheck)."""
    body = _ir_body_for_oracle(edited_text, fmt)
    result = state.oracle.run(parsed.tool, list(parsed.argv), body, fmt)
    m = result.measure
    return {
        "tool": result.tool,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "target": {
            "status": m.status if m else "uncovered",
            "n_hit": m.n_hit if m else 0,
            "n_points": m.n_points if m else 0,
        },
        "run_result": result,
    }


def run_filecheck_pipeline(
    *,
    state: UsherState,
    parsed: ParsedRun,
    test_path: Path,
    timeout_s: float | None = None,
) -> dict[str, Any]:
    """Run ``opt|llc … | FileCheck``.

    The instrumented tool half goes through ``ToolRunner`` (host or docker, same
    as coverage). FileCheck stays on the host.
    """
    if parsed.filecheck_args is None:
        return {"ok": False, "error": "RUN line has no FileCheck pipe"}
    tool_bin = state.oracle.tools.get(parsed.tool)
    if tool_bin is None:
        return {"ok": False, "error": f"tool {parsed.tool} not available"}
    timeout = timeout_s if timeout_s is not None else state.oracle.timeout_s
    test_path = test_path.resolve()
    tool_bin = tool_bin.resolve()

    tool_cmd = [str(tool_bin), *parsed.argv]
    # Coverage strips -o from argv; FileCheck needs stdout when the RUN used -o -.
    if getattr(parsed, "output", "default") == "stdout":
        tool_cmd.extend(["-o", "-"])
    stdin_text: str | None = None
    if parsed.stdin_redirect:
        stdin_text = test_path.read_text(encoding="utf-8", errors="replace")
    else:
        tool_cmd.append(str(test_path))

    try:
        tool_proc = state.oracle.runner.run(
            tool_cmd,
            timeout_s=timeout,
            bind_paths=[tool_bin, test_path],
            input=stdin_text,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "tool timed out", "timed_out": True}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}

    tool_out = tool_proc.stdout or ""
    tool_err = tool_proc.stderr or ""
    if parsed.redirect_stderr:
        combined = tool_out + tool_err
    else:
        combined = tool_out

    if tool_proc.returncode != 0:
        return {
            "ok": False,
            "tool_exit": tool_proc.returncode,
            "filecheck_exit": None,
            "stderr_tail": tool_err[-2000:],
            "error": "instrumented tool failed before FileCheck",
        }

    fc_cmd = [str(state.filecheck_bin.resolve()), *parsed.filecheck_args, str(test_path)]
    try:
        fc_proc = subprocess.run(
            fc_cmd,
            input=combined,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "FileCheck timed out", "timed_out": True}

    ok = fc_proc.returncode == 0
    return {
        "ok": ok,
        "tool_exit": tool_proc.returncode,
        "filecheck_exit": fc_proc.returncode,
        "stderr_tail": (fc_proc.stderr or "")[-2000:],
    }


def resolve_update_script(state: UsherState, script_name: str) -> Path | None:
    name = Path(script_name).name
    if name not in SUPPORTED_UPDATE_SCRIPTS:
        return None
    candidates: list[Path] = []
    if state.update_scripts_dir is not None:
        candidates.append(state.update_scripts_dir / name)
    root = state.llvm_src
    candidates.extend(
        [
            root / "llvm" / "utils" / name,
            root / "utils" / name,
        ]
    )
    for c in candidates:
        if c.is_file():
            return c
    return None


def script_for_standalone(text: str, fmt: str) -> str:
    """Pick an update_* script for a standalone temp file."""
    note = autogen_script(text)
    if note and note in SUPPORTED_UPDATE_SCRIPTS:
        return note
    if fmt == "mir":
        return "update_mir_test_checks.py"
    runs = parse_all_runs(text)
    if runs and runs[0].tool == "llc":
        return "update_llc_test_checks.py"
    return "update_test_checks.py"


def ensure_usher_comment(
    test_text: str,
    *,
    suggested_host: str,
    note: str | None = None,
    fmt: str = "ll",
    style_mismatch: bool = False,
    style_mismatch_detail: str | None = None,
    # Back-compat aliases
    mir_only: bool | None = None,
    mir_only_detail: str | None = None,
) -> str:
    """Insert or refresh the Usher placement comment near the top."""
    if mir_only is not None:
        style_mismatch = bool(mir_only)
    if mir_only_detail is not None and style_mismatch_detail is None:
        style_mismatch_detail = mir_only_detail
    comment = ";" if fmt == "ll" else "#"
    lines = test_text.splitlines()
    # Drop prior Usher comments
    lines = [ln for ln in lines if not re.match(r"^[;#]\s*Usher:", ln)]
    insert_at = 0
    for i, line in enumerate(lines):
        if line.strip().startswith((";", "#")) and "RUN:" in line:
            insert_at = i
            break
        if line.strip() and not line.strip().startswith((";", "#")):
            insert_at = i
            break
    usher_lines: list[str]
    if style_mismatch:
        detail = (style_mismatch_detail or "").strip()
        usher_lines = [
            f"{comment} Usher: Style mismatch. {detail}".rstrip()
            if detail
            else (
                f"{comment} Usher: Style mismatch. No PR-style test covered the "
                f"target; ask the author whether the path is reachable in the "
                f"PR's style."
            )
        ]
        usher_lines.append(
            f"{comment} Usher: If kept, add to {suggested_host}"
            + (f" ({note.strip()})" if note and note.strip() else "")
        )
    else:
        host_line = f"{comment} Usher: add to {suggested_host}"
        if note and note.strip():
            host_line = f"{host_line} ({note.strip()})"
        usher_lines = [host_line]
    for offset, ul in enumerate(usher_lines):
        lines.insert(insert_at + offset, ul)
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    return text


def run_update_checks_on_standalone(
    state: UsherState,
    *,
    test_text: str,
    fmt: str,
    script_name: str | None = None,
    function_name: str | None = None,
) -> dict[str, Any]:
    """Run update_*_test_checks.py on a temp standalone file; return new text."""
    if looks_like_spirv(test_text):
        return {
            "ok": False,
            "error": (
                "SPIRV-like input: update scripts often fail; "
                "write CHECKs from dump_ir/get_output instead"
            ),
            "spirv": True,
        }
    script_name = script_name or script_for_standalone(test_text, fmt)
    script = resolve_update_script(state, script_name)
    if script is None:
        return {"ok": False, "error": f"update script not found: {script_name}"}

    tool_for_script = "llc" if "llc" in script_name or "mir" in script_name else "opt"
    tool_bin = state.oracle.tools.get(tool_for_script)  # type: ignore[arg-type]
    if tool_bin is None:
        tool_bin = next(iter(state.oracle.tools.values()), None)
    if tool_bin is None:
        return {"ok": False, "error": "no instrumented opt/llc for update script"}

    fn = function_name
    if fn is None and fmt == "ll":
        funcs = split_ll_functions(test_text)
        fn = funcs[0].name if funcs else function_name_from_ir(test_text)

    with tempfile.TemporaryDirectory(prefix="usher-annotate-") as tmp:
        tmp_path = Path(tmp) / f"standalone.{fmt}"
        tmp_path.write_text(test_text, encoding="utf-8")

        def _cmd(*binary_flags: str) -> list[str]:
            cmd = ["python3", str(script), *binary_flags]
            if fn and "mir" not in script_name:
                cmd.extend(["--function", fn])
            cmd.append(str(tmp_path))
            return cmd

        attempts: list[list[str]] = []
        if "llc" in script_name or "mir" in script_name:
            attempts.append(_cmd("--llc_binary", str(tool_bin)))
            attempts.append(_cmd("--llc-binary", str(tool_bin)))
        else:
            attempts.append(_cmd("--opt-binary", str(tool_bin)))
            attempts.append(_cmd("--tool-binary", str(tool_bin)))

        last: dict[str, Any] = {"ok": False, "error": "update script failed"}
        for cmd in attempts:
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            except subprocess.TimeoutExpired:
                return {"ok": False, "error": "update script timed out", "cmd": cmd}
            last = {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-1500:],
                "stderr_tail": (proc.stderr or "")[-1500:],
                "cmd": cmd,
                "script": script_name,
            }
            if proc.returncode == 0:
                last["test_text"] = tmp_path.read_text(encoding="utf-8")
                return last
        return last


def validate_standalone(
    state: UsherState,
    *,
    test_text: str,
    fmt: str,
) -> dict[str, Any]:
    """Coverage + optional FileCheck on a standalone lit file."""
    runs = parse_all_runs(test_text)
    if not runs:
        return {
            "ok": False,
            "covered": False,
            "filecheck_ok": False,
            "error": "standalone has no supported RUN lines",
        }
    parsed = runs[0]
    fmt_typed: InputFormat = fmt if fmt in ("ll", "mir") else "ll"  # type: ignore[assignment]
    cov = run_coverage_for_parsed(state, parsed, test_text, fmt_typed)
    covered = cov["target"]["status"] == "covered"
    coverage = {
        "status": cov["target"]["status"],
        "n_hit": cov["target"]["n_hit"],
        "n_points": cov["target"]["n_points"],
        "exit_code": cov["exit_code"],
        "run_index": parsed.line_index,
    }
    filecheck: dict[str, Any] = {"ok": True, "skipped": True}
    filecheck_ok = True
    if parsed.filecheck_args is not None:
        with tempfile.TemporaryDirectory(prefix="usher-fc-") as tmp:
            tmp_path = Path(tmp) / f"standalone.{fmt}"
            tmp_path.write_text(test_text, encoding="utf-8")
            fc = run_filecheck_pipeline(state=state, parsed=parsed, test_path=tmp_path)
            filecheck = {k: v for k, v in fc.items()}
            filecheck_ok = bool(fc.get("ok"))
            filecheck["skipped"] = False
    elif cov["exit_code"] != 0:
        filecheck_ok = False
        filecheck = {
            "ok": False,
            "skipped": True,
            "note": "no FileCheck on RUN; tool exit non-zero",
        }

    return {
        "ok": covered and filecheck_ok,
        "covered": covered,
        "filecheck_ok": filecheck_ok,
        "coverage": coverage,
        "filecheck": filecheck,
        "run": parsed.raw,
    }


def proposal_matches_pr_style(
    state: UsherState, test_text: str, fmt: str
) -> bool:
    """True if the proposal matches any PR-grounded declared style."""
    for style in state.declared_styles:
        if not style.pr_grounded:
            continue
        ok, _ = style.matches(test_text, fmt)
        if ok:
            return True
    return False


def style_violation(
    style: DeclaredStyle,
    *,
    fmt: str,
    argv: list[str],
    tool: str = "llc",
) -> str | None:
    """Return an error if *fmt*/*argv* disagree with the declared PR style."""
    if fmt != style.suffix:
        return f"format must be {style.suffix!r} to match declared style (got {fmt!r})"
    tool_name: ToolName = "opt" if tool == "opt" else "llc"
    parsed = ParsedRun(
        raw=" ".join([tool_name, *argv]),
        tool=tool_name,
        argv=list(argv),
        stdin_redirect=False,
        redirect_stderr=False,
        filecheck_args=[],
        line_index=0,
        output="stdout",
    )
    shape = run_shape(parsed, fmt)
    if shape != style.shape:
        return (
            f"RUN shape must be {style.shape!r} to match declared style "
            f"(got {shape!r} from args={argv!r})"
        )
    if style.triple:
        got_triple = triple_from_argv(argv)
        if got_triple != style.triple:
            return (
                f"argv must include -mtriple={style.triple} "
                f"(got {got_triple!r})"
            )
    got_flags = set(flags_from_argv(argv))
    missing = [f for f in style.flags if f not in got_flags]
    if missing:
        return f"argv missing required style flags {missing}"
    return None


def build_standalone_from_run(
    *,
    input_text: str,
    run_template: str,
    fmt: str,
    check_lines: str | None = None,
) -> str:
    """Build a lit file from a discovery run's input plus a declared RUN template."""
    comment = ";" if fmt == "ll" else "#"
    run_line = f"{comment} RUN: {run_template.strip()}"
    body = input_text.strip()
    # Drop any existing RUN / Usher headers from the input body.
    body_lines = [
        ln
        for ln in body.splitlines()
        if not re.match(r"^[;#]\s*(?:RUN:|Usher:)", ln)
    ]
    parts = [run_line]
    if check_lines and check_lines.strip():
        parts.append(check_lines.strip())
    parts.append("\n".join(body_lines))
    text = "\n".join(parts)
    if not text.endswith("\n"):
        text += "\n"
    return text


def evidence_file_style(
    llvm_src: Path, rel: str
) -> tuple[str, str] | str:
    """Return ``(suffix, shape)`` for a lit file, or an error string."""
    rel_n = rel.replace("\\", "/")
    path = llvm_src / rel_n
    if not path.is_file():
        return f"evidence file not found under llvm-src: {rel_n}"
    suffix = path.suffix.lstrip(".")
    if suffix not in ("ll", "mir"):
        return f"evidence {rel_n} has unsupported suffix .{suffix}"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"cannot read evidence {rel_n}: {exc}"
    runs = parse_all_runs(text)
    if not runs:
        return f"evidence {rel_n} has no supported RUN line to classify"
    primary = next((r for r in runs if r.filecheck_args is not None), runs[0])
    return suffix, run_shape(primary, suffix)


def evidence_matches_declaration(
    *,
    llvm_src: Path,
    evidence: list[str],
    suffix: str,
    shape: str,
) -> str | None:
    """Return an error if any evidence file disagrees with the declaration."""
    mismatches: list[str] = []
    for rel in evidence:
        got = evidence_file_style(llvm_src, rel)
        if isinstance(got, str):
            return got
        got_suffix, got_shape = got
        if got_suffix != suffix or got_shape != shape:
            mismatches.append(
                f"{rel} is .{got_suffix}/{got_shape}, not .{suffix}/{shape}"
            )
    if mismatches:
        return (
            "declare_test_style must describe what the evidence files actually are "
            "(not a preferred format for coverage). "
            + "; ".join(mismatches)
        )
    return None


def declare_test_style_impl(state: UsherState, args: dict[str, Any]) -> dict[str, Any]:
    """Validate and record a declare_test_style call. Returns a plain payload dict."""
    suffix = str(args.get("suffix") or "").strip()
    if suffix not in ("ll", "mir"):
        return {"ok": False, "error": "suffix must be ll or mir"}
    run_template = str(args.get("run_template") or "").strip()
    if not run_template:
        return {"ok": False, "error": "run_template is required"}
    evidence_raw = args.get("evidence")
    if not isinstance(evidence_raw, list) or not evidence_raw:
        return {"ok": False, "error": "evidence must be a non-empty list of paths you read"}
    evidence = [str(p).replace("\\", "/").strip() for p in evidence_raw if str(p).strip()]
    if not evidence:
        return {"ok": False, "error": "evidence must be a non-empty list of paths you read"}
    unread = [p for p in evidence if p not in state.read_paths]
    if unread:
        return {
            "ok": False,
            "error": (
                "evidence paths must be opened with read_source first: "
                + ", ".join(unread)
            ),
        }
    if not state.pr_test_paths and state.diff_path.is_file():
        diff_text = state.diff_path.read_text(encoding="utf-8", errors="replace")
        info = list_pr_tests_info(
            diff_text=diff_text, target_rel=state.target.rel_path
        )
        state.pr_test_paths = [t["path"] for t in info["tests"]]
        state.mapped_test_dir = info.get("mapped_test_dir")

    parsed = parse_run_template(run_template, suffix)
    if isinstance(parsed, str):
        return {"ok": False, "error": parsed}

    mismatch = evidence_matches_declaration(
        llvm_src=state.llvm_src,
        evidence=evidence,
        suffix=suffix,
        shape=parsed.shape,
    )
    if mismatch:
        return {"ok": False, "error": mismatch}

    pr_set = set(state.pr_test_paths)
    if pr_set:
        if not any(p in pr_set for p in evidence):
            return {
                "ok": False,
                "error": (
                    "when the PR touches tests, at least one evidence path must be "
                    "a PR-touched test from list_pr_tests"
                ),
            }
        pr_grounded = True
    else:
        mapped = (state.mapped_test_dir or "").replace("\\", "/")
        pr_grounded = bool(
            mapped
            and any(
                p == mapped or p.startswith(mapped.rstrip("/") + "/")
                for p in evidence
            )
        )

    extra_raw = args.get("extra_runs") or []
    extra_runs: list[str] = []
    if isinstance(extra_raw, list):
        extra_runs = [str(x).strip() for x in extra_raw if str(x).strip()]
    rationale = str(args.get("rationale") or "").strip()
    if not rationale:
        return {"ok": False, "error": "rationale is required"}

    style = DeclaredStyle(
        style_id=len(state.declared_styles) + 1,
        suffix=suffix,  # type: ignore[arg-type]
        run_template=run_template,
        shape=parsed.shape,
        triple=parsed.triple,
        flags=list(parsed.flags),
        evidence=evidence,
        rationale=rationale,
        pr_grounded=pr_grounded,
        extra_runs=extra_runs,
    )
    state.declared_styles.append(style)
    state.history.append(
        {
            "event": "declare_test_style",
            "style_id": style.style_id,
            "suffix": style.suffix,
            "run_template": style.run_template,
            "shape": style.shape,
            "pr_grounded": style.pr_grounded,
            "evidence": list(evidence),
        }
    )
    return {
        "ok": True,
        "style": style.to_json(),
        "active": True,
        "hint": (
            "Active style updated. Use select_tool / record_analysis / "
            "run_candidate in this style. When a run covers the target, call "
            "finalize_standalone(run=N). Fallback to a non-PR format unlocks "
            "only after discovery budget/stale/likely_unreachable."
        ),
    }


def finalize_standalone_impl(
    state: UsherState, args: dict[str, Any]
) -> dict[str, Any]:
    """Validate and record a finalize_standalone call. Returns a plain payload dict."""
    budget = state.budget_exhausted()
    if budget:
        state.gave_up = True
        state.give_up_reason = budget
        state.stop_requested = True
        return {"ok": False, "error": budget}

    active = state.active_style()
    if active is None:
        return {
            "ok": False,
            "error": (
                "declare_test_style first (list_pr_tests → read_source → declare)"
            ),
        }

    suggested_host = str(args.get("suggested_host") or "").strip()
    if not suggested_host:
        return {
            "ok": False,
            "error": (
                "suggested_host is required (existing lit path or suggested new path)"
            ),
        }
    note = args.get("note")
    note_s = str(note).strip() if isinstance(note, str) and note.strip() else None

    from_run: int | None = None
    run_raw = args.get("run")
    test_text = args.get("test_text")
    check_lines = args.get("check_lines")
    check_s = (
        str(check_lines).strip()
        if isinstance(check_lines, str) and check_lines.strip()
        else None
    )

    if run_raw is not None:
        if state.discovery is None or not state.discovery.runs:
            return {"ok": False, "error": "no discovery runs; call run_candidate first"}
        try:
            from_run = int(run_raw)
        except (TypeError, ValueError):
            return {"ok": False, "error": "run must be an integer discovery run number"}
        if not 1 <= from_run <= len(state.discovery.runs):
            return {
                "ok": False,
                "error": (
                    f"run must be between 1 and {len(state.discovery.runs)}"
                ),
            }
        chosen = state.discovery.runs[from_run - 1]
        fmt = str(args.get("format") or chosen.fmt or active.suffix)
        if fmt not in ("ll", "mir"):
            return {"ok": False, "error": "format must be ll or mir"}
        # Prefer declared RUN template when the run matches PR style.
        run_ok = state.run_style_ok.get(from_run, False)
        template = active.run_template if run_ok else None
        if template is None:
            # Build a simple FileCheck RUN from the discovery argv.
            tool = chosen.tool
            argv = " ".join(chosen.argv)
            template = f"{tool} {argv} %s -o - | FileCheck %s".strip()
        test_text = build_standalone_from_run(
            input_text=chosen.input_text,
            run_template=template,
            fmt=fmt,
            check_lines=check_s,
        )
    else:
        if not isinstance(test_text, str) or not test_text.strip():
            return {
                "ok": False,
                "error": (
                    "test_text is required, or pass run=N from a covering "
                    "run_candidate"
                ),
            }
        fmt = str(args.get("format") or active.suffix or state.fill_test_fmt or "ll")
        if fmt not in ("ll", "mir"):
            return {"ok": False, "error": "format must be ll or mir"}

    assert isinstance(test_text, str)
    host_norm = suggested_host.replace("\\", "/")
    if not host_norm.endswith(f".{fmt}"):
        return {
            "ok": False,
            "error": (
                f"suggested_host suffix must match format .{fmt} "
                f"(got {suggested_host!r})"
            ),
        }

    style_ok, style_reasons = active.matches(test_text, fmt)
    pr_style_ok = proposal_matches_pr_style(state, test_text, fmt)

    annotated = ensure_usher_comment(
        test_text,
        suggested_host=suggested_host,
        note=note_s,
        fmt=fmt,
    )
    validation = validate_standalone(state, test_text=annotated, fmt=fmt)
    proposal = StandaloneProposal(
        proposal_id=len(state.proposals) + 1,
        test_text=annotated,
        suggested_host=suggested_host,
        note=note_s,
        covered=bool(validation.get("covered")),
        filecheck_ok=bool(validation.get("filecheck_ok")),
        coverage=dict(validation.get("coverage") or {}),
        filecheck=dict(validation.get("filecheck") or {}),
        fmt=fmt,
        style_id=active.style_id,
        style_ok=style_ok,
        style_reasons=list(style_reasons),
        pr_style_ok=pr_style_ok,
    )
    state.proposals.append(proposal)
    state.latest_proposal = proposal
    state.history.append(
        {
            "event": "finalize_standalone",
            "proposal": proposal.proposal_id,
            "suggested_host": suggested_host,
            "fmt": fmt,
            "from_run": from_run,
            "covered": proposal.covered,
            "filecheck_ok": proposal.filecheck_ok,
            "style_ok": style_ok,
            "pr_style_ok": pr_style_ok,
            "style_reasons": list(style_reasons),
        }
    )
    hint = "call accept if covered and FileCheck ok"
    if not proposal.covered or not proposal.filecheck_ok:
        hint = str(
            validation.get("error")
            or validation.get("filecheck", {}).get("stderr_tail")
            or validation.get("filecheck", {}).get("error")
            or "fix RUN/CHECKs and finalize again"
        )
    elif not pr_style_ok:
        unlocked = state.fallback_unlocked_by()
        if unlocked:
            hint = (
                f"covered with style mismatch ({'; '.join(style_reasons)}). "
                f"Fallback unlocked ({unlocked}); accept with style_reason."
            )
        else:
            hint = (
                f"covered, but style mismatch ({'; '.join(style_reasons)}). "
                f"Keep searching with run_candidate in the declared style "
                f"({active.run_template}); fallback unlocks on budget/stale/"
                f"likely_unreachable."
            )
    return {
        "ok": True,
        "proposal": proposal.proposal_id,
        "suggested_host": suggested_host,
        "fmt": fmt,
        "from_run": from_run,
        "covered": proposal.covered,
        "filecheck_ok": proposal.filecheck_ok,
        "style_ok": style_ok,
        "pr_style_ok": pr_style_ok,
        "style_reasons": style_reasons,
        "fallback_unlocked": state.fallback_unlocked(),
        "fallback_unlocked_by": state.fallback_unlocked_by(),
        "coverage": proposal.coverage,
        "filecheck": proposal.filecheck,
        "run": validation.get("run"),
        "hint": hint,
    }


def accept_proposal_impl(state: UsherState, args: dict[str, Any]) -> dict[str, Any]:
    """Accept a proposal with the PR-style gate. Returns a plain payload dict."""
    raw = args.get("proposal")
    if raw is None:
        if state.latest_proposal is None:
            return {"ok": False, "error": "no proposal to accept"}
        proposal = state.latest_proposal
    else:
        try:
            pid = int(raw)
        except (TypeError, ValueError):
            return {"ok": False, "error": "proposal must be an integer"}
        if not 1 <= pid <= len(state.proposals):
            return {
                "ok": False,
                "error": f"proposal must be between 1 and {len(state.proposals)}",
            }
        proposal = state.proposals[pid - 1]

    if not proposal.covered:
        return {
            "ok": False,
            "error": f"proposal {proposal.proposal_id} does not cover the target",
        }
    if not proposal.filecheck_ok:
        return {
            "ok": False,
            "error": (
                f"proposal {proposal.proposal_id} FileCheck (or tool) "
                "validation failed"
            ),
        }

    style_reason_raw = args.get("style_reason")
    style_reason = (
        str(style_reason_raw).strip()
        if isinstance(style_reason_raw, str) and style_reason_raw.strip()
        else None
    )

    if not proposal.pr_style_ok:
        missing: list[str] = []
        if not state.fallback_unlocked():
            missing.append(
                "fallback not unlocked yet (need discovery budget exhausted, "
                "stale runs, or likely_unreachable analysis)"
            )
        if not style_reason:
            missing.append("pass style_reason explaining why PR style failed")
        if missing:
            return {
                "ok": False,
                "error": "cannot accept style-mismatched proposal: "
                + "; ".join(missing),
            }

    proposal.style_reason = style_reason
    state.accepted = True
    state.accepted_by = "agent"
    state.accepted_proposal = proposal
    state.accepted_style_reason = style_reason
    state.latest_proposal = proposal
    state.stop_requested = True
    state.history.append(
        {
            "event": "accept",
            "proposal": proposal.proposal_id,
            "suggested_host": proposal.suggested_host,
            "pr_style_ok": proposal.pr_style_ok,
            "style_reason": style_reason,
            "fallback_unlocked_by": state.fallback_unlocked_by(),
        }
    )
    return {
        "ok": True,
        "accepted": True,
        "proposal": proposal.proposal_id,
        "suggested_host": proposal.suggested_host,
        "pr_style_ok": proposal.pr_style_ok,
    }


def build_usher_tools(state: UsherState):
    """MCP server for usher-test: shared source tools + standalone finalize tools."""

    if state.discovery is None:
        raise ValueError("UsherState.discovery SessionState is required")

    fill_handlers = make_fill_handlers(state.discovery)

    async def run_candidate(args: dict[str, Any]) -> dict[str, Any]:
        """Style-gated wrapper around fill-line run_candidate."""
        active = state.active_style()
        if active is None:
            return error_payload(
                "declare_test_style before run_candidate "
                "(list_pr_tests → read_source → declare)"
            )
        fmt_raw = str(args.get("format") or active.suffix)
        argv_in = args.get("args") or []
        if not isinstance(argv_in, list):
            return error_payload("args must be a list of strings")
        tool = state.discovery.selected_tool or "llc"
        viol = style_violation(
            active, fmt=fmt_raw, argv=[str(a) for a in argv_in], tool=tool
        )
        style_ok = viol is None
        if viol and not state.fallback_unlocked():
            return error_payload(
                f"style gate: {viol}. "
                "Keep searching in the declared PR style; fallback unlocks "
                "on budget/stale/likely_unreachable."
            )
        before = len(state.discovery.runs)
        result = await fill_handlers["run_candidate"](args)
        after = len(state.discovery.runs)
        if after > before:
            run_no = after
            state.run_style_ok[run_no] = style_ok
            try:
                import json

                content = result.get("content") or []
                if content and isinstance(content[0], dict):
                    text = content[0].get("text") or ""
                    payload = json.loads(text)
                    if isinstance(payload, dict):
                        payload["style_ok"] = style_ok
                        if viol:
                            payload["style_note"] = viol
                        content[0]["text"] = json.dumps(payload)
            except Exception:
                pass
        return result

    async def list_pr_tests(args: dict[str, Any]) -> dict[str, Any]:
        diff_text = (
            state.diff_path.read_text(encoding="utf-8", errors="replace")
            if state.diff_path.is_file()
            else ""
        )
        info = list_pr_tests_info(
            diff_text=diff_text, target_rel=state.target.rel_path
        )
        state.pr_test_paths = [t["path"] for t in info["tests"]]
        state.mapped_test_dir = info.get("mapped_test_dir")
        return text_payload(
            {
                "ok": True,
                **info,
                "hint": (
                    "Read these files with read_source, then call declare_test_style "
                    "citing the paths you opened. No conclusions are drawn here."
                ),
            }
        )

    async def declare_test_style(args: dict[str, Any]) -> dict[str, Any]:
        result = declare_test_style_impl(state, args)
        if not result.get("ok"):
            return error_payload(str(result.get("error") or "declare_test_style failed"))
        return text_payload(result)

    async def list_candidate_tests(args: dict[str, Any]) -> dict[str, Any]:
        hint = args.get("pass_hint")
        style = state.active_style()
        search_dirs: list[str] | None = None
        if style is not None:
            search_dirs = [str(Path(e).parent) for e in style.evidence]
        elif state.pr_test_paths:
            search_dirs = [str(Path(p).parent) for p in state.pr_test_paths]
        rows = rank_candidate_tests(
            llvm_src=state.llvm_src,
            diff_path=state.diff_path,
            pass_hint=str(hint) if hint else None,
            style=style,
            search_dirs=search_dirs,
        )
        return text_payload({"ok": True, "candidates": rows, "count": len(rows)})

    async def get_output(args: dict[str, Any]) -> dict[str, Any]:
        raw = args.get("run")
        try:
            run_no = int(raw)
        except (TypeError, ValueError):
            return error_payload("run must be an integer dump run number")
        if not 1 <= run_no <= len(state.dump_results):
            return error_payload(
                f"run must be between 1 and {len(state.dump_results)} (dump runs)"
            )
        result = state.dump_results[run_no - 1]
        capture = result.capture or ""
        page = stream_page(
            capture, offset=int(args.get("offset") or 0), n_lines=CAPTURE_PAGE_LINES
        )
        return text_payload(
            {
                "ok": True,
                "run": run_no,
                "tool": result.tool,
                "capture_present": result.capture is not None,
                **page,
            }
        )

    async def dump_ir(args: dict[str, Any]) -> dict[str, Any]:
        tool = str(args.get("tool") or "")
        if tool not in ("opt", "llc"):
            return error_payload("tool must be opt or llc")
        if tool not in state.oracle.tools:
            return error_payload(f"tool {tool} not available")
        argv_in = args.get("args") or []
        if not isinstance(argv_in, list):
            return error_payload("args must be a list of strings")
        active = state.active_style()
        default_fmt = (
            active.suffix if active else (state.fill_test_fmt or "ll")
        )
        fmt_raw = str(args.get("format") or default_fmt)
        if fmt_raw not in ("ll", "mir"):
            return error_payload("format must be ll or mir")
        fmt: InputFormat = fmt_raw  # type: ignore[assignment]
        try:
            argv = validate_argv(tool, list(argv_in), fmt)  # type: ignore[arg-type]
        except ValueError as exc:
            return error_payload(str(exc))
        if active is not None:
            viol = style_violation(active, fmt=fmt, argv=argv, tool=tool)
            if viol and not state.fallback_unlocked():
                return error_payload(
                    f"dump_ir style gate: {viol}. "
                    "Use the declared PR style, or wait until fallback unlocks."
                )
        input_text = str(args.get("input") or "")
        if not input_text.strip():
            _h, body = strip_header_comments_keep_run(state.fill_test_text)
            input_text = body
        result = state.oracle.run(tool, argv, input_text, fmt)  # type: ignore[arg-type]
        state.dump_results.append(result)
        m = result.measure
        return text_payload(
            {
                "ok": True,
                "run": len(state.dump_results),
                "tool": result.tool,
                "exit_code": result.exit_code,
                "timed_out": result.timed_out,
                "capture_present": result.capture is not None,
                "target": {
                    "status": m.status if m else "uncovered",
                    "n_hit": m.n_hit if m else 0,
                    "n_points": m.n_points if m else 0,
                },
                "hint": "use get_output to page the -o capture",
            }
        )

    async def annotate_checks(args: dict[str, Any]) -> dict[str, Any]:
        budget = state.budget_exhausted()
        if budget:
            state.gave_up = True
            state.give_up_reason = budget
            state.stop_requested = True
            return error_payload(budget)

        test_text = args.get("test_text")
        if not isinstance(test_text, str) or not test_text.strip():
            return error_payload("test_text is required (full standalone lit file)")
        active = state.active_style()
        default_fmt = active.suffix if active else (state.fill_test_fmt or "ll")
        fmt = str(args.get("format") or default_fmt)
        if fmt not in ("ll", "mir"):
            return error_payload("format must be ll or mir")
        script = args.get("script")
        script_name = str(script) if script else None
        fn = args.get("function")
        function_name = str(fn) if fn else None

        result = run_update_checks_on_standalone(
            state,
            test_text=test_text,
            fmt=fmt,
            script_name=script_name,
            function_name=function_name,
        )
        state.history.append(
            {
                "event": "annotate_checks",
                "ok": bool(result.get("ok")),
                "script": result.get("script") or script_name,
            }
        )
        if not result.get("ok"):
            return text_payload({"ok": False, **result})
        return text_payload(
            {
                "ok": True,
                "test_text": result["test_text"],
                "script": result.get("script"),
                "hint": "pass the returned test_text to finalize_standalone",
            }
        )

    async def finalize_standalone(args: dict[str, Any]) -> dict[str, Any]:
        result = finalize_standalone_impl(state, args)
        if not result.get("ok"):
            return error_payload(
                str(result.get("error") or "finalize_standalone failed")
            )
        return text_payload(result)

    async def accept(args: dict[str, Any]) -> dict[str, Any]:
        result = accept_proposal_impl(state, args)
        if not result.get("ok"):
            return error_payload(str(result.get("error") or "accept failed"))
        return text_payload(result)

    async def give_up(args: dict[str, Any]) -> dict[str, Any]:
        state.gave_up = True
        state.give_up_reason = str(args.get("reason") or "agent gave up")
        state.stop_requested = True
        state.history.append(
            {"event": "give_up", "reason": state.give_up_reason}
        )
        return text_payload(
            {"ok": True, "gave_up": True, "reason": state.give_up_reason}
        )

    usher_specs = [
        (
            "list_pr_tests",
            "List lit test files the PR touches (paths, added/modified, added RUN "
            "excerpts). Facts only — read them with read_source, then call "
            "declare_test_style. If empty, use mapped_test_dir for nearby tests.",
            {"type": "object", "properties": {}},
            list_pr_tests,
        ),
        (
            "declare_test_style",
            "Declare what the PR's tests actually look like after reading them. "
            "Evidence files must match the declared suffix and RUN shape (citing a "
            ".ll codegen test while declaring MIR is rejected). Redeclare PR-matching "
            "variants if attempts fail. Required before finalize_standalone.",
            {
                "type": "object",
                "properties": {
                    "suffix": {
                        "type": "string",
                        "description": "ll or mir",
                    },
                    "run_template": {
                        "type": "string",
                        "description": (
                            "Primary RUN to copy, e.g. "
                            "llc -O0 -mtriple=spirv64-unknown-unknown %s -o - | "
                            "FileCheck %s"
                        ),
                    },
                    "extra_runs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional additional RUNs (e.g. spirv-val)",
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Paths you read with read_source",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this is the PR's style",
                    },
                },
                "required": ["suffix", "run_template", "evidence", "rationale"],
            },
            declare_test_style,
        ),
        (
            "list_candidate_tests",
            "List lit test files that are good paste targets. Prefers style match "
            "and PR-touched files. Only files with at least one supported RUN line. "
            "Humans will merge; do not edit hosts.",
            {
                "type": "object",
                "properties": {
                    "pass_hint": {
                        "type": "string",
                        "description": "Optional pass or function name to search for",
                    },
                },
            },
            list_candidate_tests,
        ),
        (
            "dump_ir",
            "Run instrumented opt/llc to capture output for writing CHECK lines "
            "(not a discovery substitute). Subject to the same style gate as "
            "run_candidate unless fallback is unlocked. Page with get_output.",
            {
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "args": {"type": "array", "items": {"type": "string"}},
                    "input": {"type": "string"},
                    "format": {"type": "string"},
                },
                "required": ["tool", "args"],
            },
            dump_ir,
        ),
        (
            "get_output",
            "Page the capture from a prior dump_ir run.",
            {"run": int, "offset": int},
            get_output,
        ),
        (
            "annotate_checks",
            "Run update_*_test_checks.py on a temp copy of a standalone lit file "
            "(not a host). Returns rewritten test_text with CHECKs. Soft-fails for "
            "SPIRV-like inputs — write CHECKs from dump_ir instead.",
            {
                "type": "object",
                "properties": {
                    "test_text": {
                        "type": "string",
                        "description": "Full standalone lit file to annotate",
                    },
                    "format": {"type": "string", "description": "ll or mir"},
                    "script": {
                        "type": "string",
                        "description": "Optional update_*_test_checks.py basename",
                    },
                    "function": {
                        "type": "string",
                        "description": "Optional --function name for .ll scripts",
                    },
                },
                "required": ["test_text"],
            },
            annotate_checks,
        ),
        (
            "finalize_standalone",
            "Build/validate a standalone lit proposal. Prefer run=N from a "
            "covering run_candidate (uses that input + the declared RUN "
            "template + optional check_lines). Or pass full test_text. "
            "Requires declare_test_style. Host suffix must match format.",
            {
                "type": "object",
                "properties": {
                    "run": {
                        "type": "integer",
                        "description": (
                            "Discovery run number whose input becomes the body"
                        ),
                    },
                    "check_lines": {
                        "type": "string",
                        "description": (
                            "Optional CHECK lines when building from run=N"
                        ),
                    },
                    "test_text": {
                        "type": "string",
                        "description": "Full standalone lit file (alternative to run=N)",
                    },
                    "suggested_host": {
                        "type": "string",
                        "description": (
                            "Where a human should paste this "
                            "(e.g. llvm/test/CodeGen/AMDGPU/foo.ll)"
                        ),
                    },
                    "note": {
                        "type": "string",
                        "description": "Optional placement hint (after @fn, new file, …)",
                    },
                    "format": {"type": "string"},
                },
                "required": ["suggested_host"],
            },
            finalize_standalone,
        ),
        (
            "accept",
            "Accept a standalone proposal that covers the target and passes "
            "validation. Style-mismatched proposals need fallback_unlocked "
            "(budget/stale/likely_unreachable) plus style_reason.",
            {
                "type": "object",
                "properties": {
                    "proposal": {"type": "integer"},
                    "style_reason": {
                        "type": "string",
                        "description": (
                            "Required when accepting a non-PR-style proposal "
                            "after fallback unlocks"
                        ),
                    },
                },
            },
            accept,
        ),
        (
            "give_up",
            "Stop without accepting. The harness may still emit a standalone file "
            "with a heuristic suggested_host comment for a human to paste.",
            {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                },
                "required": ["reason"],
            },
            give_up,
        ),
    ]

    # Fill-line discovery specs with wrapped run_candidate; skip fill-line
    # accept/give_up — usher owns those.
    wrapped_handlers = {**fill_handlers, "run_candidate": run_candidate}
    discovery_specs = [
        spec
        for spec in fill_tool_specs(state.discovery, wrapped_handlers)
        if spec[0] not in ("accept", "give_up")
    ]

    return build_mcp_server(
        name="usher",
        version="1.0.0",
        state=state,
        tools=source_tool_specs(state) + discovery_specs + usher_specs,
        summarize=_summarize,
    )
