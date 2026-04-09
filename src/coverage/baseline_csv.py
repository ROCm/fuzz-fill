"""
Joint coverage CSV and line maps as pandas DataFrames (``pd.read_csv``, merges, groupby).

Public load/compare helpers return DataFrames with documented columns—no tuple-of-frozenset
representations in the API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, NamedTuple

import pandas as pd


class NovelLineMapPrecompute(NamedTuple):
    """Cached tables for :func:`novel_source_lines_vs_baseline` (same for every test input)."""

    lm_u: pd.DataFrame
    overlap_line_keys: pd.DataFrame
    line_n_addrs: pd.DataFrame


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


def _empty_addr_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["addr"])


def _empty_raw_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["raw"])


def _empty_loc_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["file", "function", "line"])


def _parse_llc_address_cell(cell: object) -> list[str]:
    cell_s = (str(cell) if cell is not None else "").strip()
    if not cell_s or cell_s == "[]":
        return []
    try:
        parsed = json.loads(cell_s)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [
        normalize_llc_address_for_compare(x)
        for x in parsed
        if isinstance(x, str) and x.strip()
    ]


def read_baseline_joint_csv_long(
    csv_path: Path,
    *,
    source_path_prefix: str | None = None,
) -> pd.DataFrame:
    """
    Read joint baseline CSV into long form: columns ``file``, ``function``, ``line``, ``addr``.

    Each JSON element in ``llc_addresses`` becomes one row (normalized ``addr``).
    """
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    if df.empty:
        return pd.DataFrame(columns=["file", "function", "line", "addr"])
    df.columns = [str(c).strip().lower() for c in df.columns]
    for col in ("file", "function", "line", "llc_addresses"):
        if col not in df.columns:
            raise ValueError(
                f"CSV must include {col!r} column (got {list(df.columns)!r}): {csv_path}"
            )
    if source_path_prefix is not None:
        mask = df["file"].map(
            lambda f: bool(str(f).strip())
            and source_path_has_prefix(str(f).strip(), source_path_prefix)
        )
        df = df.loc[mask]
    df["_addrs"] = df["llc_addresses"].map(_parse_llc_address_cell)
    df = df.explode("_addrs", ignore_index=True)
    df = df.rename(columns={"_addrs": "addr"})
    df = df.dropna(subset=["addr"])
    df["addr"] = df["addr"].astype(str)
    df = df[df["addr"].str.len() > 0]
    df["line"] = pd.to_numeric(df["line"], errors="coerce")
    df = df.dropna(subset=["line"])
    df["line"] = df["line"].astype(int)
    df["file"] = df["file"].map(lambda s: str(s).strip())
    df["function"] = df["function"].map(lambda s: str(s).strip())
    df = df[(df["file"] != "") & (df["function"] != "")]
    return df[["file", "function", "line", "addr"]].drop_duplicates().reset_index(
        drop=True
    )


def load_baseline_llc_addresses_from_csv(
    csv_path: Path,
    *,
    source_path_prefix: str | None = None,
) -> pd.DataFrame:
    """
    Baseline as a deduplicated DataFrame: column ``addr`` (normalized instrumentation ids).
    """
    long_df = read_baseline_joint_csv_long(
        csv_path, source_path_prefix=source_path_prefix
    )
    if long_df.empty:
        return _empty_addr_df()
    return long_df[["addr"]].drop_duplicates().reset_index(drop=True)


def load_baseline_llc_addresses_by_source_line(
    csv_path: Path,
    *,
    source_path_prefix: str | None = None,
) -> pd.DataFrame:
    """
    Same CSV as :func:`load_baseline_llc_addresses_from_csv`, long form with
    ``file``, ``function``, ``line``, ``addr``.
    """
    return read_baseline_joint_csv_long(
        csv_path, source_path_prefix=source_path_prefix
    )


def test_hit_addresses_normalized_df(addr_strings: set[str]) -> pd.DataFrame:
    """One row per distinct normalized address from raw ``sancov --print`` lines."""
    if not addr_strings:
        return _empty_addr_df()
    s = pd.Series(sorted(addr_strings), dtype=object)
    out = pd.DataFrame({"addr": s.map(normalize_llc_address_for_compare)})
    return out.drop_duplicates(subset="addr").reset_index(drop=True)


def addresses_in_test_not_in_baseline(
    test_raw_df: pd.DataFrame,
    baseline_addr_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rows with columns ``raw`` (original print string) and ``norm``; one ``raw`` per distinct
    ``norm`` not present in ``baseline_addr_df['addr']``. ``test_raw_df`` must have column ``raw``.
    """
    if test_raw_df.empty:
        return pd.DataFrame(columns=["raw", "norm"])
    df = test_raw_df[["raw"]].copy()
    df["norm"] = df["raw"].map(normalize_llc_address_for_compare)
    if baseline_addr_df.empty or baseline_addr_df["addr"].empty:
        return df.drop_duplicates(subset="norm", keep="first").reset_index(drop=True)
    df = df.loc[~df["norm"].isin(baseline_addr_df["addr"])]
    return df.drop_duplicates(subset="norm", keep="first").reset_index(drop=True)


