"""``coverage map`` — summarize paired llc/opt symcov and sancov inputs."""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

import pandas as pd


def _point_symbol_info_records(psi: dict[str, object]) -> list[dict[str, object]]:
    """Flatten ``point-symbol-info`` to rows before building a DataFrame."""
    records: list[dict[str, object]] = []
    for file_path, by_func in psi.items():
        if not isinstance(file_path, str) or not isinstance(by_func, dict):
            continue
        for func_name, by_point in by_func.items():
            if not isinstance(func_name, str) or not isinstance(by_point, dict):
                continue
            for point_id, loc_str in by_point.items():
                if not isinstance(point_id, str):
                    continue
                records.append(
                    {
                        "point_id": point_id,
                        "file": file_path,
                        "function": func_name,
                        "loc_str": loc_str,
                    }
                )
    return records


def _point_table_from_symcov(symcov: dict[str, object]) -> pd.DataFrame:
    """
    DataFrame keyed by ``point_id`` with columns ``file``, ``function``, ``line``.

    Line is parsed vectorized from ``loc_str`` (``line:col``). Duplicate ``point_id`` rows keep
    the last occurrence (same as dict overwrite semantics).
    """
    psi = symcov.get("point-symbol-info")
    if psi is None:
        psi = symcov.get("point_symbol_info")
    if not isinstance(psi, dict):
        return pd.DataFrame(columns=["point_id", "file", "function", "line"])

    records = _point_symbol_info_records(psi)
    if not records:
        return pd.DataFrame(columns=["point_id", "file", "function", "line"])

    df = pd.DataFrame(records)
    loc = df["loc_str"].astype(str)
    first_col = loc.str.split(":", n=1, expand=True)[0].str.strip()
    df["line"] = pd.to_numeric(first_col, errors="coerce")
    df = df.drop(columns=["loc_str"])
    df = df.dropna(subset=["line"])
    df["line"] = df["line"].astype("int64")
    df = df.drop_duplicates(subset=["point_id"], keep="last")
    return df


def _covered_locations_from_symcov(symcov: dict[str, object]) -> list[dict[str, object]]:
    """Map ``covered-points`` through ``point-symbol-info`` to unique location rows.

    Raises ``ValueError`` if any covered id is missing or not a string.
    """
    raw = symcov.get("covered-points")
    if raw is None:
        raw = symcov.get("covered_points")
    if not isinstance(raw, list):
        return []
    if not raw:
        return []

    for x in raw:
        if not isinstance(x, str):
            raise ValueError(
                f"covered-points entries must be strings, got {type(x).__name__}: {x!r}"
            )

    table = _point_table_from_symcov(symcov)
    covered = pd.DataFrame({"point_id": raw})
    merged = covered.merge(table, on="point_id", how="left", validate="many_to_one")

    miss = merged.loc[merged["line"].isna(), "point_id"].tolist()
    if miss:
        raise ValueError(
            "covered-points not found under point-symbol-info (or unparseable line:col): "
            + ", ".join(miss)
        )

    out = merged.drop_duplicates(subset=["file", "function", "line"])[
        ["file", "function", "line"]
    ]
    out = out.sort_values(by=["file", "line", "function"], kind="mergesort")
    return _location_df_to_records(out)


def _location_rows_to_df(rows: list[dict[str, object]]) -> pd.DataFrame:
    cols = ["file", "function", "line"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)


def _location_df_to_records(df: pd.DataFrame) -> list[dict[str, object]]:
    """JSON-friendly records (plain ``int`` / ``str``, no numpy scalars)."""
    return [
        {
            "file": str(r.file),
            "function": str(r.function),
            "line": int(r.line),
        }
        for r in df.itertuples(index=False)
    ]


