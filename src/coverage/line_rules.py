"""Shared line-level coverage helpers for candidate-test address maps."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from coverage.pr_llc_settings import normalize_llvm_rel_path
from coverage.sancov import Sancov


def match_symcov_file(rel_path: str, summary_files: set[str]) -> str | None:
    """Map a git-relative path to an absolute path string present in *summary_files*."""
    rel_path = normalize_llvm_rel_path(rel_path)
    rel_parts = Path(rel_path).as_posix().split("/")
    n = len(rel_parts)
    for abs_file in summary_files:
        parts = Path(abs_file).as_posix().split("/")
        if len(parts) >= n and parts[-n:] == rel_parts:
            return abs_file
    return None


def normalize_llc_address_line_map(llc_address_line_map: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with int ``line`` and normalized ``point`` values."""
    m = llc_address_line_map.copy()
    m["line"] = m["line"].astype(int)
    m["point"] = m["point"].map(
        lambda x: Sancov.format_hex_address(x) if pd.notna(x) else x
    )
    return m


def gap_address_line_map(
    llc_address_line_map: pd.DataFrame,
    baseline_uncovered: frozenset[tuple[str, int]],
) -> pd.DataFrame:
    """Return address-map rows whose ``(file, line)`` is ``uncovered`` in the baseline summary."""
    if not baseline_uncovered:
        return llc_address_line_map.iloc[0:0].copy()
    uncovered_keys = pd.DataFrame(list(baseline_uncovered), columns=["file", "line"])
    uncovered_keys["line"] = uncovered_keys["line"].astype(int)
    return llc_address_line_map.merge(uncovered_keys, on=["file", "line"])


def filter_uncovered_lines(
    baseline_uncovered: frozenset[tuple[str, int]],
    source_filter: str,
) -> frozenset[tuple[str, int]]:
    """Keep only ``(file, line)`` pairs whose file path matches *source_filter* regex."""
    if not source_filter:
        return baseline_uncovered
    try:
        pattern = re.compile(source_filter)
    except re.error as exc:
        raise ValueError(f"invalid source filter regex: {source_filter!r}") from exc
    return frozenset(
        (file, line) for file, line in baseline_uncovered if pattern.search(file)
    )
