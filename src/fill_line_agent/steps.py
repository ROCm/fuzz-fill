# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Timed step tracking for fill-line progress."""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from fuzz_fill.log import get_logger

logger = get_logger("fill_line_agent")


@dataclass
class StepRecord:
    name: str
    seconds: float
    detail: str = ""


@dataclass
class StepTracker:
    """Record named steps with wall time; log start/finish to stderr."""

    steps: list[StepRecord] = field(default_factory=list)

    @contextmanager
    def step(self, name: str, detail: str = "") -> Iterator[None]:
        suffix = f" ({detail})" if detail else ""
        logger.info("step start: %s%s", name, suffix)
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.steps.append(StepRecord(name=name, seconds=elapsed, detail=detail))
            logger.info("step done:  %s%s in %.2fs", name, suffix, elapsed)

    def note(self, message: str) -> None:
        logger.info("%s", message)

    def as_dicts(self) -> list[dict[str, object]]:
        return [
            {
                "step": s.name,
                "seconds": round(s.seconds, 3),
                **({"detail": s.detail} if s.detail else {}),
            }
            for s in self.steps
        ]
