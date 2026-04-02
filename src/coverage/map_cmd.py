"""``coverage map`` — summarize paired llc/opt symcov and sancov inputs."""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path


def _parse_line_from_loc(loc_str: object) -> int | None:
    if not isinstance(loc_str, str) or not loc_str.strip():
        return None
    part = loc_str.split(":", 1)[0].strip()
    try:
        return int(part)
    except ValueError:
        return None


def _point_id_to_location(symcov: dict[str, object]) -> dict[str, tuple[str, str, int]]:
    """
    Invert ``point-symbol-info``: point id -> (file_path, function_name, line).

    Values in the leaf map are strings like ``5:0`` (line:column); line is the first integer.
    """
    out: dict[str, tuple[str, str, int]] = {}
    psi = symcov.get("point-symbol-info")
    if psi is None:
        psi = symcov.get("point_symbol_info")
    if not isinstance(psi, dict):
        return out

    for file_path, by_func in psi.items():
        if not isinstance(file_path, str) or not isinstance(by_func, dict):
            continue
        for func_name, by_point in by_func.items():
            if not isinstance(func_name, str) or not isinstance(by_point, dict):
                continue
            for point_id, loc_str in by_point.items():
                if not isinstance(point_id, str):
                    continue
                line = _parse_line_from_loc(loc_str)
                if line is None:
                    continue
                out[point_id] = (file_path, func_name, line)
    return out


def _covered_locations_from_symcov(symcov: dict[str, object]) -> list[dict[str, object]]:
    """Map ``covered-points`` ids through ``point-symbol-info`` to unique ``file`` / ``function`` / ``line`` rows.

    Raises ``ValueError`` if any covered point id is missing from ``point-symbol-info`` (or has a
    value that does not yield a parseable line), or if a ``covered-points`` entry is not a string.
    """
    raw = symcov.get("covered-points")
    if raw is None:
        raw = symcov.get("covered_points")
    if not isinstance(raw, list):
        return []

    table = _point_id_to_location(symcov)
    missing: list[str] = []
    for pid in raw:
        if not isinstance(pid, str):
            raise ValueError(
                f"covered-points entries must be strings, got {type(pid).__name__}: {pid!r}"
            )
        if pid not in table:
            missing.append(pid)
    if missing:
        raise ValueError(
            "covered-points not found under point-symbol-info (or unparseable line:col): "
            + ", ".join(missing)
        )

    seen: set[tuple[str, str, int]] = set()
    rows: list[dict[str, object]] = []
    for pid in raw:
        loc = table[pid]
        file_path, func_name, line = loc
        key = (file_path, func_name, line)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"file": file_path, "function": func_name, "line": line})

    rows.sort(key=lambda r: (str(r["file"]), int(r["line"]), str(r["function"])))
    return rows


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

    llc_rows = _covered_locations_from_symcov(llc_data)
    opt_rows = _covered_locations_from_symcov(opt_data)

    seen: set[tuple[str, str, int]] = set()
    union: list[dict[str, object]] = []
    for r in llc_rows + opt_rows:
        key = (str(r["file"]), str(r["function"]), int(r["line"]))
        if key in seen:
            continue
        seen.add(key)
        union.append(
            {"file": r["file"], "function": r["function"], "line": r["line"]}
        )

    union.sort(key=lambda r: (str(r["file"]), int(r["line"]), str(r["function"])))
    return union


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
