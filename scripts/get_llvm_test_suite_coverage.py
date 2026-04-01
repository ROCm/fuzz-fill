"""
Run LLVM tests via llvm-lit (default: ../llvm/test with --filter=CodeGen/AMDGPU) under
SanitizerCoverage, merge all raw .sancov outputs, symbolize once, and write an amalgamated
coverage outline. Override the run with --command (-c).

Workflow (matches scripts/check_expected_line_coverage.py for env):
  UBSAN_OPTIONS=coverage=1:coverage_dir=<dir>  (prepended before any existing UBSAN_OPTIONS)
  sancov -union  <many llc.*.sancov>  --output merged.sancov
  sancov -symbolize merged.sancov <llc-binary>  > merged.symcov
  sancov -print-coverage-stats merged.sancov <llc-binary>  (human-readable stats)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

# Run from LLVM build root (--cwd); paths are relative to that tree.
DEFAULT_TEST_COMMAND = (
    "./bin/llvm-lit ../llvm/test/ --filter=CodeGen/AMDGPU"
)


def get_repo_base(script_file: str) -> Path:
    return Path(script_file).resolve().parent.parent


def parse_args(base: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Amalgamate SanitizerCoverage from many llc runs into one outline."
    )
    parser.add_argument(
        "--command",
        "-c",
        default=None,
        help="Command line to run tests (parsed with shlex.split). Default: llvm-lit "
        "on ../llvm/test/ with --filter=CodeGen/AMDGPU. Not used with --skip-run.",
    )
    parser.add_argument(
        "--llvm-project",
        type=Path,
        default=None,
        help="Path to llvm-project root (default: <repo>/llvm-project)",
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=None,
        help="LLVM build tree (e.g. build/ or build-amdgpu/); llc and sancov are taken "
        "from <this>/bin/. Independent of --cwd. Default: <llvm-project>/build.",
    )
    parser.add_argument(
        "--coverage-dir",
        type=Path,
        default=None,
        help="Directory for raw .sancov files and merged outputs "
        "(default: <repo>/coverage_output/test_suite_<timestamp>)",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=None,
        help="Working directory for the test command (default: current directory).",
    )
    parser.add_argument(
        "--binary-name",
        default="llc",
        help="Instrumented binary basename for .sancov glob and symbolize (default: llc).",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Only merge/symbolize existing .sancov files in --coverage-dir (no new runs).",
    )
    parser.add_argument(
        "--union-batch",
        type=int,
        default=200,
        metavar="N",
        help="Max .sancov files per sancov -union invocation (avoid ARG_MAX).",
    )
    parser.add_argument(
        "--outline-json",
        type=Path,
        default=None,
        help="Write machine-readable outline (stats + paths) to this JSON file.",
    )
    args = parser.parse_args()
    if not args.skip_run and not args.command:
        args.command = DEFAULT_TEST_COMMAND
    args.llvm_project = args.llvm_project or base / "llvm-project"
    if args.build_dir is None:
        args.build_dir = args.llvm_project / "build"
    else:
        args.build_dir = Path(args.build_dir).resolve()
    if args.build_dir.name != "bin":
        args.build_dir = args.build_dir / "bin"
    args.cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd()
    if args.coverage_dir is not None:
        args.coverage_dir = Path(args.coverage_dir).resolve()
    else:
        args.coverage_dir = (
            base / "coverage_output" / f"test_suite_{int(time.time())}"
        ).resolve()
    return args


def collect_sancov_files(coverage_dir: Path, binary_name: str) -> list[Path]:
    files = sorted(coverage_dir.glob(f"{binary_name}.*.sancov"))
    return files


def union_sancov_batched(
    sancov_bin: Path,
    files: list[Path],
    output: Path,
    batch_size: int,
) -> None:
    """Merge many raw .sancov files using repeated sancov -union (batched)."""
    if not files:
        raise FileNotFoundError(
            f"No {output.name.split('.')[0]}.*.sancov files under {output.parent}"
        )
    if len(files) == 1:
        shutil.copy(files[0], output)
        return

    layer = list(files)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        tmp_path = Path(tmp)
        round_idx = 0
        while len(layer) > 1:
            nxt: list[Path] = []
            for i in range(0, len(layer), batch_size):
                batch = layer[i : i + batch_size]
                if len(batch) == 1:
                    nxt.append(batch[0])
                    continue
                out_f = tmp_path / f"u_{round_idx}_{len(nxt)}.sancov"
                cmd = [str(sancov_bin), "-union"] + [str(p) for p in batch] + [
                    "--output",
                    str(out_f),
                ]
                subprocess.run(cmd, check=True)
                nxt.append(out_f)
            layer = nxt
            round_idx += 1
        shutil.copy(layer[0], output)


def run_sancov_symbolize(
    sancov_bin: Path,
    merged_sancov: Path,
    binary: Path,
    symcov_out: Path,
) -> None:
    with symcov_out.open("w") as f:
        subprocess.run(
            [str(sancov_bin), "-symbolize", str(merged_sancov), str(binary)],
            check=True,
            stdout=f,
        )


def run_sancov_stats(
    sancov_bin: Path,
    merged_sancov: Path,
    binary: Path,
) -> str:
    proc = subprocess.run(
        [
            str(sancov_bin),
            "-print-coverage-stats",
            str(merged_sancov),
            str(binary),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout


_STATS_RE = re.compile(
    r"^(all-edges|cov-edges|all-functions|cov-functions):\s*(\d+)\s*$", re.MULTILINE
)


def parse_stats_text(stats_stdout: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for m in _STATS_RE.finditer(stats_stdout):
        key = m.group(1).replace("-", "_")
        out[key] = int(m.group(2))
    return out


def main() -> None:
    base = get_repo_base(__file__)
    args = parse_args(base)

    llc_bin = args.build_dir / args.binary_name
    sancov_bin = args.build_dir / "sancov"
    args.coverage_dir.mkdir(parents=True, exist_ok=True)

    run_returncode: int | None = None
    if not args.skip_run:
        cmd = shlex.split(args.command)
        if not cmd:
            raise SystemExit("empty command after shlex.split")
        env = os.environ.copy()
        cov_opts = f"coverage=1:coverage_dir={args.coverage_dir}"
        prev = env.get("UBSAN_OPTIONS", "").strip()
        env["UBSAN_OPTIONS"] = f"{cov_opts}:{prev}" if prev else cov_opts
        print(
            f"Running: UBSAN_OPTIONS={env['UBSAN_OPTIONS']!r} {' '.join(shlex.quote(x) for x in cmd)} "
            f"(cwd={args.cwd})"
        )
        result = subprocess.run(cmd, cwd=args.cwd, env=env)
        run_returncode = result.returncode
        print(f"Exit code: {run_returncode}")
    else:
        print("(--skip-run: not executing tests)")

    sancov_files = collect_sancov_files(args.coverage_dir, args.binary_name)
    print(f"Found {len(sancov_files)} raw .sancov file(s) for {args.binary_name}")

    if not sancov_bin.exists():
        print(f"ERROR: sancov not found at {sancov_bin}")
        raise SystemExit(1)
    if not llc_bin.exists():
        print(f"ERROR: binary not found at {llc_bin}")
        raise SystemExit(1)

    merged_sancov = args.coverage_dir / f"{args.binary_name}.merged.sancov"
    union_sancov_batched(
        sancov_bin, sancov_files, merged_sancov, args.union_batch
    )
    print(f"Merged raw coverage -> {merged_sancov}")

    symcov_path = args.coverage_dir / f"{args.binary_name}.merged.symcov"
    run_sancov_symbolize(sancov_bin, merged_sancov, llc_bin, symcov_path)
    print(f"Symbolized -> {symcov_path}")

    stats_text = run_sancov_stats(sancov_bin, merged_sancov, llc_bin)
    outline_txt = args.coverage_dir / "coverage_outline.txt"
    outline_txt.write_text(
        stats_text
        + "\n---\n"
        + f"merged_sancov: {merged_sancov}\n"
        + f"merged_symcov: {symcov_path}\n"
        + f"raw_sancov_count: {len(sancov_files)}\n"
    )
    print(f"Outline -> {outline_txt}")
    print()
    print(stats_text)

    if args.outline_json:
        payload = {
            "merged_sancov": str(merged_sancov),
            "merged_symcov": str(symcov_path),
            "raw_sancov_count": len(sancov_files),
            "stats": parse_stats_text(stats_text),
            "stats_raw": stats_text.strip(),
            "run_summary": {
                "command": args.command,
                "returncode": run_returncode,
            },
        }
        args.outline_json.write_text(json.dumps(payload, indent=2))
        print(f"JSON outline -> {args.outline_json}")


if __name__ == "__main__":
    main()
