"""Parse gap-fill ``new_coverage.csv`` rows and source paths."""

from __future__ import annotations

import csv
from pathlib import Path

NEW_COVERAGE_COLUMNS = frozenset({"test_name", "file", "line", "covered-points"})


def llvm_rel_source_path(abs_path: str) -> str:
    """Path under llvm/... as used in fuzz-fill config.json."""
    norm = abs_path.replace("\\", "/")
    for needle in ("llvm/lib/", "llvm/include/", "llvm/utils/", "llvm/tools/"):
        i = norm.find(needle)
        if i >= 0:
            return norm[i:]
    raise ValueError(f"Could not derive llvm-relative path from: {abs_path!r}")


def parse_covered_points_field(value: str) -> list[str]:
    """Split ``covered-points`` cell into hex strings without 0x prefix."""
    if not value or not value.strip():
        return []
    out: list[str] = []
    for part in value.split(";"):
        p = part.strip()
        if not p:
            continue
        if p.lower().startswith("0x"):
            p = p[2:]
        out.append(p)
    return out


def resolve_covered_hexes(covered_points_cell: str) -> tuple[str, list[str]]:
    """Return (COVERED value with 0x prefix, sorted hex-without-0x list for logging)."""
    hexes = parse_covered_points_field(covered_points_cell)
    if not hexes:
        raise ValueError("covered-points is empty or has no valid hex values")
    hexes_sorted = sorted(hexes, key=lambda h: int(h, 16))
    return "0x" + hexes_sorted[0], hexes_sorted


def load_new_coverage_rows(csv_path: Path, *, limit: int | None = None) -> list[dict[str, str]]:
    """Load and validate rows from a gap-fill ``new_coverage.csv``."""
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or set(reader.fieldnames) != NEW_COVERAGE_COLUMNS:
            raise ValueError(
                f"CSV must have columns {sorted(NEW_COVERAGE_COLUMNS)}, "
                f"got {reader.fieldnames!r}"
            )
        rows = list(reader)
    if limit is not None:
        return rows[:limit]
    return rows
