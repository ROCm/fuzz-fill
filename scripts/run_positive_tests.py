#!/usr/bin/env python3
"""Run check_positve_test.py over a fixed list of (.ll test, pass, llc-args) cases."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_CHECK = Path(__file__).resolve().parent / "check_positve_test.py"
_DEFAULT_OUT = _REPO / "data" / "output" / "positive_tests"


def _pass_slug(pass_name: str) -> str:
    return pass_name.replace("/", "_").replace("\\", "_")


# Each entry: path to .ll (str or Path relative to repo or absolute), pass name, llc-args string (shell-style).
CASES: list[dict[str, str | Path]] = [
    {
        "test": _REPO / "fuzzer-tests/reduced/llc.real.2.spirv.reduced.ll",
        "pass": "spirv-emit-intrinsics",
        "llc_args": "-mtriple=spirv64-amd-amdhsa",
    },
    {
        "test": _REPO / "fuzzer-tests/reduced/llc.real.4.spirv.reduced.ll",
        "pass": "spirv-emit-intrinsics",
        "llc_args": "-mtriple=spirv64-amd-amdhsa",
    },
    {
        "test": _REPO / "fuzzer-tests/reduced/llc.real.34.reduced.ll",
        "pass": "spirv-emit-intrinsics",
        "llc_args": "-mtriple=spirv64-amd-amdhsa",
    },
    {
        "test": _REPO / "fuzzer-tests/reduced/llc.real.51.spirv.reduced.ll",
        "pass": "instruction-select",
        "llc_args": "-mtriple=spirv64-amd-amdhsa",
    },
    {
        "test": _REPO / "fuzzer-tests/reduced/llc.real.156.reduced.ll",
        "pass": "amdgpu-mark-last-scratch-load",
        "llc_args": "-mtriple=amdgcn-amd-amdhsa",
    },
    {
        "test": _REPO / "fuzzer-tests/reduced/llc.real.272.reduced.ll",
        "pass": "si-lower-sgpr-spills",
        "llc_args": "-O0 -mtriple=amdgcn-amd-amdhsa",
    },
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Loop over CASES and run check_positve_test.py for each."
    )
    p.add_argument("--llc", default="llc", help="Path to llc (passed to each check)")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUT,
        help=(
            f"Base directory; each run creates <base>/<YYYYMMDD-HHMMSS>/ with one subdir per case "
            f"(default base: {_DEFAULT_OUT})"
        ),
    )
    return p.parse_args()


def _resolve_test(p: str | Path) -> Path:
    path = Path(p)
    return path if path.is_absolute() else (_REPO / path).resolve()


def _interpret(combined: str, rc: int) -> str:
    if rc != 0:
        return "llc_error"
    if "DIFFERENT" in combined:
        return "positive"
    if "IDENTICAL" in combined:
        return "negative"
    return "unknown"


def main() -> int:
    args = parse_args()
    if not CASES:
        print("CASES is empty — add dict entries in run_positive_tests.py", file=sys.stderr)
        return 1

    out_base = args.output_dir.resolve()
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_root = out_base / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    print(f"Run output directory: {run_root}")

    failures = 0
    for i, case in enumerate(CASES, start=1):
        test = _resolve_test(case["test"])
        pass_name = str(case["pass"])
        llc_args = str(case.get("llc_args") or "")

        if not test.is_file():
            print(f"[{i}] SKIP missing file: {test}", file=sys.stderr)
            failures += 1
            continue

        case_dir = run_root / f"{test.stem}__{_pass_slug(pass_name)}"
        case_dir.mkdir(parents=True, exist_ok=True)

        # Use --llc-args=VALUE (one argv token). If VALUE starts with '-', passing
        # `--llc-args -mtriple=...` breaks: argparse does not consume -mtriple as the value.
        cmd: list[str] = [
            sys.executable,
            str(_CHECK),
            "--test",
            str(test),
            "--pass",
            pass_name,
            "--llc",
            args.llc,
        ]
        if llc_args:
            cmd.append(f"--llc-args={llc_args}")
        cmd.extend(["--output-dir", str(case_dir.resolve())])
        r = subprocess.run(cmd, capture_output=True, text=True)
        combined = (r.stdout or "") + (r.stderr or "")
        label = _interpret(combined, r.returncode)

        print(f"[{i}/{len(CASES)}] {test.name}  pass={pass_name}  ->  {label}")
        if r.returncode != 0:
            failures += 1
            tail = combined.strip().splitlines()[-5:]
            if tail:
                print("  last lines:", file=sys.stderr)
                for ln in tail:
                    print(f"    {ln}", file=sys.stderr)

    print(f"--- done: {len(CASES)} case(s), {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
