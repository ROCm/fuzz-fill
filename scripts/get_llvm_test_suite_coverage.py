"""
Run LLVM tests via llvm-lit (default: ../llvm/test with a configurable --filter) under
SanitizerCoverage, merge raw .sancov outputs per instrumented binary (default: llc and opt), symbolize each,
and write outlines. Override the run with --command (-c).

Workflow (matches scripts/check_expected_line_coverage.py for env):
  UBSAN_OPTIONS=coverage=1:coverage_dir=<dir>  (prepended before any existing UBSAN_OPTIONS)
  For each --binary NAME: sancov -union … → NAME.<merge-id>.sancov, then -symbolize and
  -print-coverage-stats with build-dir/bin/NAME.

  The merged .sancov basename prefix must equal the instrumented binary name (llvm sancov
  matches coverage files to the binary that way); do not use e.g. llcmerged.0.sancov.
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
DEFAULT_LIT_FILTER = "CodeGen/AMDGPU"

# Raw and merged files use <binary>.<digits>.sancov. Merged output uses MERGED_SANCOV_SUFFIX_ID
# (default 0); that exact file is excluded when collecting raw inputs. Prefix must match the
# binary basename for sancov -symbolize (see llvm/tools/sancov/sancov.cpp SancovFileRegex).
MERGED_SANCOV_SUFFIX_ID = "0"


def default_lit_command(lit_filter: str) -> str:
    return shlex.join(
        ["./bin/llvm-lit", "../llvm/test/", f"--filter={lit_filter}"]
    )


def get_repo_base(script_file: str) -> Path:
    return Path(script_file).resolve().parent.parent


def parse_args(base: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Amalgamate SanitizerCoverage from llvm-lit runs (per --binary)."
    )
    parser.add_argument(
        "--command",
        "-c",
        default=None,
        help="Command line to run tests (parsed with shlex.split). Default: llvm-lit "
        "on ../llvm/test/ with --filter from --filter. Not used with --skip-run.",
    )
    parser.add_argument(
        "--filter",
        dest="lit_filter",
        default=DEFAULT_LIT_FILTER,
        metavar="PATTERN",
        help="Value for lit --filter= when using the default command (default: %(default)s). "
        "Ignored when --command (-c) is set.",
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
        help="LLVM build tree (e.g. build/ or build-amdgpu/); each --binary and sancov are "
        "taken from <this>/bin/. Independent of --cwd. Default: <llvm-project>/build.",
    )
    parser.add_argument(
        "--coverage-dir",
        type=Path,
        default=None,
        help="Directory for raw .sancov files and merged outputs "
        "(default: <repo>/data/coverage_output/test_suite_<timestamp>)",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=None,
        help="Working directory for the test command (default: current directory).",
    )
    parser.add_argument(
        "--binary",
        dest="binaries",
        action="append",
        default=None,
        metavar="NAME",
        help="Instrumented tool basename under build-dir/bin (repeat for multiple). "
        f"Default when omitted: llc opt. Raw files: <name>.<digits>.sancov; merged: "
        f"<name>.{MERGED_SANCOV_SUFFIX_ID}.sancov.",
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
    if args.binaries is None:
        args.binaries = ["llc", "opt"]
    else:
        seen: set[str] = set()
        uniq: list[str] = []
        for b in args.binaries:
            if b not in seen:
                seen.add(b)
                uniq.append(b)
        args.binaries = uniq
    if not args.skip_run and not args.command:
        args.command = default_lit_command(args.lit_filter)
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
            base / "data" / "coverage_output" / f"test_suite_{int(time.time())}"
        ).resolve()
    return args


def collect_sancov_files(
    coverage_dir: Path,
    binary_name: str,
    merged_suffix_id: str = MERGED_SANCOV_SUFFIX_ID,
) -> list[Path]:
    """Raw <binary_name>.<digits>.sancov only; skips reserved merged name."""
    pat = re.compile(rf"^{re.escape(binary_name)}\.\d+\.sancov$")
    merged_name = f"{binary_name}.{merged_suffix_id}.sancov"
    return sorted(
        p
        for p in coverage_dir.iterdir()
        if p.is_file() and pat.match(p.name) and p.name != merged_name
    )


def union_sancov_batched(
    sancov_bin: Path,
    files: list[Path],
    output: Path,
    batch_size: int,
) -> None:
    """Merge many raw .sancov files using repeated sancov -union (batched)."""
    if not files:
        raise FileNotFoundError(
            f"No raw <binary>.<digits>.sancov inputs to merge under {output.parent}"
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

    if not sancov_bin.exists():
        print(f"ERROR: sancov not found at {sancov_bin}")
        raise SystemExit(1)

    outline_sections: list[str] = []
    per_binary: dict[str, dict[str, object]] = {}
    processed = 0

    for binary_name in args.binaries:
        tool_bin = args.build_dir / binary_name
        if not tool_bin.exists():
            print(f"ERROR: binary not found at {tool_bin}")
            raise SystemExit(1)

        sancov_files = collect_sancov_files(
            args.coverage_dir, binary_name, MERGED_SANCOV_SUFFIX_ID
        )
        print(f"Found {len(sancov_files)} raw .sancov file(s) for {binary_name}")
        if not sancov_files:
            print(
                f"WARNING: skipping {binary_name}: no raw <{binary_name}>.<digits>.sancov "
                f"in {args.coverage_dir}"
            )
            continue

        merged_sancov = (
            args.coverage_dir
            / f"{binary_name}.{MERGED_SANCOV_SUFFIX_ID}.sancov"
        )
        union_sancov_batched(
            sancov_bin, sancov_files, merged_sancov, args.union_batch
        )
        print(f"Merged raw coverage -> {merged_sancov}")

        symcov_path = (
            args.coverage_dir
            / f"{binary_name}.{MERGED_SANCOV_SUFFIX_ID}.symcov"
        )
        run_sancov_symbolize(sancov_bin, merged_sancov, tool_bin, symcov_path)
        print(f"Symbolized -> {symcov_path}")

        stats_text = run_sancov_stats(sancov_bin, merged_sancov, tool_bin)
        section = (
            f"=== {binary_name} ===\n"
            + stats_text.rstrip()
            + "\n---\n"
            + f"merged_sancov: {merged_sancov}\n"
            + f"merged_symcov: {symcov_path}\n"
            + f"raw_sancov_count: {len(sancov_files)}\n"
        )
        outline_sections.append(section)
        print()
        print(stats_text)

        per_binary[binary_name] = {
            "merged_sancov": str(merged_sancov),
            "merged_symcov": str(symcov_path),
            "raw_sancov_count": len(sancov_files),
            "stats": parse_stats_text(stats_text),
            "stats_raw": stats_text.strip(),
        }
        processed += 1

    if processed == 0:
        print("ERROR: no binaries produced coverage (no raw .sancov inputs).")
        raise SystemExit(1)

    outline_txt = args.coverage_dir / "coverage_outline.txt"
    outline_txt.write_text("\n".join(outline_sections).rstrip() + "\n")
    print(f"Outline -> {outline_txt}")

    if args.outline_json:
        payload = {
            "binaries": per_binary,
            "run_summary": {
                "command": args.command,
                "returncode": run_returncode,
            },
        }
        args.outline_json.write_text(json.dumps(payload, indent=2))
        print(f"JSON outline -> {args.outline_json}")


if __name__ == "__main__":
    main()
