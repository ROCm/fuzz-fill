"""Load deduplicated llc address ids from joint coverage CSV (``llc_addresses`` column)."""

from __future__ import annotations

import csv
import json
from pathlib import Path


def source_path_has_prefix(path_str: str, prefix: str) -> bool:
    """
    True if ``path_str`` is the prefix path or lies under it (POSIX, after expanduser).

    Used to drop baseline / symcov rows early before building large sets.
    """
    p = Path(path_str).expanduser().as_posix()
    base = Path(prefix).expanduser().as_posix().rstrip("/")
    return p == base or p.startswith(base + "/")


def normalize_llc_address_for_compare(addr: str) -> str:
    """
    Canonical form for set comparisons between ``sancov --print`` lines and CSV JSON ids.

    Strips whitespace, removes a leading ``0x`` / ``0X``, lowercases hex.
    """
    t = addr.strip()
    if t.lower().startswith("0x"):
        t = t[2:]
    return t.lower()


def load_baseline_llc_addresses_from_csv(
    csv_path: Path,
    *,
    source_path_prefix: str | None = None,
) -> set[str]:
    """
    Read ``file,function,line,llc_addresses`` CSV; parse each ``llc_addresses`` cell as JSON
    array of strings; return a deduplicated set of **normalized** address ids.

    With ``source_path_prefix``, skip rows whose ``file`` path is not under that prefix (no
    ``json.loads`` for those rows).
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
        cf: str | None = None
        if source_path_prefix is not None:
            cf = by_lower.get("file")
            if cf is None:
                raise ValueError(
                    "--source-path-prefix requires a 'file' column in the baseline CSV "
                    f"(got {list(reader.fieldnames)!r})"
                )
        for row in reader:
            if cf is not None:
                file_s = (row.get(cf) or "").strip()
                if not file_s or not source_path_has_prefix(file_s, source_path_prefix):
                    continue
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


def load_baseline_llc_addresses_by_source_line(
    csv_path: Path,
    *,
    source_path_prefix: str | None = None,
) -> dict[tuple[str, str, int], frozenset[str]]:
    """
    Same CSV as :func:`load_baseline_llc_addresses_from_csv`, keyed by ``(file, function, line)``.

    Rows with duplicate keys merge address sets. Line numbers are integers; file/function strings
    are stripped from the CSV.

    With ``source_path_prefix``, skip rows whose ``file`` is not under that prefix before
    parsing ``llc_addresses``.
    """
    buckets: dict[tuple[str, str, int], set[str]] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header row: {csv_path}")
        by_lower = {
            (name or "").strip().lower(): name for name in reader.fieldnames if name
        }
        for key in ("file", "function", "line", "llc_addresses"):
            if key not in by_lower:
                raise ValueError(
                    f"CSV must include {key!r} column (got {list(reader.fieldnames)!r})"
                )
        cf = by_lower["file"]
        cfn = by_lower["function"]
        cln = by_lower["line"]
        caddr = by_lower["llc_addresses"]
        for row in reader:
            file_s = (row.get(cf) or "").strip()
            if source_path_prefix is not None and (
                not file_s or not source_path_has_prefix(file_s, source_path_prefix)
            ):
                continue
            func_s = (row.get(cfn) or "").strip()
            line_s = (row.get(cln) or "").strip()
            cell = (row.get(caddr) or "").strip()
            if not file_s or not func_s or not line_s or not cell or cell == "[]":
                continue
            try:
                line_num = int(line_s)
            except ValueError:
                continue
            try:
                parsed = json.loads(cell)
            except json.JSONDecodeError:
                continue
            if not isinstance(parsed, list):
                continue
            loc_key = (file_s, func_s, line_num)
            acc = buckets.setdefault(loc_key, set())
            for item in parsed:
                if isinstance(item, str) and item.strip():
                    acc.add(normalize_llc_address_for_compare(item))
    return {k: frozenset(v) for k, v in buckets.items()}


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


def load_llc_line_address_map_rows(
    map_path: Path,
    *,
    source_path_prefix: str | None = None,
) -> list[tuple[str, str, int, frozenset[str]]]:
    """
    Load ``*.point_symbol_info.json`` (or any symcov-shaped JSON with ``point-symbol-info``)
    produced by ``symcov-line-map`` / per-test symbolize extract.

    With ``source_path_prefix``, drop non-matching top-level file paths from ``point-symbol-info``
    immediately after JSON parse (before building line rows).
    """
    from coverage.map import line_address_map_rows_from_symcov

    path = Path(map_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(
            f"line map JSON must be an object, got {type(data).__name__}: {path}"
        )
    if source_path_prefix is not None:
        data = _filter_point_symbol_info_files(data, source_path_prefix)
    rows = line_address_map_rows_from_symcov(data)
    out: list[tuple[str, str, int, frozenset[str]]] = []
    for r in rows:
        addrs = r.get("llc_addresses")
        if not isinstance(addrs, list) or not addrs:
            continue
        norm = frozenset(
            normalize_llc_address_for_compare(x)
            for x in addrs
            if isinstance(x, str) and x.strip()
        )
        if not norm:
            continue
        out.append(
            (
                str(r["file"]),
                str(r["function"]),
                int(r["line"]),
                norm,
            )
        )
    return out


def _filter_point_symbol_info_files(
    data: dict[str, object], source_path_prefix: str
) -> dict[str, object]:
    out = dict(data)
    for key in ("point-symbol-info", "point_symbol_info"):
        psi = out.get(key)
        if not isinstance(psi, dict):
            continue
        out[key] = {
            fp: v
            for fp, v in psi.items()
            if isinstance(fp, str) and source_path_has_prefix(fp, source_path_prefix)
        }
    return out


def novel_source_lines_vs_baseline(
    line_map_rows: list[tuple[str, str, int, frozenset[str]]],
    baseline_by_line: dict[tuple[str, str, int], frozenset[str]],
    test_norm: set[str],
) -> list[tuple[str, str, int]]:
    """
    Lines where **no** instrumentation id for that ``(file, function, line)`` appears in the
    baseline row for that same location, but **at least one** id for that line appears in
    ``test_norm``.

    If the baseline CSV has no row for that location, the baseline address set for that line is
    treated as empty.
    """
    flagged: list[tuple[str, str, int]] = []
    for file_s, func_s, line_num, addrs in line_map_rows:
        if not addrs:
            continue
        base_line = baseline_by_line.get((file_s, func_s, line_num), frozenset())
        if addrs & base_line:
            continue
        if addrs & test_norm:
            flagged.append((file_s, func_s, line_num))
    return sorted(flagged)
