#!/usr/bin/env python3
"""
Create per-line reduce harness directories from incremental/new_coverage.csv and
matching folders under candidate_tests/.

CSV columns: test_name, file, line, covered-points
(test_name is a directory under --candidate-tests containing test.sh).

Each test.sh records the instrumented llc invocation (binary, flags, .bc path).
Llvm flags on that command are copied into interesting_ir.sh and extract_*
pipeline steps (config ``llc_O``). interesting_mir.sh uses the same COVERED
sancov check as interesting_ir.sh. Use ``--mir-codegen-only`` when the pass
under test is codegen-only (e.g. amdgpu-isel): resume from extracted MIR with
``LLC_FLAGS`` instead of ``-run-pass``.
Each output directory mirrors example/amd/new-test-1 (config.json,
interesting_ir.sh, and the copied .bc). COVERED in interesting_ir.sh is the
lowest hex among addresses for that row.

Each config.json sets output_dir to a reduced subdirectory next to it so
reduction artifacts stay inside the case directory.

With --llvm-bin, runs python -m reduce --config <case>/config.json for each case.

Use --n to process only the first N data rows of the CSV (after the header).

Use --pipeline to choose reduction passes (comma-separated ids), e.g.
``llvm_reduce_ir,extract_mir_before_pass,llvm_reduce_mir`` as in
example/amd/si-i1-copies. When the pipeline includes extract_* or
llvm_reduce_mir, pass --pass-under-test and --mtriple; use ``--mir-codegen-only``
for ISel/codegen-only passes. Templates: ``interesting_mir_codegen.sh`` or
``interesting_mir.sh`` (machine ``-run-pass``) under ``--template-dir``.
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


def _known_pass_ids() -> frozenset[str]:
    src = str(_repo_root() / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from reduce.pass_registry import known_pass_ids

    return known_pass_ids()


_PASSES_NEEDING_EXTRACT_OPTS = frozenset(
    {"extract_mir_before_pass", "extract_ir_before_pass"}
)
_PASSES_NEEDING_INTERESTING_MIR = frozenset({"llvm_reduce_mir"})


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
    """Parse candidate_tests/<test_name>/test.sh for llc binary, flags, and .bc path."""
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


def _llc_flags_to_llc_O(llc_flags: tuple[str, ...]) -> str:
    return " ".join(llc_flags)


def _mir_template_basename(*, mir_codegen_only: bool) -> str:
    return "interesting_mir_codegen.sh" if mir_codegen_only else "interesting_mir.sh"


def _apply_mir_template_common(
    template_text: str,
    *,
    template_name: str,
    covered: str,
    llvm_bin: Path,
) -> str:
    out, n = re.subn(
        r'^LLVM_BIN=.*$',
        f'LLVM_BIN={llvm_bin}',
        template_text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise ValueError(
            f'Template {template_name} must contain exactly one LLVM_BIN=... line.'
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
            f'Template {template_name} must contain exactly one COVERED="..." line.'
        )
    return out


def _apply_mir_template_llc_flags(
    out: str,
    *,
    template_name: str,
    llc_flags: tuple[str, ...],
) -> str:
    flags_value = " ".join(llc_flags)
    if re.search(r'^LLC_FLAGS=', out, flags=re.MULTILINE):
        out, n = re.subn(
            r'^LLC_FLAGS=.*$',
            f'LLC_FLAGS="{flags_value}"',
            out,
            count=1,
            flags=re.MULTILINE,
        )
        if n != 1:
            raise ValueError(f"Failed to set LLC_FLAGS in {template_name}.")
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
                f'Template {template_name} must contain LLC=$LLVM_BIN/llc '
                "or an LLC_FLAGS= line."
            )
    out, n = re.subn(
        r'(\$LLC)\s+(\$LLC_FLAGS\s+)?',
        r'\1 $LLC_FLAGS ',
        out,
        count=1,
    )
    if n != 1:
        raise ValueError(
            f'Template {template_name} must invoke llc as $LLC [$LLC_FLAGS] ... "$1".'
        )
    return out


def _apply_mir_template_mtriple(out: str, *, template_name: str, mtriple: str) -> str:
    out, n = re.subn(
        r'-mtriple=[^\s"]+',
        f'-mtriple={mtriple}',
        out,
        count=1,
    )
    if n != 1:
        raise ValueError(
            f'Template {template_name} must contain -mtriple=<triple> on the llc line.'
        )
    return out


def render_interesting_mir(
    template_text: str,
    *,
    template_name: str,
    covered: str,
    llvm_bin: Path,
    mtriple: str,
    mir_codegen_only: bool,
    llc_flags: tuple[str, ...],
    pass_under_test: str | None,
) -> str:
    out = _apply_mir_template_common(
        template_text,
        template_name=template_name,
        covered=covered,
        llvm_bin=llvm_bin,
    )
    out = _apply_mir_template_mtriple(out, template_name=template_name, mtriple=mtriple)

    if mir_codegen_only:
        return _apply_mir_template_llc_flags(
            out, template_name=template_name, llc_flags=llc_flags
        )

    if pass_under_test is None:
        raise ValueError("pass_under_test is required for machine-pass interesting_mir.sh.")
    out, n = re.subn(
        r'-run-pass=[^\s"]+',
        f'-run-pass={pass_under_test}',
        out,
        count=1,
    )
    if n != 1:
        raise ValueError(
            f'Template {template_name} must contain -run-pass=<pass> on the llc line.'
        )
    return out


def parse_pipeline_arg(value: str) -> list[str]:
    ids = [p.strip() for p in value.split(",") if p.strip()]
    if not ids:
        raise ValueError("--pipeline must list at least one pass id.")
    known = _known_pass_ids()
    bad = [p for p in ids if p not in known]
    if bad:
        raise ValueError(
            f"Unknown pipeline pass id(s): {', '.join(bad)}. "
            f"Known ids: {', '.join(sorted(known))}."
        )
    return ids


def creduce_interesting_script(pass_ids: list[str], creduce_index: int) -> str:
    """Interesting script for creduce: match the artifact produced by the prior step."""
    if creduce_index <= 0:
        return "interesting_ir.sh"
    prev = pass_ids[creduce_index - 1]
    if prev == "llvm_reduce_mir":
        return "interesting_mir.sh"
    return "interesting_ir.sh"


def build_pipeline_steps(
    pass_ids: list[str],
    *,
    pass_under_test: str | None,
    mtriple: str | None,
    llc_flags: tuple[str, ...],
    extract_mir_output: str | None,
    extract_ir_output: str | None,
    creduce_n: int | None,
) -> list[dict]:
    steps: list[dict] = []
    llc_O = _llc_flags_to_llc_O(llc_flags)
    for i, pid in enumerate(pass_ids):
        if pid == "llvm_reduce_ir":
            steps.append(
                {
                    "id": "llvm_reduce_ir",
                    "parameters": {"interesting": "interesting_ir.sh"},
                }
            )
        elif pid == "llvm_reduce_mir":
            steps.append(
                {
                    "id": "llvm_reduce_mir",
                    "parameters": {"interesting_mir": "interesting_mir.sh"},
                }
            )
        elif pid == "extract_mir_before_pass":
            params: dict[str, str] = {
                "pass_under_test": pass_under_test or "",
                "mtriple": mtriple or "",
                "llc_O": llc_O,
            }
            if extract_mir_output:
                params["extract_mir_output"] = extract_mir_output
            steps.append({"id": pid, "parameters": params})
        elif pid == "extract_ir_before_pass":
            params = {
                "pass_under_test": pass_under_test or "",
                "mtriple": mtriple or "",
                "llc_O": llc_O,
            }
            if extract_ir_output:
                params["extract_ir_before_output"] = extract_ir_output
            steps.append({"id": pid, "parameters": params})
        elif pid == "creduce":
            params: dict[str, str | int] = {
                "interesting": creduce_interesting_script(pass_ids, i),
            }
            if creduce_n is not None:
                params["n"] = creduce_n
            steps.append({"id": "creduce", "parameters": params})
        elif pid == "snapshot":
            steps.append({"id": "snapshot"})
        else:
            raise ValueError(f"Unhandled pass id: {pid}")
    return steps


def validate_pipeline_cli(
    pass_ids: list[str],
    *,
    pass_under_test: str | None,
    mtriple: str | None,
    template_dir: Path,
    mir_codegen_only: bool,
) -> None:
    needs_extract = _PASSES_NEEDING_EXTRACT_OPTS & set(pass_ids)
    if needs_extract:
        if not pass_under_test:
            raise ValueError(
                f"--pass-under-test is required when the pipeline includes "
                f"{', '.join(sorted(needs_extract))}."
            )
        if not mtriple:
            raise ValueError(
                f"--mtriple is required when the pipeline includes "
                f"{', '.join(sorted(needs_extract))}."
            )
    if _PASSES_NEEDING_INTERESTING_MIR & set(pass_ids):
        if not pass_under_test:
            raise ValueError(
                "--pass-under-test is required when the pipeline includes llvm_reduce_mir."
            )
        mir_name = _mir_template_basename(mir_codegen_only=mir_codegen_only)
        mir_template = template_dir / mir_name
        if not mir_template.is_file():
            raise ValueError(
                f"Pipeline includes llvm_reduce_mir but {mir_template} is missing. "
                f"Use --template-dir with {mir_name} (e.g. example/amd/new-test-1)."
            )


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
    candidate_tests: Path,
    out_parent: Path,
    template_interesting: str,
    pipeline_steps: list[dict],
    template_interesting_mir: str | None,
    mir_template_name: str | None,
    pass_under_test: str | None,
    mtriple: str | None,
    mir_codegen_only: bool,
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

    test_info = parse_test_sh(candidate_tests / test_name / "test.sh")
    input_name = copy_input_bc(test_info, dest_dir)

    reduced_dir = (dest_dir / "reduced").resolve()
    config = {
        "input": input_name,
        "file": llvm_rel_source_path(file_col),
        "line": line,
        "replacement": "",
        "output_dir": str(reduced_dir),
        "pipeline": pipeline_steps,
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

    if template_interesting_mir is not None:
        if pass_under_test is None or mtriple is None:
            raise ValueError(
                "pass_under_test and mtriple are required to generate interesting_mir.sh."
            )
        (dest_dir / "interesting_mir.sh").write_text(
            render_interesting_mir(
                template_interesting_mir,
                template_name=mir_template_name or "interesting_mir.sh",
                covered=covered,
                llvm_bin=test_info.llvm_bin,
                mtriple=mtriple,
                mir_codegen_only=mir_codegen_only,
                llc_flags=test_info.llc_flags,
                pass_under_test=pass_under_test,
            ),
            encoding="utf-8",
        )
        (dest_dir / "interesting_mir.sh").chmod(0o755)

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
        "--candidate-tests",
        type=Path,
        required=True,
        help="candidate_tests directory; each CSV test_name is a subdirectory with test.sh.",
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
        help="Directory containing interesting_ir.sh (coverage-based template).",
    )
    p.add_argument(
        "--pipeline",
        default="llvm_reduce_ir",
        metavar="PASS_IDS",
        help=(
            "Comma-separated reduce pass ids for config.json pipeline "
            "(default: llvm_reduce_ir). Examples: llvm_reduce_ir,creduce; "
            "llvm_reduce_ir,extract_mir_before_pass,llvm_reduce_mir."
        ),
    )
    p.add_argument(
        "--with-creduce",
        action="store_true",
        help=(
            "Append creduce to --pipeline if not already present (creduce uses "
            "interesting_ir.sh when it follows llvm_reduce_ir)."
        ),
    )
    p.add_argument(
        "--creduce-n",
        type=int,
        default=None,
        metavar="N",
        help="Pass creduce --n (parallelism) for creduce pipeline steps.",
    )
    p.add_argument(
        "--pass-under-test",
        default=None,
        metavar="PASS",
        help=(
            "LLVM pass id for extract_*_before_pass (required with those passes). "
            "Also sets -run-pass= in interesting_mir.sh unless --mir-codegen-only."
        ),
    )
    p.add_argument(
        "--mtriple",
        default=None,
        help="Target triple for extract_*_before_pass and interesting_mir.sh.",
    )
    p.add_argument(
        "--mir-codegen-only",
        action="store_true",
        help=(
            "interesting_mir.sh resumes codegen from MIR (LLC_FLAGS, -o /dev/null) "
            "instead of llc -run-pass= (for ISel/codegen-only passes such as "
            "amdgpu-isel). Uses interesting_mir_codegen.sh from --template-dir."
        ),
    )
    p.add_argument(
        "--extract-mir-output",
        default=None,
        metavar="BASENAME",
        help="Optional extract_mir_output basename for extract_mir_before_pass.",
    )
    p.add_argument(
        "--extract-ir-output",
        default=None,
        metavar="BASENAME",
        help="Optional extract_ir_before_output basename for extract_ir_before_pass.",
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

    candidate_tests = args.candidate_tests.resolve()
    llvm_bin = args.llvm_bin.resolve() if args.llvm_bin is not None else None
    out_parent = args.output.resolve()
    out_parent.mkdir(parents=True, exist_ok=True)

    template_dir = args.template_dir.resolve()
    template_path = template_dir / "interesting_ir.sh"
    template_interesting = template_path.read_text(encoding="utf-8")

    try:
        pass_ids = parse_pipeline_arg(args.pipeline)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    if args.with_creduce and "creduce" not in pass_ids:
        pass_ids.append("creduce")

    if args.creduce_n is not None and args.creduce_n < 1:
        print("--creduce-n must be a positive integer.", file=sys.stderr)
        return 2

    try:
        validate_pipeline_cli(
            pass_ids,
            pass_under_test=args.pass_under_test,
            mtriple=args.mtriple,
            template_dir=template_dir,
            mir_codegen_only=args.mir_codegen_only,
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    mir_template_name: str | None = None
    template_interesting_mir: str | None = None
    if "llvm_reduce_mir" in pass_ids:
        mir_template_name = _mir_template_basename(
            mir_codegen_only=args.mir_codegen_only
        )
        template_interesting_mir = (
            template_dir / mir_template_name
        ).read_text(encoding="utf-8")

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
            test_info = parse_test_sh(candidate_tests / row["test_name"].strip() / "test.sh")
            row_pipeline = build_pipeline_steps(
                pass_ids,
                pass_under_test=args.pass_under_test,
                mtriple=args.mtriple,
                llc_flags=test_info.llc_flags,
                extract_mir_output=args.extract_mir_output,
                extract_ir_output=args.extract_ir_output,
                creduce_n=args.creduce_n,
            )
            amb, dest = prepare_test_case(
                row_index=i,
                test_name=row["test_name"].strip(),
                file_col=row["file"].strip(),
                line=line,
                covered=covered,
                hexes_sorted=hexes_sorted,
                candidate_tests=candidate_tests,
                out_parent=out_parent,
                template_interesting=template_interesting,
                pipeline_steps=row_pipeline,
                template_interesting_mir=template_interesting_mir,
                mir_template_name=mir_template_name,
                pass_under_test=args.pass_under_test,
                mtriple=args.mtriple,
                mir_codegen_only=args.mir_codegen_only,
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
