#!/usr/bin/env python3
"""
Create per-line reduce harness directories from diff/new_coverage.csv and
matching folders under new_tests/.

CSV columns: test_name, file, line, covered-points
(test_name is a directory under --new-tests containing test.sh).

Each test.sh records the instrumented llc invocation (binary, flags, .bc path).
Each output directory mirrors example/amd/new-test-1 (config.json,
interesting_ir.sh, and the copied .bc). COVERED in interesting_ir.sh is the
lowest hex among addresses for that row.

Each config.json sets output_dir to a reduced subdirectory next to it so
reduction artifacts stay inside the case directory.

With --llvm-bin, runs python -m reduce --config <case>/config.json for each case.

Use --n to process only the first N data rows of the CSV (after the header).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
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
    """Run reduce for one prepared case directory."""
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


@dataclass(frozen=True)
class TestShInfo:
    llvm_bin: Path
    bc_path: Path
    llc_flags: tuple[str, ...]


def parse_test_sh(test_sh: Path) -> TestShInfo:
    """Parse new_tests/<test_name>/test.sh for llc binary, flags, and .bc path."""
    if not test_sh.is_file():
        raise FileNotFoundError(f"test.sh not found: {test_sh}")

    llc_line: str | None = None
    for raw in test_sh.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            continue
        if "/llc" in line or line.endswith("llc") or " llc " in f" {line} ":
            llc_line = line
            break

    if llc_line is None:
        raise ValueError(f"No llc invocation found in {test_sh}")

    cmd = re.sub(r"\s*>.*$", "", llc_line).strip()
    parts = shlex.split(cmd)
    if len(parts) < 2:
        raise ValueError(f"Could not parse llc command in {test_sh}: {llc_line!r}")

    llc_exe = Path(parts[0])
    if llc_exe.name != "llc":
        raise ValueError(f"Expected llc executable, got {llc_exe!r} in {test_sh}")

    bc_indices = [i for i, p in enumerate(parts) if p.endswith(".bc")]
    if len(bc_indices) != 1:
        raise ValueError(
            f"Expected exactly one .bc argument in {test_sh}, got {bc_indices!r}"
        )
    bc_idx = bc_indices[0]
    bc_path = Path(parts[bc_idx])
    if not bc_path.is_file():
        raise FileNotFoundError(f"Bitcode file from test.sh does not exist: {bc_path}")

    flags = tuple(parts[1:bc_idx])
    return TestShInfo(llvm_bin=llc_exe.parent, bc_path=bc_path, llc_flags=flags)


def render_interesting_ir(
    template_text: str,
    *,
    covered: str,
    llvm_bin: Path,
    llc_flags: tuple[str, ...],
) -> str:
    flags_value = " ".join(llc_flags)

    out, n = re.subn(
        r'^LLVM_BIN=.*$',
        f'LLVM_BIN={llvm_bin}',
        template_text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise ValueError(
            'Template interesting_ir.sh must contain exactly one LLVM_BIN=... line.'
        )

    def repl_covered(m: re.Match[str]) -> str:
        return f'COVERED="{covered}"'

    out, n = re.subn(
        r'^COVERED="[^"]*"',
        repl_covered,
        out,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise ValueError(
            'Template interesting_ir.sh must contain exactly one COVERED="..." line.'
        )

    if re.search(r'^LLC_FLAGS=', out, flags=re.MULTILINE):
        out, n = re.subn(
            r'^LLC_FLAGS=.*$',
            f'LLC_FLAGS="{flags_value}"',
            out,
            count=1,
            flags=re.MULTILINE,
        )
        if n != 1:
            raise ValueError("Failed to set LLC_FLAGS in template.")
    else:
        out, n = re.subn(
            r'^(LLC=\$LLVM_BIN/llc)$',
            rf'\1\nLLC_FLAGS="{flags_value}"',
            out,
            count=1,
            flags=re.MULTILINE,
        )
        if n != 1:
            raise ValueError(
                'Template interesting_ir.sh must contain LLC=$LLVM_BIN/llc '
                "or an LLC_FLAGS= line."
            )

    out, n = re.subn(
        r'(\$LLC)\s+"\$1"',
        r'\1 $LLC_FLAGS "$1"',
        out,
        count=1,
    )
    if n != 1:
        raise ValueError(
            'Template interesting_ir.sh must invoke llc as $LLC ... "$1".'
        )
    return out


def copy_input_bc(test_info: TestShInfo, dest_dir: Path) -> str:
    """Copy the .bc from test.sh into dest_dir; return config input basename."""
    dest_name = test_info.bc_path.name
    shutil.copy2(test_info.bc_path, dest_dir / dest_name)
    return dest_name


def prepare_test_case(
    *,
    row_index: int,
    test_name: str,
    file_col: str,
    line: int,
    covered: str,
    hexes_sorted: list[str],
    new_tests: Path,
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

    test_info = parse_test_sh(new_tests / test_name / "test.sh")
    input_name = copy_input_bc(test_info, dest_dir)

    reduced_dir = (dest_dir / "reduced").resolve()
    config = {
        "input": input_name,
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
        render_interesting_ir(
            template_interesting,
            covered=covered,
            llvm_bin=test_info.llvm_bin,
            llc_flags=test_info.llc_flags,
        ),
        encoding="utf-8",
    )
    (dest_dir / "interesting_ir.sh").chmod(0o755)
    return len(hexes_sorted) > 1, dest_dir


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Coverage CSV (test_name, file, line, covered-points).",
    )
    p.add_argument(
        "--new-tests",
        type=Path,
        required=True,
        help="new_tests directory; each CSV test_name is a subdirectory with test.sh.",
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
        help="Example layout; interesting_ir.sh is used as a template.",
    )
    p.add_argument(
        "--llvm-bin",
        type=Path,
        default=None,
        help="If set, run python -m reduce for each prepared case directory.",
    )
    p.add_argument(
        "--n",
        type=int,
        default=None,
        metavar="N",
        help="Process at most the first N CSV data rows (default: all rows).",
    )
    args = p.parse_args(argv)

    if args.n is not None and args.n < 1:
        print("--n must be a positive integer.", file=sys.stderr)
        return 2

    new_tests = args.new_tests.resolve()
    llvm_bin = args.llvm_bin.resolve() if args.llvm_bin is not None else None
    out_parent = args.output.resolve()
    out_parent.mkdir(parents=True, exist_ok=True)

    template_path = args.template_dir / "interesting_ir.sh"
    template_interesting = template_path.read_text(encoding="utf-8")

    with args.csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        expected = {"test_name", "file", "line", "covered-points"}
        if reader.fieldnames is None or set(reader.fieldnames) != expected:
            print(
                f"CSV must have columns {sorted(expected)}, got {reader.fieldnames!r}",
                file=sys.stderr,
            )
            return 2
        rows = list(reader)

    if args.n is not None:
        rows = rows[: args.n]

    ok = 0
    ambiguous_rows = 0
    for i, row in enumerate(rows, start=1):
        try:
            line = int(row["line"])
        except ValueError:
            print(f"Row {i}: bad line {row['line']!r}", file=sys.stderr)
            continue
        try:
            covered, hexes_sorted = resolve_covered_hexes(row["covered-points"])
            amb, dest = prepare_test_case(
                row_index=i,
                test_name=row["test_name"].strip(),
                file_col=row["file"].strip(),
                line=line,
                covered=covered,
                hexes_sorted=hexes_sorted,
                new_tests=new_tests,
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
                f"Summary: each of the {ok} successful row(s) matched to a unique COVERED "
                "address (one instrumentation site per file/source line).",
                file=sys.stderr,
            )

    if ok == 0:
        return 1
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
