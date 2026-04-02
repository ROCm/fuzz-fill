"""``coverage map`` — summarize paired llc/opt symcov and sancov inputs."""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from collections.abc import Callable
from pathlib import Path

import pandas as pd


def _map_log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _joint_path_filter_from_args(args: Namespace) -> Callable[[str], bool] | None:
    """
    ``None`` — no path restriction (strict validation: every covered id must resolve).

    Otherwise a predicate kept only for joint/CSV output; applied to the point table **before**
    merging with ``covered-points``, so downstream work is smaller.
    """
    if getattr(args, "no_joint_file_filter", False):
        return None
    pfx = getattr(args, "joint_file_prefix", None)
    if pfx is not None:
        base = Path(pfx).expanduser()
        base_s = base.as_posix().rstrip("/")

        def by_prefix(path: str) -> bool:
            p = Path(path).expanduser().as_posix()
            return p == base_s or p.startswith(base_s + "/")

        return by_prefix

    def llvm_project_component(path: str) -> bool:
        try:
            return "llvm-project" in Path(path).expanduser().parts
        except (TypeError, ValueError):
            return False

    return llvm_project_component


def _joint_filter_label(args: Namespace) -> str:
    if getattr(args, "no_joint_file_filter", False):
        return "none (all source paths, strict resolution)"
    if getattr(args, "joint_file_prefix", None) is not None:
        return f"prefix {Path(args.joint_file_prefix).expanduser()}"
    return "default (path has directory component 'llvm-project')"


def _covered_points_count(symcov: dict[str, object]) -> int:
    raw = symcov.get("covered-points")
    if raw is None:
        raw = symcov.get("covered_points")
    return len(raw) if isinstance(raw, list) else 0


def _symcov_point_table_stats(
    symcov: dict[str, object],
    path_filter: Callable[[str], bool] | None,
) -> tuple[int, int, int]:
    """``covered_points``, ``point_table_rows``, ``point_table_rows_after_filter``."""
    c = _covered_points_count(symcov)
    table = _point_table_from_symcov(symcov)
    n_all = len(table)
    if path_filter is None or table.empty:
        return c, n_all, n_all
    filtered = table[table["file"].astype(str).map(path_filter)]
    return c, n_all, len(filtered)


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


