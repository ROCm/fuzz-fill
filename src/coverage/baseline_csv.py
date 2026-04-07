"""Load deduplicated llc address ids from joint coverage CSV (``llc_addresses`` column)."""

from __future__ import annotations

import csv
import json
from pathlib import Path


def normalize_llc_address_for_compare(addr: str) -> str:
    """
    Canonical form for set comparisons between ``sancov --print`` lines and CSV JSON ids.

    Strips whitespace, removes a leading ``0x`` / ``0X``, lowercases hex.
    """
    t = addr.strip()
    if t.lower().startswith("0x"):
        t = t[2:]
    return t.lower()


def load_baseline_llc_addresses_from_csv(csv_path: Path) -> set[str]:
    """
    Read ``file,function,line,llc_addresses`` CSV; parse each ``llc_addresses`` cell as JSON
    array of strings; return a deduplicated set of **normalized** address ids.
    """
    out: set[str] = set()
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header row: {csv_path}")
        by_lower = {
            (name or "").strip().lower(): name for name in reader.fieldnames if name
        }
        col = by_lower.get("llc_addresses")
        if col is None:
            raise ValueError(
                f"CSV must include an 'llc_addresses' column (got {list(reader.fieldnames)!r})"
            )
        for row in reader:
            cell = (row.get(col) or "").strip()
            if not cell or cell == "[]":
                continue
            try:
                parsed = json.loads(cell)
            except json.JSONDecodeError:
                continue
            if not isinstance(parsed, list):
                continue
            for item in parsed:
                if isinstance(item, str) and item.strip():
                    out.add(normalize_llc_address_for_compare(item))
    return out


def addresses_in_test_not_in_baseline(
    test_addresses_from_print: set[str],
    baseline_normalized: set[str],
) -> list[str]:
    """
    ``sancov --print`` strings that are not in the baseline when compared by
    :func:`normalize_llc_address_for_compare`. Sorted for stable output; one representative
    string per normalized id.
    """
    seen_norm: set[str] = set()
    result: list[str] = []
    for a in sorted(test_addresses_from_print):
        n = normalize_llc_address_for_compare(a)
        if n in baseline_normalized or n in seen_norm:
            continue
        seen_norm.add(n)
        result.append(a)
    return result
