"""Shared line-level coverage classification rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from coverage.sancov import Sancov

LineCoverageClass = Literal["full", "partial", "none", "not_instrumented"]


@dataclass(frozen=True)
class LineCoverageIndex:
    """Baseline suite coverage keyed by ``(symcov_file, line)``."""

    instrumented: frozenset[tuple[str, int]]
    full: frozenset[tuple[str, int]]
    none: frozenset[tuple[str, int]]
    partial: frozenset[tuple[str, int]]
    point_addresses: dict[tuple[str, int], list[str]]

    @classmethod
    def from_summary_df(cls, summary: pd.DataFrame) -> LineCoverageIndex:
        df = summary.copy()
        df["line"] = df["line"].astype(int)

        instrumented = frozenset(zip(df["file"], df["line"]))
        full = frozenset(
            zip(
                df.loc[df["coverage"] == "full", "file"],
                df.loc[df["coverage"] == "full", "line"],
            )
        )
        none = frozenset(
            zip(
                df.loc[df["coverage"] == "none", "file"],
                df.loc[df["coverage"] == "none", "line"],
            )
        )
        partial = frozenset(
            zip(
                df.loc[df["coverage"] == "partial", "file"],
                df.loc[df["coverage"] == "partial", "line"],
            )
        )

        point_addresses: dict[tuple[str, int], list[str]] = {}
        for row in df.loc[df["coverage"] == "none"].itertuples(index=False):
            addrs = [a for a in str(row.point_addresses).split(";") if a]
            point_addresses[(row.file, int(row.line))] = addrs

        return cls(
            instrumented=instrumented,
            full=full,
            none=none,
            partial=partial,
            point_addresses=point_addresses,
        )

    def classify(self, file: str, line: int) -> LineCoverageClass:
        key = (file, line)
        if key not in self.instrumented:
            return "not_instrumented"
        if key in self.full:
            return "full"
        if key in self.none:
            return "none"
        return "partial"

    def is_baseline_gap(self, file: str, line: int) -> bool:
        return (file, line) in self.none


def normalize_llc_address_line_map(llc_address_line_map: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with int ``line`` and normalized ``point_llc`` values."""
    m = llc_address_line_map.copy()
    m["line"] = m["line"].astype(int)
    m["point_llc"] = m["point_llc"].map(
        lambda x: Sancov.format_hex_address(x) if pd.notna(x) else x
    )
    return m


def fully_covered_line_keys_from_address_map(
    llc_address_line_map: pd.DataFrame,
    covered_addresses: set[str],
    *,
    point_column: str = "point_llc",
) -> set[tuple[str, int]]:
    """``(file, line)`` pairs where every mapped point on the line is in *covered_addresses*."""
    m = llc_address_line_map.copy()
    m["line"] = m["line"].astype(int)
    m["covered"] = m[point_column].isin(covered_addresses).astype(int)
    return Sancov.full_line_keys(m, covered_column="covered")
