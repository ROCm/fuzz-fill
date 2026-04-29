#!/usr/bin/env python3
"""
Create per-line reduce harness directories from a coverage CSV (new_coverage
shape) and a directory of input tests.

Expected ``--csv`` columns: test_name, file, line, covered_addresses
(covered_addresses is ``0x...`` values separated by ``;``, as in diff/new_coverage.csv).

Each output directory mirrors example/amd/new-test-1 (config.json,
interesting_ir.sh, and the copied .bc). COVERED in interesting_ir.sh is the
lowest hex among addresses for that row (same as multiple instrumentation sites
on one source line).

Each ``config.json`` sets ``output_dir`` to a ``reduced`` subdirectory next to
it so reduction artifacts stay inside the case directory.

With ``--llvm-bin``, runs ``python -m reduce --config <case>/config.json``
for each case (same idea as scripts/reduce_amd_coverage_based.sh).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _reduce_subprocess_env() -> dict[str, str]:
    """Prepend repo ``src`` on PYTHONPATH so ``python -m reduce`` resolves."""
    env = os.environ.copy()
    src = str(_repo_root() / "src")
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src if not prev else f"{src}{os.pathsep}{prev}"
    return env


def run_reduce(*, case_dir: Path, llvm_bin: Path) -> None:
    """Run the same CLI as scripts/reduce_amd_coverage_based.sh for one case directory."""
    config = case_dir / "config.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "reduce",
            "--config",
            str(config),
            "--llvm-bin",
            str(llvm_bin.resolve()),
        ],
        cwd=case_dir,
        env=_reduce_subprocess_env(),
        check=True,
    )


def llvm_rel_source_path(abs_path: str) -> str:
    """Path under llvm/... as used in fuzz-fill config.json."""
    norm = abs_path.replace("\\", "/")
    for needle in ("llvm/lib/", "llvm/include/", "llvm/utils/", "llvm/tools/"):
        i = norm.find(needle)
        if i >= 0:
            return norm[i:]
    raise ValueError(f"Could not derive llvm-relative path from: {abs_path!r}")


def parse_covered_addresses_field(value: str) -> list[str]:
    """Split ``covered_addresses`` cell into hex strings without 0x prefix."""
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


def resolve_covered_hexes(covered_addresses_cell: str) -> tuple[str, list[str]]:
    """Return (COVERED value with 0x prefix, sorted hex-without-0x list for logging)."""
    hexes = parse_covered_addresses_field(covered_addresses_cell)
    if not hexes:
        raise ValueError("covered_addresses is empty or has no valid hex values")
    hexes_sorted = sorted(hexes, key=lambda h: int(h, 16))
    return "0x" + hexes_sorted[0], hexes_sorted


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
    test_name: str,
    file_col: str,
    line: int,
    covered: str,
    hexes_sorted: list[str],
    tests_base: Path,
    out_parent: Path,
    template_interesting: str,
) -> tuple[bool, Path]:
    short = Path(test_name).stem[:8] if test_name else f"r{row_index}"
    dest_dir = out_parent / f"t-{row_index:05d}-{short}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    if len(hexes_sorted) > 1:
        detail = ", ".join(f"0x{h}" for h in hexes_sorted)
        print(
            f"Row {row_index}: ambiguous COVERED - {len(hexes_sorted)} "
            f"addresses on source line {line}; using {covered}; all: {detail}",
            file=sys.stderr,
        )
    reduced_dir = (dest_dir / "reduced").resolve()
    config = {
        "input": Path(test_name).name,
        "file": llvm_rel_source_path(file_col),
        "line": line,
        "replacement": "",
        "output_dir": str(reduced_dir),
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
    return len(hexes_sorted) > 1, dest_dir


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Coverage CSV: test_name, file, line, covered_addresses (e.g. diff/new_coverage.csv).",
    )
    p.add_argument(
        "--tests-base",
        type=Path,
        required=True,
        help="Directory containing each test as <stem-from-csv>.bc (or that path as a dir).",
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
    p.add_argument(
        "--llvm-bin",
        type=Path,
        default=None,
        help=(
            "If set, run `python -m reduce --config <case>/config.json --llvm-bin ...` "
            "after each prepared directory (same as scripts/reduce_amd_coverage_based.sh)."
        ),
    )
    args = p.parse_args(argv)

    tests_base = args.tests_base.resolve()
    llvm_bin = args.llvm_bin.resolve() if args.llvm_bin is not None else None
    out_parent = args.output.resolve()
    out_parent.mkdir(parents=True, exist_ok=True)

    template_path = args.template_dir / "interesting_ir.sh"
    template_interesting = template_path.read_text(encoding="utf-8")

    with args.csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        expected = {"test_name", "file", "line", "covered_addresses"}
        if reader.fieldnames is None or not expected.issubset(set(reader.fieldnames)):
            print(
                f"CSV must have columns {expected}, got {reader.fieldnames!r}",
                file=sys.stderr,
            )
            return 2
        rows = list(reader)

    ok = 0
    ambiguous_rows = 0
    for i, row in enumerate(rows, start=1):
        try:
            line = int(row["line"])
        except ValueError:
            print(f"Row {i}: bad line {row['line']!r}", file=sys.stderr)
            continue
        try:
            covered, hexes_sorted = resolve_covered_hexes(
                row.get("covered_addresses") or "",
            )
            amb, dest = prepare_test_case(
                row_index=i,
                test_name=row["test_name"].strip(),
                file_col=row["file"].strip(),
                line=line,
                covered=covered,
                hexes_sorted=hexes_sorted,
                tests_base=tests_base,
                out_parent=out_parent,
                template_interesting=template_interesting,
            )
            if llvm_bin is not None:
                print(
                    f"Row {i}: running reduce (llvm-bin={llvm_bin})...",
                    file=sys.stderr,
                    flush=True,
                )
                run_reduce(case_dir=dest, llvm_bin=llvm_bin)
            print(dest)
            ok += 1
            if amb:
                ambiguous_rows += 1
        except subprocess.CalledProcessError as e:
            print(f"Row {i}: reduce exited with status {e.returncode}", file=sys.stderr)
        except (OSError, ValueError, FileNotFoundError) as e:
            print(f"Row {i}: {e}", file=sys.stderr)

    if ambiguous_rows:
        print(
            f"Summary: {ambiguous_rows} row(s) had multiple COVERED candidates on the same "
            "source line (lowest address was used; see messages above).",
            file=sys.stderr,
        )
    elif ok > 0:
        if ok == len(rows):
            print(
                "Summary: every row matched to a unique COVERED address "
                "(one instrumentation site per file/source line).",
                file=sys.stderr,
            )
        else:
            print(
                f"Summary: each of the {ok} successful row(s) matched to a unique COVERED address "
                "(one instrumentation site per file/source line).",
                file=sys.stderr,
            )

    if ok == 0:
        return 1
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
