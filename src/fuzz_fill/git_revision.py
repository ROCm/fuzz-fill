"""Record and compare the LLVM revision a pipeline stage was run against.

``coverage baseline`` and ``added_lines`` drop a ``COMMIT`` file next to their
CSV outputs holding the full revision they used. ``coverage target-lines`` reads
those files back and refuses to mix artifacts from different revisions.
"""

from __future__ import annotations

from pathlib import Path

from fuzz_fill.log import get_logger, run_subprocess

logger = get_logger("fuzz_fill.git_revision")

_COMMIT_FILENAME = "COMMIT"


def commit_file_path(directory: Path) -> Path:
    """Path of the recorded-revision file inside ``directory``."""
    return directory / _COMMIT_FILENAME


def resolve_revision(repo: Path, rev: str = "HEAD") -> str | None:
    """Full hash of ``rev`` in ``repo``, or ``None`` when it cannot be resolved."""
    r = run_subprocess(
        logger,
        ["git", "-C", str(repo), "rev-parse", "--verify", f"{rev}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return None
    return r.stdout.strip() or None


def write_commit_file(directory: Path, revision: str) -> Path:
    """Write ``revision`` to ``<directory>/COMMIT`` and return that path."""
    path = commit_file_path(directory)
    path.write_text(revision + "\n", encoding="utf-8")
    return path


def read_commit_file(directory: Path) -> str | None:
    """Revision recorded in ``<directory>/COMMIT``, or ``None`` when absent."""
    try:
        revision = commit_file_path(directory).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return revision or None
