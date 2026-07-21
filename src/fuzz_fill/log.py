from __future__ import annotations

import argparse
import csv
import logging
import subprocess
import sys
import threading
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

DEFAULT_LOG_FILENAME = "fuzz_fill.log"
_LOG_FORMAT = "%(levelname)s [%(name)s] %(message)s"

_LOG_LEVELS = {
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}

_timings_lock = threading.Lock()
_active_timings: list[tuple[str, float]] | None = None


def resolve_log_file(output_dir: Path, log_to_file: bool) -> Path | None:
    if not log_to_file:
        return None
    return output_dir / DEFAULT_LOG_FILENAME


def configure_logging(level: str, *, log_file: Path | None = None) -> None:
    """Configure fuzz-fill logging to stderr and optionally to a log file."""
    numeric_level = _LOG_LEVELS[level.lower()]
    formatter = logging.Formatter(_LOG_FORMAT)

    root = logging.getLogger("fuzz_fill")
    root.handlers.clear()

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

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


def add_log_to_file_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--log-to-file",
        action="store_true",
        help=(
            f"Also write log messages to <output-dir>/{DEFAULT_LOG_FILENAME} "
            "(same --log-level as the terminal)."
        ),
    )


# ``log_timing`` logs elapsed wall time. Wrap a block in ``record_log_timings`` when
# nested ``log_timing`` rows should also be exported (see ``write_timings_csv``).


@contextmanager
def record_log_timings() -> Iterator[list[tuple[str, float]]]:
    """Enable CSV export for nested ``log_timing`` blocks.

    This does not measure time itself; it collects ``(label, elapsed_seconds)`` rows
    that ``log_timing`` appends while this context is active.
    """
    global _active_timings
    rows: list[tuple[str, float]] = []
    with _timings_lock:
        _active_timings = rows
    try:
        yield rows
    finally:
        with _timings_lock:
            _active_timings = None


def write_timings_csv(path: Path, rows: Sequence[tuple[str, float]]) -> None:
    """Write rows collected by ``record_log_timings`` to a CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["step", "seconds"])
        for label, elapsed in rows:
            writer.writerow([label, f"{elapsed:.3f}"])


@contextmanager
def log_timing(
    logger: logging.Logger,
    label: str,
    *,
    level: int = logging.INFO,
) -> Iterator[None]:
    """Log elapsed wall time for a block of work.

    When called inside ``record_log_timings()``, also append the elapsed time to
    the collected rows for CSV export.
    """
    logger.log(level, "%s: starting", label)
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.log(level, "%s finished in %.2fs", label, elapsed)
        with _timings_lock:
            if _active_timings is not None:
                _active_timings.append((label, elapsed))


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