def _create_joint_sancov(
    llc_symcov: Path,
    opt_symcov: Path,
    *,
    _llc_sancov: Path,
    _opt_sancov: Path,
) -> list[dict[str, object]]:
    """
    Load llc and opt symcov JSON and return a de-duplicated list of covered source locations.

    Each entry is ``{"file", "function", "line"}`` with ``line`` from the part before ``:`` in
    point-symbol-info values (e.g. ``5:0`` -> ``5``). ``_llc_sancov`` / ``_opt_sancov`` are kept
    for API symmetry; reserved for future joint ``.sancov`` output.
    """

    with llc_symcov.open(encoding="utf-8") as f:
        llc_data = json.load(f)
    with opt_symcov.open(encoding="utf-8") as f:
        opt_data = json.load(f)

    if not isinstance(llc_data, dict) or not isinstance(opt_data, dict):
        raise TypeError("llc and opt symcov must be JSON objects")

    llc_df = _location_rows_to_df(_covered_locations_from_symcov(llc_data))
    opt_df = _location_rows_to_df(_covered_locations_from_symcov(opt_data))
    if llc_df.empty and opt_df.empty:
        return []

    union = pd.concat([llc_df, opt_df], axis=0, ignore_index=True)
    union = union.drop_duplicates(subset=["file", "function", "line"])
    union = union.sort_values(by=["file", "line", "function"], kind="mergesort")
    return _location_df_to_records(union)


def _symcov_summary(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"path": str(path), "json_type": type(data).__name__}

    out: dict[str, object] = {
        "path": str(path),
        "top_level_keys": sorted(data.keys()),
    }
    if "BinaryHash" in data:
        out["binary_hash"] = data["BinaryHash"]
    if isinstance(data.get("Points"), list):
        out["points_len"] = len(data["Points"])
    if isinstance(data.get("CoveredIds"), list):
        out["covered_ids_len"] = len(data["CoveredIds"])
    return out


def _sancov_meta(path: Path) -> dict[str, object]:
    st = path.stat()
    return {"path": str(path), "bytes": st.st_size}


def map_main(args: Namespace) -> int:
    get_summary = getattr(args, "get_summary", False)
    create_joint = getattr(args, "create_joint_sancov", False)
    if not get_summary and not create_joint:
        print(
            "ERROR: specify at least one of --get-summary or --create-joint-sancov",
            file=sys.stderr,
        )
        return 1

    llc_symcov = Path(args.llc_symcov).resolve()
    llc_sancov = Path(args.llc_sancov).resolve()
    opt_symcov = Path(args.opt_symcov).resolve()
    opt_sancov = Path(args.opt_sancov).resolve()

    for label, p in (
        ("llc-symcov", llc_symcov),
        ("llc-sancov", llc_sancov),
        ("opt-symcov", opt_symcov),
        ("opt-sancov", opt_sancov),
    ):
        if not p.is_file():
            print(f"ERROR: {label} is not a file: {p}", file=sys.stderr)
            return 1

    joint_locations: list[dict[str, object]] | None = None
    if create_joint:
        try:
            joint_locations = _create_joint_sancov(
                llc_symcov,
                opt_symcov,
                _llc_sancov=llc_sancov,
                _opt_sancov=opt_sancov,
            )
        except (json.JSONDecodeError, OSError, TypeError, ValueError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1

    if get_summary:
        try:
            payload = {
                "llc_symcov": _symcov_summary(llc_symcov),
                "llc_sancov": _sancov_meta(llc_sancov),
                "opt_symcov": _symcov_summary(opt_symcov),
                "opt_sancov": _sancov_meta(opt_sancov),
            }
            if joint_locations is not None:
                payload["joint_covered_locations"] = joint_locations
        except json.JSONDecodeError as e:
            print(f"ERROR: invalid JSON in symcov: {e}", file=sys.stderr)
            return 1
        except OSError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1

        text = json.dumps(payload, indent=2)
        if getattr(args, "output", None):
            out_path = Path(args.output).resolve()
            out_path.write_text(text, encoding="utf-8")
            print(f"Wrote {out_path}")
        else:
            print(text)
    elif joint_locations is not None:
        print(json.dumps(joint_locations, indent=2))

    return 0
