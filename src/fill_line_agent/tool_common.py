# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Shared MCP server helpers for fill-line and usher-test."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Awaitable, Callable

from fuzz_fill.log import get_logger

logger = get_logger("fill_line_agent.tool_common")

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


def text_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(payload, indent=2, default=str)}]
    }


def error_payload(message: str) -> dict[str, Any]:
    return text_payload({"ok": False, "error": message})


def resolve_under_root(root: Path, rel: str) -> Path:
    candidate = (root / rel).resolve()
    root_resolved = root.resolve()
    if root_resolved not in candidate.parents and candidate != root_resolved:
        raise ValueError(f"path escapes llvm-src root: {rel!r}")
    return candidate


def build_mcp_server(
    *,
    name: str,
    version: str,
    state: Any,
    tools: list[Any],
    summarize: Callable[[str, dict[str, Any]], str] | None = None,
):
    """Wrap tool handlers with busy/step tracking and create an SDK MCP server."""
    try:
        from claude_agent_sdk import create_sdk_mcp_server, tool
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "claude-agent-sdk is required; install with: pip install 'fuzz-fill[agent]'"
        ) from exc

    def tracked(
        tool_name: str,
        description: str,
        schema: dict[str, Any] | type,
        handler: ToolHandler,
    ):
        @tool(tool_name, description, schema)
        async def wrapped(args: dict[str, Any]) -> dict[str, Any]:
            detail = ""
            if summarize is not None:
                detail = summarize(tool_name, args if isinstance(args, dict) else {})
            state.tool_busy = True
            try:
                with state.steps.step(f"tool:{tool_name}", detail):
                    result = await handler(args)
            finally:
                state.tool_busy = False
            state.note_tool_call(tool_name)
            if hasattr(state, "progress_line"):
                logger.info("%s", state.progress_line())
            return result

        return wrapped

    wrapped_tools = []
    for spec in tools:
        # Each spec is (name, description, schema, handler) or already a tracked tool
        if isinstance(spec, tuple) and len(spec) == 4:
            wrapped_tools.append(tracked(*spec))
        else:
            wrapped_tools.append(spec)

    server = create_sdk_mcp_server(name=name, version=version, tools=wrapped_tools)
    allowed = [f"mcp__{name}__{t.name}" for t in wrapped_tools]
    return server, allowed
