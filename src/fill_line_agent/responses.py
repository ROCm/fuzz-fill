# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Per-response timing, size, and content log for fill-line LLM replies."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fuzz_fill.log import get_logger

logger = get_logger("fill_line_agent.responses")

TOOL_INPUT_PREVIEW = 160


@dataclass
class _Pending:
    index: int
    message_id: str | None
    started_at: float
    first_delta_at: float | None = None
    stopped_at: float | None = None
    model: str | None = None
    stop_reason: str | None = None
    input_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_creation_tokens: int | None = None
    output_tokens: int | None = None
    blocks: list[dict[str, Any]] = field(default_factory=list)
    block_ids: set[str] = field(default_factory=set)


def _int_or_none(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _block_record(block: object) -> tuple[str | None, dict[str, Any]] | None:
    """Return ``(dedupe_key, record)`` for one SDK content block."""
    name = type(block).__name__
    if name == "ThinkingBlock":
        text = str(getattr(block, "thinking", "") or "")
        return (f"thinking:{hash(text)}", {"type": "thinking", "chars": len(text), "text": text})
    if name == "RedactedThinkingBlock":
        return (None, {"type": "redacted_thinking"})
    if name == "TextBlock":
        text = str(getattr(block, "text", "") or "")
        return (f"text:{hash(text)}", {"type": "text", "chars": len(text), "text": text})
    if name == "ToolUseBlock":
        tool_input = getattr(block, "input", None) or {}
        encoded = json.dumps(tool_input, default=str)
        return (
            f"tool:{getattr(block, 'id', '')}",
            {
                "type": "tool_use",
                "name": str(getattr(block, "name", "")),
                "input_bytes": len(encoded),
                "input": tool_input,
            },
        )
    return None


class ResponseLog:
    """Track each API response from stream events and assistant messages.

    A response starts at a ``message_start`` stream event and is finalized when
    the next response starts, a non-assistant message arrives, or the session ends.
    The CLI may emit several assistant messages (one per content block) for a
    single API response; they are merged by ``message_id``.
    """

    def __init__(self, out_dir: Path | None) -> None:
        self.path = out_dir / "responses.jsonl" if out_dir is not None else None
        self.records: list[dict[str, Any]] = []
        self._pending: _Pending | None = None
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("", encoding="utf-8")

    def on_stream_event(self, event: dict[str, Any] | None) -> bool:
        """Handle one raw API stream event. Return True when a response starts."""
        if not isinstance(event, dict):
            return False
        etype = event.get("type")
        now = time.perf_counter()
        if etype == "message_start":
            self.finalize()
            message = event.get("message") or {}
            usage = message.get("usage") or {}
            self._pending = _Pending(
                index=len(self.records) + 1,
                message_id=message.get("id"),
                started_at=now,
                model=message.get("model"),
                input_tokens=_int_or_none(usage.get("input_tokens")),
                cache_read_tokens=_int_or_none(usage.get("cache_read_input_tokens")),
                cache_creation_tokens=_int_or_none(
                    usage.get("cache_creation_input_tokens")
                ),
            )
            return True
        pending = self._pending
        if pending is None:
            return False
        if etype == "content_block_delta" and pending.first_delta_at is None:
            pending.first_delta_at = now
        elif etype == "message_delta":
            delta = event.get("delta") or {}
            if delta.get("stop_reason"):
                pending.stop_reason = str(delta["stop_reason"])
            usage = event.get("usage") or {}
            out = _int_or_none(usage.get("output_tokens"))
            if out is not None:
                pending.output_tokens = out
        elif etype == "message_stop":
            pending.stopped_at = now
        return False

    def on_assistant(self, message: object) -> None:
        pending = self._pending
        message_id = getattr(message, "message_id", None)
        if pending is None or (
            message_id and pending.message_id and message_id != pending.message_id
        ):
            self.finalize()
            pending = _Pending(
                index=len(self.records) + 1,
                message_id=message_id,
                started_at=time.perf_counter(),
            )
            self._pending = pending
        if pending.message_id is None:
            pending.message_id = message_id
        pending.model = pending.model or getattr(message, "model", None)
        stop = getattr(message, "stop_reason", None)
        if stop:
            pending.stop_reason = str(stop)
        usage = getattr(message, "usage", None) or {}
        if isinstance(usage, dict):
            out = _int_or_none(usage.get("output_tokens"))
            if out is not None and (
                pending.output_tokens is None or out > pending.output_tokens
            ):
                pending.output_tokens = out
            if pending.input_tokens is None:
                pending.input_tokens = _int_or_none(usage.get("input_tokens"))
        for block in getattr(message, "content", None) or []:
            rec = _block_record(block)
            if rec is None:
                continue
            key, record = rec
            if key is not None:
                if key in pending.block_ids:
                    continue
                pending.block_ids.add(key)
            pending.blocks.append(record)

    def finalize(self) -> dict[str, Any] | None:
        pending = self._pending
        self._pending = None
        if pending is None:
            return None
        end = pending.stopped_at or time.perf_counter()
        thinking_chars = sum(
            b.get("chars", 0) for b in pending.blocks if b["type"] == "thinking"
        )
        text_chars = sum(b.get("chars", 0) for b in pending.blocks if b["type"] == "text")
        tools = [b["name"] for b in pending.blocks if b["type"] == "tool_use"]
        record: dict[str, Any] = {
            "response": pending.index,
            "message_id": pending.message_id,
            "model": pending.model,
            "duration_s": round(end - pending.started_at, 3),
            "ttft_s": (
                round(pending.first_delta_at - pending.started_at, 3)
                if pending.first_delta_at is not None
                else None
            ),
            "input_tokens": pending.input_tokens,
            "cache_read_tokens": pending.cache_read_tokens,
            "cache_creation_tokens": pending.cache_creation_tokens,
            "output_tokens": pending.output_tokens,
            "stop_reason": pending.stop_reason,
            "thinking_chars": thinking_chars,
            "text_chars": text_chars,
            "tool_calls": tools,
            "blocks": pending.blocks,
        }
        self.records.append(record)
        self._write(record)
        logger.info("%s", self.line(record))
        return record

    def _write(self, record: dict[str, Any]) -> None:
        if self.path is None:
            return
        try:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, default=str) + "\n")
        except OSError as exc:
            logger.warning("failed to write %s: %s", self.path, exc)

    @staticmethod
    def line(record: dict[str, Any]) -> str:
        bits = [f"response {record['response']}: {record['duration_s']:.1f}s"]
        if record.get("ttft_s") is not None:
            bits.append(f"(ttft {record['ttft_s']:.1f}s)")
        if record.get("output_tokens") is not None:
            bits.append(f"out={record['output_tokens']}tok")
        if record.get("input_tokens") is not None:
            cached = record.get("cache_read_tokens") or 0
            bits.append(f"in={record['input_tokens']}+{cached}cached")
        bits.append(f"thinking={record['thinking_chars']}ch")
        bits.append(f"text={record['text_chars']}ch")
        tools = record.get("tool_calls") or []
        if tools:
            short = [t.removeprefix("mcp__cover__") for t in tools]
            bits.append(f"tools={','.join(short)}")
        if record.get("stop_reason"):
            bits.append(f"stop={record['stop_reason']}")
        return " ".join(bits)

    def summary(self) -> dict[str, Any]:
        recs = self.records
        if not recs:
            return {"responses": 0}
        durations = [r["duration_s"] for r in recs]
        out_tokens = [r["output_tokens"] for r in recs if r["output_tokens"] is not None]
        slowest = max(recs, key=lambda r: r["duration_s"])
        return {
            "responses": len(recs),
            "total_s": round(sum(durations), 1),
            "mean_s": round(sum(durations) / len(durations), 1),
            "max_s": round(slowest["duration_s"], 1),
            "slowest_response": slowest["response"],
            "output_tokens": sum(out_tokens) if out_tokens else None,
            "thinking_chars": sum(r["thinking_chars"] for r in recs),
            "text_chars": sum(r["text_chars"] for r in recs),
            "responses_with_tools": sum(1 for r in recs if r["tool_calls"]),
        }
