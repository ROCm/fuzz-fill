"""Shared line-level coverage helpers for candidate-test address maps."""

from __future__ import annotations

import pandas as pd

from coverage.sancov import Sancov


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
    """Keep only ``(file, line)`` pairs whose file path contains *source_filter*."""
    if not source_filter:
        return baseline_uncovered
    return frozenset(
        (file, line) for file, line in baseline_uncovered if source_filter in file
    )
