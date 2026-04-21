#!/usr/bin/env python3
"""
Create per-line reduce harness directories from a stacked novel-lines CSV,
a directory of input .bc tests, and an llc point_symbol_info.json mapping.

Each output directory mirrors example/amd/new-test-1 (config.json,
interesting_ir.sh, and the copied .bc). COVERED in interesting_ir.sh is
resolved from (file, function, line) via the symbol JSON.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def llvm_rel_source_path(abs_path: str) -> str:
    """Path under llvm/... as used in fuzz-fill config.json."""
    norm = abs_path.replace("\\", "/")
    for needle in ("llvm/lib/", "llvm/include/", "llvm/utils/", "llvm/tools/"):
        i = norm.find(needle)
        if i >= 0:
            return norm[i:]
    raise ValueError(f"Could not derive llvm-relative path from: {abs_path!r}")


def _json_path_key(point_symbol_info: dict, abs_file: str) -> str:
    if abs_file in point_symbol_info:
        return abs_file
    try:
        suffix = llvm_rel_source_path(abs_file)
    except ValueError:
        suffix = None
    if suffix:
        for k in point_symbol_info:
            if k.replace("\\", "/").endswith(suffix):
                return k
    raise KeyError(
        f"No point-symbol-info entry for file {abs_file!r} "
        f"(tried exact path and suffix from llvm/...)."
    )


def covered_address_for_line(
    point_symbol_info: dict,
    abs_file: str,
    function: str,
    line: int,
) -> str:
    file_key = _json_path_key(point_symbol_info, abs_file)
    by_fn = point_symbol_info[file_key]
    if function not in by_fn:
        avail = [k for k in by_fn if function.split("(")[0] in k]
        hint = f" Similar keys: {avail[:5]}" if avail else ""
        raise KeyError(f"Unknown function {function!r} in {file_key}.{hint}")
    line_str = str(line)
    matches: list[str] = []
    for addr_hex, loc in by_fn[function].items():
        src_line = loc.split(":", 1)[0]
        if src_line == line_str:
            matches.append(addr_hex)
    if not matches:
        raise KeyError(
            f"No coverage point for {file_key} :: {function} :: line {line}"
        )
    if len(matches) > 1:
        # Prefer lowest hex as stable tie-break (multiple probes on one line).
        matches.sort(key=lambda h: int(h, 16))
    return "0x" + matches[0]


def load_point_symbol_info(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        root = json.load(f)
    psi = root.get("point-symbol-info")
    if not isinstance(psi, dict):
        raise ValueError(f"{path} missing top-level 'point-symbol-info' object")
    return psi


def render_interesting_ir(template_text: str, covered: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return f'COVERED="{covered}"'

    out, n = re.subn(
        r'^COVERED="[^"]*"',
        repl,
        template_text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise ValueError(
            "Template interesting_ir.sh must contain exactly one COVERED=\"...\" line."
        )
    return out


def copy_input_bc(tests_base: Path, test_name: str, dest_dir: Path) -> None:
    """Copy tests_base/<test_name> into dest_dir/<basename(test_name)>."""
    src = tests_base / test_name
    if not src.exists():
        raise FileNotFoundError(f"Input test not found: {src}")
    dest_name = Path(test_name).name
    dest = dest_dir / dest_name
    if src.is_dir():
        # Prefer explicit child matching test_name, else a single .bc in the dir.
        child = src / dest_name
        if child.is_file():
            shutil.copy2(child, dest)
            return
        bcs = list(src.glob("*.bc"))
        if len(bcs) == 1:
            shutil.copy2(bcs[0], dest)
            return
        raise FileNotFoundError(
            f"Directory {src} has no {dest_name} and not exactly one *.bc"
        )
    shutil.copy2(src, dest)


def prepare_test_case(
    *,
    row_index: int,
    per_test_csv: str,
    file_col: str,
    function: str,
    line: int,
    tests_base: Path,
    out_parent: Path,
    point_symbol_info: dict,
    template_interesting: str,
) -> Path:
    test_name = Path(per_test_csv).stem  # e.g. hash.bc from hash.bc.csv
    short = Path(test_name).stem[:8] if test_name else f"r{row_index}"
    dest_dir = out_parent / f"t-{row_index:05d}-{short}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    covered = covered_address_for_line(
        point_symbol_info, file_col, function, line
    )
    config = {
        "input": Path(test_name).name,
        "file": llvm_rel_source_path(file_col),
        "line": line,
        "replacement": "",
        "pipeline": [
            {
                "id": "llvm_reduce_ir",
                "parameters": {"interesting": "interesting_ir.sh"},
            }
        ],
    }
    (dest_dir / "config.json").write_text(
        json.dumps(config, indent=4) + "\n", encoding="utf-8"
    )
    (dest_dir / "interesting_ir.sh").write_text(
        render_interesting_ir(template_interesting, covered),
        encoding="utf-8",
    )
    copy_input_bc(tests_base, test_name, dest_dir)
    (dest_dir / "interesting_ir.sh").chmod(0o755)
    return dest_dir


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, required=True, help="all_novel_source_lines.csv")
    p.add_argument(
        "--tests-base",
        type=Path,
        required=True,
        help="Directory containing each test as <stem-from-csv>.bc (or that path as a dir).",
    )
    p.add_argument(
        "--symbol-json",
        type=Path,
        required=True,
        help="llc.*.point_symbol_info.json (point-symbol-info map).",
    )
    p.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory to create t-00001-xxxx subdirectories under.",
    )
    p.add_argument(
        "--template-dir",
        type=Path,
        default=_repo_root() / "example" / "amd" / "new-test-1",
        help="Example layout; interesting_ir.sh is used as a template (default: example/amd/new-test-1).",
    )
    args = p.parse_args(argv)

    tests_base = args.tests_base.resolve()
    out_parent = args.output.resolve()
    out_parent.mkdir(parents=True, exist_ok=True)

    template_path = args.template_dir / "interesting_ir.sh"
    template_interesting = template_path.read_text(encoding="utf-8")

    point_symbol_info = load_point_symbol_info(args.symbol_json.resolve())

    with args.csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        expected = {"per_test_csv", "file", "function", "line"}
        if reader.fieldnames is None or not expected.issubset(set(reader.fieldnames)):
            print(
                f"CSV must have columns {expected}, got {reader.fieldnames!r}",
                file=sys.stderr,
            )
            return 2
        rows = list(reader)

    ok = 0
    for i, row in enumerate(rows, start=1):
        try:
            line = int(row["line"])
        except ValueError:
            print(f"Row {i}: bad line {row['line']!r}", file=sys.stderr)
            continue
        try:
            dest = prepare_test_case(
                row_index=i,
                per_test_csv=row["per_test_csv"].strip(),
                file_col=row["file"].strip(),
                function=row["function"].strip(),
                line=line,
                tests_base=tests_base,
                out_parent=out_parent,
                point_symbol_info=point_symbol_info,
                template_interesting=template_interesting,
            )
            print(dest)
            ok += 1
        except (OSError, KeyError, ValueError, FileNotFoundError) as e:
            print(f"Row {i}: {e}", file=sys.stderr)

    if ok == 0:
        return 1
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