def _covered_locations_from_symcov(
    symcov: dict[str, object],
    *,
    path_filter: Callable[[str], bool] | None = None,
) -> list[dict[str, object]]:
    """Map ``covered-points`` through ``point-symbol-info`` to unique location rows.

    If ``path_filter`` is set, keep only point-symbol rows whose ``file`` passes it **before**
    merging with ``covered-points``; covered ids that only map outside the filter are dropped.

    If ``path_filter`` is ``None``, every covered id must resolve (strict).

    Raises ``ValueError`` if any covered id is missing or not a string (strict mode only).
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
    if path_filter is not None:
        table = table[table["file"].astype(str).map(path_filter)]
    covered = pd.DataFrame({"point_id": raw})
    merged = covered.merge(table, on="point_id", how="left", validate="many_to_one")

    if path_filter is None:
        miss = merged.loc[merged["line"].isna(), "point_id"].tolist()
        if miss:
            raise ValueError(
                "covered-points not found under point-symbol-info (or unparseable line:col): "
                + ", ".join(miss)
            )
    else:
        merged = merged.dropna(subset=["line"])

    if merged.empty:
        return []

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


def _covered_locations_df(
    symcov: dict[str, object],
    *,
    path_filter: Callable[[str], bool] | None = None,
) -> pd.DataFrame:
    return _location_rows_to_df(_covered_locations_from_symcov(symcov, path_filter=path_filter))


def _union_covered_df(
    llc_data: dict[str, object],
    opt_data: dict[str, object],
    *,
    path_filter: Callable[[str], bool] | None = None,
) -> pd.DataFrame:
    """Unique (file, function, line) covered by llc **or** opt symcov."""
    llc_df = _covered_locations_df(llc_data, path_filter=path_filter)
    opt_df = _covered_locations_df(opt_data, path_filter=path_filter)
    if llc_df.empty and opt_df.empty:
        return pd.DataFrame(columns=["file", "function", "line"])
    union = pd.concat([llc_df, opt_df], axis=0, ignore_index=True)
    union = union.drop_duplicates(subset=["file", "function", "line"])
    union = union.sort_values(by=["file", "line", "function"], kind="mergesort")
    return union


def _union_covered_locations(
    llc_data: dict[str, object],
    opt_data: dict[str, object],
    *,
    path_filter: Callable[[str], bool] | None = None,
) -> list[dict[str, object]]:
    return _location_df_to_records(
        _union_covered_df(llc_data, opt_data, path_filter=path_filter)
    )


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
    llc_data: dict[str, object],
    opt_data: dict[str, object],
    *,
    _llc_sancov: Path,
    _opt_sancov: Path,
    path_filter: Callable[[str], bool] | None = None,
) -> list[dict[str, object]]:
    """
    Union of covered (file, function, line) from llc and opt symcov payloads.

    ``_llc_sancov`` / ``_opt_sancov`` are reserved for future joint ``.sancov`` output.
    """
    return _union_covered_locations(llc_data, opt_data, path_filter=path_filter)


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
    joint_csv = getattr(args, "joint_csv", None)
    if joint_csv is not None and not create_joint:
        print(
            "ERROR: --joint-csv requires --create-joint-sancov",
            file=sys.stderr,
        )
        return 1
    if not get_summary and not create_joint:
        print(
            "ERROR: specify at least one of --get-summary or --create-joint-sancov",
            file=sys.stderr,
        )
        return 1

    parts: list[str] = []
    if create_joint:
        parts.append("--create-joint-sancov")
    if get_summary:
        parts.append("--get-summary")
    if joint_csv is not None:
        parts.append(f"--joint-csv {joint_csv}")
    _map_log(f"[map] Starting ({', '.join(parts)})")

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

    _map_log(f"[map] llc symcov:  {llc_symcov} ({llc_symcov.stat().st_size:,} bytes)")
    _map_log(f"[map] llc sancov:  {llc_sancov} ({llc_sancov.stat().st_size:,} bytes)")
    _map_log(f"[map] opt symcov:  {opt_symcov} ({opt_symcov.stat().st_size:,} bytes)")
    _map_log(f"[map] opt sancov:  {opt_sancov} ({opt_sancov.stat().st_size:,} bytes)")

    joint_locations: list[dict[str, object]] | None = None
    joint_counts: tuple[int, int, int] | None = None  # llc, opt, either (deduped)
    joint_path_filter = _joint_path_filter_from_args(args) if create_joint else None
    if create_joint:
        try:
            _map_log("[map] Loading llc .symcov JSON …")
            with llc_symcov.open(encoding="utf-8") as f:
                llc_data = json.load(f)
            _map_log("[map] Loading opt .symcov JSON …")
            with opt_symcov.open(encoding="utf-8") as f:
                opt_data = json.load(f)
            if not isinstance(llc_data, dict) or not isinstance(opt_data, dict):
                raise TypeError("llc and opt symcov must be JSON objects")

            _map_log(f"[map] Joint path filter: {_joint_filter_label(args)}")
            lc, lt, ltf = _symcov_point_table_stats(llc_data, joint_path_filter)
            oc, ot, otf = _symcov_point_table_stats(opt_data, joint_path_filter)
            llc_tbl_suffix = (
                f" → {ltf:,} rows after path filter" if joint_path_filter is not None else ""
            )
            opt_tbl_suffix = (
                f" → {otf:,} rows after path filter" if joint_path_filter is not None else ""
            )
            _map_log(
                f"[map] llc symcov: covered-points entries={lc:,}; "
                f"point-symbol-info rows (unique point_id)={lt:,}{llc_tbl_suffix}"
            )
            _map_log(
                f"[map] opt symcov: covered-points entries={oc:,}; "
                f"point-symbol-info rows (unique point_id)={ot:,}{opt_tbl_suffix}"
            )
            if joint_path_filter is not None:
                if lt > 0 and ltf == 0:
                    _map_log(
                        "[map] warning: path filter removed all llc point-symbol rows "
                        "(no rows will match); try --no-joint-file-filter or "
                        "--joint-file-prefix matching your paths",
                    )
                if ot > 0 and otf == 0:
                    _map_log(
                        "[map] warning: path filter removed all opt point-symbol rows "
                        "(no rows will match); try --no-joint-file-filter or "
                        "--joint-file-prefix matching your paths",
                    )

            _map_log("[map] Resolving covered locations and merging llc ∪ opt …")
            joint_locations = _create_joint_sancov(
                llc_data,
                opt_data,
                _llc_sancov=llc_sancov,
                _opt_sancov=opt_sancov,
                path_filter=joint_path_filter,
            )
            llc_n = len(_covered_locations_df(llc_data, path_filter=joint_path_filter))
            opt_n = len(_covered_locations_df(opt_data, path_filter=joint_path_filter))
            either_n = len(joint_locations)
            joint_counts = (llc_n, opt_n, either_n)
            _map_log(
                f"[map] Unique covered source lines (after filter): llc={llc_n:,}, "
                f"opt={opt_n:,}, either deduped={either_n:,}"
            )
            if joint_csv is not None:
                union_df = _union_covered_df(
                    llc_data, opt_data, path_filter=joint_path_filter
                )
                out_csv = Path(joint_csv).resolve()
                out_csv.parent.mkdir(parents=True, exist_ok=True)
                n_csv = len(union_df)
                _map_log(
                    f"[map] Writing --joint-csv: {n_csv:,} data rows (+ header) → {out_csv}"
                )
                union_df.to_csv(out_csv, index=False)
                _map_log("[map] Joint CSV write complete.")
        except (json.JSONDecodeError, OSError, TypeError, ValueError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1

    if get_summary:
        try:
            _map_log("[map] Building --get-summary (reading symcov metadata) …")
            payload = {
                "llc_symcov": _symcov_summary(llc_symcov),
                "llc_sancov": _sancov_meta(llc_sancov),
                "opt_symcov": _symcov_summary(opt_symcov),
                "opt_sancov": _sancov_meta(opt_sancov),
            }
            if joint_locations is not None and joint_counts is not None:
                x, y, z = joint_counts
                payload["joint_coverage_line_counts"] = {
                    "llc": x,
                    "opt": y,
                    "either_deduped": z,
                }
                if getattr(args, "output", None):
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
            _map_log(f"[map] Wrote JSON summary ({len(text):,} chars) → {out_path}")
            print(f"Wrote {out_path}")
        else:
            _map_log(
                f"[map] Writing JSON summary to stdout ({len(text):,} chars, "
                f"{len(text.splitlines()):,} lines) …"
            )
            print(text)

    if joint_counts is not None:
        x, y, z = joint_counts
        msg = (
            f"{x} lines were covered by llc, {y} were covered by opt, "
            f"and {z} were covered by either (removing duplicates)."
        )
        if not get_summary:
            _map_log("[map] Summary:")
            print(msg)
        elif getattr(args, "output", None):
            _map_log("[map] Summary:")
            print(msg)

    _map_log("[map] Done.")
    return 0
