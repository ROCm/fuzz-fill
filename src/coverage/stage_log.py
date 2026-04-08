"""Bracketed stage tags on log lines for long mixed streams."""

from __future__ import annotations

import sys
from typing import TextIO


def stage_line(
    stage: str,
    message: str = "",
    *,
    file: TextIO | None = None,
) -> None:
    """Print ``[stage]`` before each line of ``message`` (or ``[stage]`` alone if empty)."""
    out = sys.stdout if file is None else file
    if not message:
        print(f"[{stage}]", file=out, flush=True)
        return
    for line in message.splitlines():
        print(f"[{stage}] {line}", file=out, flush=True)
