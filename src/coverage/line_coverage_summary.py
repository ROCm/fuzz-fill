"""Shared loader for baseline line coverage CSVs."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

from coverage.constants import (
    DEFAULT_LINE_COVERAGE_COVERED_FILE,
    DEFAULT_LINE_COVERAGE_PARTIALLY_FILE,
    DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
    DEFAULT_LINE_COVERAGE_UNCOVERED_FILE,
)

_REQUIRED_COLUMNS = ("file", "line", "coverage")
_SPLIT_COLUMNS = ("file", "line")
_COVERAGE_STATUSES = ("covered", "partially", "uncovered")
_SPLIT_FILES_BY_STATUS = {
    "covered": DEFAULT_LINE_COVERAGE_COVERED_FILE,
    "partially": DEFAULT_LINE_COVERAGE_PARTIALLY_FILE,
    "uncovered": DEFAULT_LINE_COVERAGE_UNCOVERED_FILE,
}


def _missing_baseline_error(baseline_output_dir: Path, detail: str) -> SystemExit:
    return SystemExit(
        f"Missing baseline coverage under {baseline_output_dir}. "
        f"{detail} Run ``coverage baseline`` first (or pass the same "
        f"--output-dir you used for that run)."
    )


def _load_split_line_keys(path: Path) -> frozenset[tuple[str, int]]:
    if not path.is_file():
        raise _missing_baseline_error(
            path.parent,
            f"Expected {path.name}.",
        )
    frame = pd.read_csv(path)
    missing = set(_SPLIT_COLUMNS) - set(frame.columns)
    if missing:
        raise SystemExit(
            f"{path}: expected columns {sorted(_SPLIT_COLUMNS)}, got {list(frame.columns)!r}"
        )
    if frame.empty:
        return frozenset()
    frame["line"] = frame["line"].astype(int)
    return frozenset((row.file, int(row.line)) for row in frame.itertuples(index=False))


def _split_files_available(baseline_output_dir: Path) -> bool:
    return all(
        (baseline_output_dir / filename).is_file()
        for filename in _SPLIT_FILES_BY_STATUS.values()
    )


def load_baseline_uncovered_lines(baseline_output_dir: Path) -> frozenset[tuple[str, int]]:
    """Load baseline lines with ``coverage == "uncovered"``.

    Prefers ``line_coverage_uncovered.csv`` when present; otherwise filters
    ``line_coverage_summary.csv``.
    """
    split_path = baseline_output_dir / DEFAULT_LINE_COVERAGE_UNCOVERED_FILE
    if split_path.is_file():
        return _load_split_line_keys(split_path)

    summary_path = baseline_output_dir / DEFAULT_LINE_COVERAGE_SUMMARY_FILE
    _, baseline_uncovered = load_line_coverage_summary(summary_path)
    return baseline_uncovered


def load_coverage_by_line(baseline_output_dir: Path) -> dict[tuple[str, int], str]:
    """Load per-line coverage status from baseline output.

    Prefers the three per-status split CSVs when all are present; otherwise
    reads ``line_coverage_summary.csv``.
    """
    if _split_files_available(baseline_output_dir):
        coverage_by_line: dict[tuple[str, int], str] = {}
        for status in _COVERAGE_STATUSES:
            split_path = baseline_output_dir / _SPLIT_FILES_BY_STATUS[status]
            for file, line in _load_split_line_keys(split_path):
                coverage_by_line[(file, line)] = status
        return coverage_by_line

    summary_path = baseline_output_dir / DEFAULT_LINE_COVERAGE_SUMMARY_FILE
    coverage_by_line, _ = load_line_coverage_summary(summary_path)
    return coverage_by_line


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


def write_line_coverage_summary_splits(
    coverage: pd.DataFrame,
    output_dir: Path,
) -> dict[Literal["covered", "partially", "uncovered"], Path]:
    """Write per-status views of ``line_coverage_summary.csv``.

    Produces three CSVs with columns ``file`` and ``line`` only (status is
    implied by the filename), each containing rows for one coverage class.
    """
    missing = set(_REQUIRED_COLUMNS) - set(coverage.columns)
    if missing:
        raise ValueError(
            f"coverage summary missing columns {sorted(missing)}; "
            f"expected {sorted(_REQUIRED_COLUMNS)}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    filenames = {
        "covered": DEFAULT_LINE_COVERAGE_COVERED_FILE,
        "partially": DEFAULT_LINE_COVERAGE_PARTIALLY_FILE,
        "uncovered": DEFAULT_LINE_COVERAGE_UNCOVERED_FILE,
    }
    paths: dict[Literal["covered", "partially", "uncovered"], Path] = {}
    for status in _COVERAGE_STATUSES:
        subset = coverage.loc[coverage["coverage"] == status, list(_SPLIT_COLUMNS)]
        path = output_dir / filenames[status]
        subset.to_csv(path, index=False)
        paths[status] = path
    return paths
