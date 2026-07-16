"""Shared loader for the baseline ``line_coverage_summary.csv``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_REQUIRED_COLUMNS = ("file", "line", "coverage")


def load_line_coverage_summary(
    path: Path,
) -> tuple[dict[tuple[str, int], str], frozenset[tuple[str, int]]]:
    """Load the baseline summary CSV written by ``coverage baseline``.

    Args:
        path: ``line_coverage_summary.csv`` (columns ``file``, ``line``, ``coverage``
            with values ``covered`` | ``partially`` | ``uncovered``).

    Returns:
        coverage_by_line: ``(file, line)`` -> ``"covered"`` | ``"partially"`` | ``"uncovered"``.
        baseline_uncovered: keys where ``coverage == "uncovered"``.
    """
    if not path.is_file():
        raise SystemExit(
            f"Missing {path}. Run ``coverage baseline`` first (or pass the same "
            f"--output-dir you used for that run)."
        )
    summary = pd.read_csv(path)
    missing = set(_REQUIRED_COLUMNS) - set(summary.columns)
    if missing:
        raise SystemExit(
            f"{path}: expected columns {sorted(_REQUIRED_COLUMNS)}, got {list(summary.columns)!r}"
        )
    summary["line"] = summary["line"].astype(int)

    coverage_by_line: dict[tuple[str, int], str] = {
        (row.file, int(row.line)): row.coverage
        for row in summary.itertuples(index=False)
    }
    baseline_uncovered = frozenset(
        key for key, coverage in coverage_by_line.items() if coverage == "uncovered"
    )
    return coverage_by_line, baseline_uncovered
