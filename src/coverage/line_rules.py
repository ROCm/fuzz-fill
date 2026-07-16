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


def fully_covered_line_keys_from_address_map(
    llc_address_line_map: pd.DataFrame,
    covered_addresses: set[str],
    *,
    point_column: str = "point",
) -> set[tuple[str, int]]:
    """``(file, line)`` pairs where every mapped point on the line is in *covered_addresses*."""
    m = llc_address_line_map.copy()
    m["line"] = m["line"].astype(int)
    m["covered"] = m[point_column].isin(covered_addresses).astype(int)
    return Sancov.full_line_keys(m, covered_column="covered")
