# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Agent-neutral source / diff MCP tool handlers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Awaitable, Callable

from fill_line_agent.oracle import stream_page
from fill_line_agent.tool_common import error_payload, resolve_under_root, text_payload

DIFF_PAGE_LINES = 200
GREP_MAX_MATCHES = 40
GREP_MAX_LINE_LEN = 240
SOURCE_MAX_LINES = 200

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


def make_source_handlers(state: Any) -> dict[str, ToolHandler]:
    """Return handlers closed over *state* (needs llvm_src, diff_path, oracle)."""

    async def read_diff(args: dict[str, Any]) -> dict[str, Any]:
        offset = int(args.get("offset") or 0)
        text = state.diff_path.read_text(encoding="utf-8", errors="replace")
        page = stream_page(text, offset=offset, n_lines=DIFF_PAGE_LINES)
        return text_payload({"ok": True, "path": str(state.diff_path), **page})

    async def read_source(args: dict[str, Any]) -> dict[str, Any]:
        rel = str(args.get("path") or "")
        if not rel:
            return error_payload("path is required")
        ranges_in = args.get("ranges")
        if ranges_in:
            if not isinstance(ranges_in, list):
                return error_payload("ranges must be a list of [start, end] pairs")
            raw = ranges_in
        elif args.get("start") is not None and args.get("end") is not None:
            raw = [[args["start"], args["end"]]]
        else:
            return error_payload("give start and end, or ranges")
        ranges: list[tuple[int, int]] = []
        for item in raw:
            try:
                if isinstance(item, dict):
                    lo, hi = int(item["start"]), int(item["end"])
                else:
                    lo, hi = int(item[0]), int(item[1])
            except (KeyError, IndexError, TypeError, ValueError):
                return error_payload(f"bad range {item!r}; use [start, end]")
            ranges.append((min(lo, hi), max(lo, hi)))
        total = sum(hi - lo + 1 for lo, hi in ranges)
        if total > SOURCE_MAX_LINES:
            return error_payload(
                f"ranges too large ({total} lines); max {SOURCE_MAX_LINES} per call"
            )
        try:
            path = resolve_under_root(state.llvm_src, rel)
        except ValueError as exc:
            return error_payload(str(exc))
        if not path.is_file():
            return error_payload(f"file not found: {rel}")
        # Usher (and any state with read_paths) records evidence for declare_test_style.
        read_paths = getattr(state, "read_paths", None)
        if isinstance(read_paths, set):
            read_paths.add(rel.replace("\\", "/"))
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        chunks: list[dict[str, Any]] = []
        for lo, hi in ranges:
            lo = max(1, lo)
            hi = min(len(lines), hi)
            numbered = [f"{i}:{lines[i - 1]}" for i in range(lo, hi + 1)]
            chunks.append({"start": lo, "end": hi, "text": "\n".join(numbered)})
        if len(chunks) == 1:
            return text_payload({"ok": True, "path": rel, **chunks[0]})
        return text_payload({"ok": True, "path": rel, "ranges": chunks})

    async def grep_source(args: dict[str, Any]) -> dict[str, Any]:
        pattern = str(args["pattern"])
        path_glob = str(args.get("path_glob") or "**/*.{cpp,h,c,inc,td,ll,mir}")
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            return error_payload(f"invalid regex: {exc}")
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
                        return text_payload(
                            {"ok": True, "truncated": True, "matches": hits}
                        )
        return text_payload({"ok": True, "truncated": False, "matches": hits})

    async def instrumented_lines(args: dict[str, Any]) -> dict[str, Any]:
        tool_name = str(args["tool"])
        if tool_name not in state.oracle.indexes:
            return error_payload(f"unknown or unavailable tool: {tool_name}")
        rows = state.oracle.indexes[tool_name].instrumented_lines(
            str(args["path"]),
            int(args["start"]),
            int(args["end"]),
        )
        return text_payload({"ok": True, "tool": tool_name, "lines": rows})

    return {
        "read_diff": read_diff,
        "read_source": read_source,
        "grep_source": grep_source,
        "instrumented_lines": instrumented_lines,
    }


def source_tool_specs(state: Any) -> list[tuple[str, str, dict[str, Any] | type, ToolHandler]]:
    """MCP tool specs shared by fill-line and usher-test."""
    h = make_source_handlers(state)
    return [
        (
            "read_diff",
            "Read a page of the PR diff. Use offset to page through large diffs.",
            {"offset": int},
            h["read_diff"],
        ),
        (
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
            h["read_source"],
        ),
        (
            "grep_source",
            "Search LLVM sources. Each hit is path:line:text.",
            {"pattern": str, "path_glob": str},
            h["grep_source"],
        ),
        (
            "instrumented_lines",
            "List instrumented lines for a tool in [start, end] of path.",
            {"tool": str, "path": str, "start": int, "end": int},
            h["instrumented_lines"],
        ),
    ]
