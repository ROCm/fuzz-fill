from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

_LOG_LEVELS = {
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


def configure_logging(level: str) -> None:
    """Configure root fuzz-fill logging to stderr."""
    numeric_level = _LOG_LEVELS[level.lower()]
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
    root = logging.getLogger("fuzz_fill")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"fuzz_fill.{name}")


def add_log_level_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--log-level",
        default="info",
        choices=sorted(_LOG_LEVELS),
        help="Logging verbosity (default: info).",
    )


@contextmanager
def log_timing(
    logger: logging.Logger,
    label: str,
    *,
    level: int = logging.INFO,
) -> Iterator[None]:
    """Log elapsed wall time for a block of work."""
    logger.log(level, "%s: starting", label)
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.log(level, "%s finished in %.2fs", label, elapsed)


def run_subprocess(
    logger: logging.Logger,
    cmd: Sequence[str],
    *,
    label: str | None = None,
    level: int = logging.DEBUG,
    **kwargs: Any,
) -> subprocess.CompletedProcess[Any]:
    """Run a subprocess, logging argv/cwd at DEBUG and duration on completion."""
    cwd = kwargs.get("cwd")
    logger.debug("running %s", list(cmd))
    if cwd is not None:
        logger.debug("cwd: %s", cwd)

    start = time.perf_counter()
    try:
        return subprocess.run(cmd, **kwargs)
    finally:
        elapsed = time.perf_counter() - start
        name = label or " ".join(cmd[:2])
        if label is not None:
            logger.info("%s finished in %.2fs", name, elapsed)
        else:
            logger.log(level, "%s finished in %.2fs", name, elapsed)