def load_llc_line_address_map_rows(
    map_path: Path,
    *,
    source_path_prefix: str | None = None,
) -> pd.DataFrame:
    """
    Load ``*.point_symbol_info.json`` into long form: ``file``, ``function``, ``line``, ``addr``.

    With ``source_path_prefix``, drop non-matching top-level file paths from ``point-symbol-info``
    before building rows.
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
    if not rows:
        return pd.DataFrame(columns=["file", "function", "line", "addr"])
    recs: list[tuple[str, str, int, str]] = []
    for r in rows:
        addrs = r.get("llc_addresses")
        if not isinstance(addrs, list) or not addrs:
            continue
        for x in addrs:
            if not isinstance(x, str) or not x.strip():
                continue
            recs.append(
                (
                    str(r["file"]),
                    str(r["function"]),
                    int(r["line"]),
                    normalize_llc_address_for_compare(x),
                )
            )
    if not recs:
        return pd.DataFrame(columns=["file", "function", "line", "addr"])
    out = pd.DataFrame(recs, columns=["file", "function", "line", "addr"])
    return out.drop_duplicates().reset_index(drop=True)


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


def build_novel_line_map_precompute(
    full_line_addr_map_df: pd.DataFrame,
    baseline_line_addr_df: pd.DataFrame,
) -> NovelLineMapPrecompute:
    """
    Build tables shared by every call to :func:`novel_source_lines_vs_baseline` for the same
    line map and baseline (avoids repeating the line-map × baseline merge per test).
    """
    cols = ["file", "function", "line", "addr"]
    if full_line_addr_map_df.empty or "addr" not in full_line_addr_map_df.columns:
        lm_u = pd.DataFrame(columns=cols)
        return NovelLineMapPrecompute(
            lm_u=lm_u,
            overlap_line_keys=_empty_loc_df(),
            line_n_addrs=pd.DataFrame(columns=["file", "function", "line", "n_addrs"]),
        )

    lm = full_line_addr_map_df[cols].copy()
    lm_u = lm.drop_duplicates(subset=["file", "function", "line", "addr"])
    line_n_addrs = (
        lm_u.groupby(["file", "function", "line"], as_index=False)
        .agg(n_addrs=("addr", "count"))
    )
    if baseline_line_addr_df.empty:
        overlap_line_keys = _empty_loc_df()
    else:
        base = baseline_line_addr_df[cols].copy()
        overlap = lm.merge(base, on=cols, how="inner")
        overlap_line_keys = (
            overlap[cols[:3]].drop_duplicates()
            if not overlap.empty
            else _empty_loc_df()
        )
    return NovelLineMapPrecompute(
        lm_u=lm_u,
        overlap_line_keys=overlap_line_keys,
        line_n_addrs=line_n_addrs,
    )


def _novel_lines_from_precompute(
    precompute: NovelLineMapPrecompute,
    new_test_line_addr_df: pd.DataFrame,
    coverage_level: Literal["partial", "full"],
) -> pd.DataFrame:
    if new_test_line_addr_df.empty or precompute.lm_u.empty:
        return _empty_loc_df()
    test_addrs = new_test_line_addr_df["addr"]
    hit_rows = precompute.lm_u.loc[precompute.lm_u["addr"].isin(test_addrs)]
    hit_summary = hit_rows.groupby(
        ["file", "function", "line"], as_index=False
    ).agg(n_hits=("addr", "count"))
    merged = precompute.line_n_addrs.merge(
        hit_summary,
        on=["file", "function", "line"],
        how="left",
    )
    merged["n_hits"] = merged["n_hits"].fillna(0).astype(int)
    if coverage_level == "partial":
        qualifying = merged.loc[merged["n_hits"] > 0, ["file", "function", "line"]]
    else:
        qualifying = merged.loc[
            (merged["n_addrs"] > 0) & (merged["n_hits"] == merged["n_addrs"]),
            ["file", "function", "line"],
        ]
    if qualifying.empty:
        return _empty_loc_df()
    out = qualifying.merge(
        precompute.overlap_line_keys,
        on=["file", "function", "line"],
        how="left",
        indicator=True,
    )
    novel = out.loc[out["_merge"] == "left_only", ["file", "function", "line"]]
    return novel.sort_values(["file", "function", "line"]).reset_index(drop=True)


def novel_source_lines_vs_baseline(
    full_line_addr_map_df: pd.DataFrame,
    baseline_line_addr_df: pd.DataFrame,
    new_test_line_addr_df: pd.DataFrame,
    *,
    coverage_level: Literal["partial", "full"] = "partial",
    precompute: NovelLineMapPrecompute | None = None,
) -> pd.DataFrame:
    """
    Lines (``file``, ``function``, ``line``) where no ``addr`` on that line appears in the
    baseline for that location, and the test satisfies ``coverage_level`` w.r.t. addresses
    listed for that line in ``full_line_addr_map_df``.

    ``coverage_level``:

    * ``partial`` (default): at least one map ``addr`` on the line is in
      ``new_test_line_addr_df``.
    * ``full``: every distinct map ``addr`` on the line is in ``new_test_line_addr_df``.

    Pass ``precompute`` from :func:`build_novel_line_map_precompute` when evaluating many tests
    against the same line map and baseline (e.g. ``coverage new-tests``); otherwise the
    precompute is built on each call.

    Missing baseline rows are treated as empty address sets.
    """
    if coverage_level not in ("partial", "full"):
        raise ValueError(
            f"coverage_level must be 'partial' or 'full', got {coverage_level!r}"
        )
    if (
        full_line_addr_map_df.empty
        or new_test_line_addr_df.empty
        or "addr" not in full_line_addr_map_df.columns
    ):
        return _empty_loc_df()

    pc = precompute or build_novel_line_map_precompute(
        full_line_addr_map_df, baseline_line_addr_df
    )
    return _novel_lines_from_precompute(pc, new_test_line_addr_df, coverage_level)


def normalized_addresses_missing_from_line_map(
    test_norm_df: pd.DataFrame,
    line_map_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rows of ``test_norm_df`` whose ``addr`` does not appear in ``line_map_df['addr']``.
    Sorted by ``addr``.
    """
    if test_norm_df.empty:
        return _empty_addr_df()
    if line_map_df.empty or "addr" not in line_map_df.columns:
        return test_norm_df.sort_values("addr").reset_index(drop=True)
    map_addrs = line_map_df["addr"]
    return (
        test_norm_df.loc[~test_norm_df["addr"].isin(map_addrs)]
        .sort_values("addr")
        .reset_index(drop=True)
    )


