from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TextIO

DEFAULT_LOG_FILENAME = "fuzz_fill.log"

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


def add_log_to_file_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--log-to-file",
        action="store_true",
        help=f"Also write stdout/stderr to <output-dir>/{DEFAULT_LOG_FILENAME}.",
    )


class _Tee(TextIO):
    """Write to a terminal stream and a log file."""

    def __init__(self, terminal: TextIO, log_file: TextIO) -> None:
        self._terminal = terminal
        self._log_file = log_file

    def write(self, data: str) -> int:
        self._terminal.write(data)
        self._log_file.write(data)
        return len(data)

    def flush(self) -> None:
        self._terminal.flush()
        self._log_file.flush()

    def fileno(self) -> int:
        return self._terminal.fileno()


_log_file_handle: TextIO | None = None
_original_stdout: TextIO | None = None
_original_stderr: TextIO | None = None


def enable_log_file(output_dir: Path) -> Path:
    """Tee stdout/stderr to output_dir/fuzz_fill.log. Call before configure_logging()."""
    global _log_file_handle, _original_stdout, _original_stderr

    if _log_file_handle is not None:
        raise RuntimeError("log file tee is already enabled")

    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / DEFAULT_LOG_FILENAME
    _log_file_handle = log_path.open("w", encoding="utf-8")
    _original_stdout = sys.stdout
    _original_stderr = sys.stderr
    sys.stdout = _Tee(_original_stdout, _log_file_handle)
    sys.stderr = _Tee(_original_stderr, _log_file_handle)
    return log_path


def disable_log_file() -> None:
    """Restore original stdout/stderr and close the log file."""
    global _log_file_handle, _original_stdout, _original_stderr

    if _log_file_handle is None:
        return

    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
    _log_file_handle.close()
    _log_file_handle = None
    _original_stdout = None
    _original_stderr = None


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
