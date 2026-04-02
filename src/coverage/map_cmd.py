"""``coverage map`` — summarize paired llc/opt symcov and sancov inputs."""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path


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

    try:
        payload = {
            "llc_symcov": _symcov_summary(llc_symcov),
            "llc_sancov": _sancov_meta(llc_sancov),
            "opt_symcov": _symcov_summary(opt_symcov),
            "opt_sancov": _sancov_meta(opt_sancov),
        }
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
    return 0
