#!/usr/bin/env python3
"""Check whether a test is 'positive' for a given pass.

Current behavior:
- run llc with -print-before=<pass_name> on the given test input
- run llc again with -print-after=<pass_name>
- write each full llc output under --output-dir as:
  - before-pass-<pass>.txt
  - after-pass-<pass>.txt
- print only concise status lines to the terminal
"""

import argparse
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "output" / "positive_tests"


def _pass_file_slug(pass_name: str) -> str:
    """Safe filename fragment for a pass id (LLVM pass names may contain odd chars)."""
    return pass_name.replace("/", "_").replace("\\", "_")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run llc print-before and print-after for a given pass."
    )
    parser.add_argument("--test", required=True, type=Path, help="Input test file path")
    parser.add_argument("--pass", dest="pass_name", required=True, help="Pass name")
    parser.add_argument("--llc", default="llc", help="Path to llc executable (default: llc from PATH)")
    parser.add_argument(
        "--llc-args",
        default="",
        help="Extra llc argv (shell-style, e.g. '-O1 -mtriple=spirv64-unknown-unknown'); empty is ignored",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help=f"Directory for captured llc output (default: {_DEFAULT_OUTPUT_DIR})",
    )
    return parser.parse_args()


def run_llc(
    llc: str,
    extra: list[str],
    pass_opt: str,
    test_path: Path,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        llc,
        "-o",
        "-",
        *extra,
        pass_opt,
        str(test_path.resolve()),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def emit_result(
    label: str,
    result: subprocess.CompletedProcess[str],
    out_path: Path,
) -> int:
    parts: list[str] = []
    if result.stdout:
        parts.append(result.stdout)
    if result.stderr:
        parts.append(result.stderr)
    out_path.write_text("".join(parts), encoding="utf-8")
    if result.returncode == 0:
        print(f"[ok] {label} -> {out_path}")
    else:
        print(f"[fail:{result.returncode}] {label} -> {out_path}", file=sys.stderr)
    return result.returncode


def _drop_first_line(s: str) -> str:
    _, _, rest = s.partition("\n")
    return rest


def main() -> None:
    args = parse_args()
    extra = shlex.split(args.llc_args.strip()) if args.llc_args.strip() else []
    test_path = args.test.resolve()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir_name = f"{_pass_file_slug(args.pass_name)}_{ts}"
    out_dir = args.output_dir.resolve() / run_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _pass_file_slug(args.pass_name)
    before_path = out_dir / f"before-pass-{slug}.txt"
    after_path = out_dir / f"after-pass-{slug}.txt"

    print_before = run_llc(
        args.llc,
        extra,
        f"-print-before={args.pass_name}",
        test_path,
    )
    before_rc = emit_result(f"-print-before={args.pass_name}", print_before, before_path)

    print_after = run_llc(
        args.llc,
        extra,
        f"-print-after={args.pass_name}",
        test_path,
    )
    after_rc = emit_result(f"-print-after={args.pass_name}", print_after, after_path)

    before_body = _drop_first_line(before_path.read_text(encoding="utf-8"))
    after_body = _drop_first_line(after_path.read_text(encoding="utf-8"))
    if before_body == after_body:
        print("[compare] before/after (ignoring first line): IDENTICAL")
    else:
        print("[compare] before/after (ignoring first line): DIFFERENT")

    if before_rc != 0 or after_rc != 0:
        sys.exit(before_rc or after_rc)


if __name__ == "__main__":
    main()