def norm_address_to_files_from_line_map_rows(
    line_map_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Long table ``addr``, ``file`` (deduplicated) for joins and prefix splits.
    """
    if line_map_df.empty:
        return pd.DataFrame(columns=["addr", "file"])
    return line_map_df[["addr", "file"]].drop_duplicates().reset_index(drop=True)


def split_novel_addresses_by_source_prefix(
    novel_raw_df: pd.DataFrame,
    addr_files_long_df: pd.DataFrame,
    source_path_prefix: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Partition ``novel_raw_df`` (column ``raw``) using mapped ``file`` paths under ``addr``.

    Returns two DataFrames with column ``raw`` only, preserving input row order.
    """
    empty = pd.DataFrame(columns=["raw"])
    if novel_raw_df.empty:
        return empty.copy(), empty.copy()
    if addr_files_long_df.empty:
        return empty.copy(), novel_raw_df[["raw"]].reset_index(drop=True)

    df = novel_raw_df.copy()
    if "norm" not in df.columns:
        df["norm"] = df["raw"].map(normalize_llc_address_for_compare)
    files_side = addr_files_long_df.rename(columns={"addr": "norm"})
    merged = df.merge(files_side, on="norm", how="left")
    merged["in_p"] = merged["file"].notna() & merged["file"].map(
        lambda f: source_path_has_prefix(str(f), source_path_prefix)
    )
    norm_in = merged.groupby("norm", sort=False)["in_p"].any()
    df = df.reset_index(drop=True)
    df["_in"] = df["norm"].map(norm_in).fillna(False).astype(bool)
    in_df = df.loc[df["_in"], ["raw"]].reset_index(drop=True)
    out_df = df.loc[~df["_in"], ["raw"]].reset_index(drop=True)
    return in_df, out_df


def split_novel_lines_by_source_prefix(
    novel_lines_df: pd.DataFrame,
    source_path_prefix: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split rows by whether ``file`` is under ``source_path_prefix``."""
    cols = ["file", "function", "line"]
    empty = pd.DataFrame(columns=cols)
    if novel_lines_df.empty:
        return empty.copy(), empty.copy()
    df = novel_lines_df[cols].copy()
    mask = df["file"].map(lambda f: source_path_has_prefix(f, source_path_prefix))
    return (
        df.loc[mask].reset_index(drop=True),
        df.loc[~mask].reset_index(drop=True),
    )


def test_raw_addresses_df(addr_strings: set[str]) -> pd.DataFrame:
    """Sorted unique raw strings as a single-column DataFrame for :func:`addresses_in_test_not_in_baseline`."""
    if not addr_strings:
        return _empty_raw_df()
    return pd.DataFrame({"raw": sorted(addr_strings)})
