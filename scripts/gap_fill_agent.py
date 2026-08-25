#!/usr/bin/env python3
"""Gap-fill agent helpers: queue generation, context packs, sancov hit checks."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from coverage.line_rules import normalize_llc_address_line_map  # noqa: E402
from coverage.pr_llc_settings import normalize_llvm_rel_path  # noqa: E402
from coverage.sancov import Sancov  # noqa: E402
from pr_check.checker import PrCheckerError, is_evaluable_run, parse_run_dir_name  # noqa: E402

import pandas as pd  # noqa: E402

SKIP_REASONS = {
    ("215196", "amdgpu", "AMDGPUInstCombineIntrinsic.cpp", 744): (
        "no llc instrumentation map row (InstCombine / opt path)"
    ),
}

SPIRV_DEFAULT_FLAGS = [
    "-O0 -mtriple=spirv64-amd-amdhsa",
    "-O1 -mtriple=spirv64-amd-amdhsa",
    "-O2 -mtriple=spirv64-amd-amdhsa",
    "-O3 -mtriple=spirv64-amd-amdhsa",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class GapEntry:
    pr_number: str
    backend: str
    file: str
    line: int
    text: str
    status: str
    attempts: int
    llc_map_csv: str
    gap_lines_csv: str
    settings_csv: str
    pr_run_dir: str
    skip_reason: str = ""


def _basename(path: str) -> str:
    return Path(path).name


def _load_manifest(root: Path) -> dict[tuple[str, str], dict[str, str]]:
    manifest_path = root / "data/gap-fill/inputs/manifest.csv"
    out: dict[tuple[str, str], dict[str, str]] = {}
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            out[(row["pr_number"], row["backend"])] = row
    return out


def _load_gap_text_from_runs(root: Path) -> dict[tuple[str, str, str, int], str]:
    """Map (pr, backend, absolute file path, line) -> uncovered-line text."""
    texts: dict[tuple[str, str, str, int], str] = {}
    runs_root = root / "data/pr-check/runs"
    if not runs_root.is_dir():
        return texts

    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir() or not is_evaluable_run(run_dir):
            continue
        try:
            pr_number, backend = parse_run_dir_name(run_dir.name)
        except PrCheckerError:
            continue

        gap_csv = run_dir / "commit_lines_report" / "target_lines_uncovered.csv"
        with gap_csv.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                continue
            for row in reader:
                file_path = (row.get("file") or "").strip()
                line_text = (row.get("line") or "").strip()
                if not file_path or not line_text:
                    continue
                texts[(str(pr_number), backend, file_path, int(line_text))] = (
                    row.get("text") or ""
                ).strip()
    return texts


def _gap_points(llc_map_csv: Path, file: str, line: int) -> list[dict[str, str]]:
    df = normalize_llc_address_line_map(pd.read_csv(llc_map_csv))
    target = df[(df["file"] == file) & (df["line"].astype(int) == line)]
    points: list[dict[str, str]] = []
    for _, row in target.iterrows():
        points.append(
            {
                "point": str(row["point"]),
                "covered_in_baseline": str(int(row["covered"])),
            }
        )
    return points


def generate_queue(root: Path, out_csv: Path) -> None:
    gaps_filled = root / "data/gap-fill/reports/gaps-filled.csv"
    manifest = _load_manifest(root)
    texts = _load_gap_text_from_runs(root)
    rows: list[GapEntry] = []

    with gaps_filled.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("filled", "").lower() == "yes":
                continue
            pr = row["pr_number"]
            backend = row["backend"]
            file_path = row["file"]
            line = int(row["line"])
            m = manifest[(pr, backend)]
            pr_run = root / "data/pr-check/runs" / f"{pr}-{backend}"
            skip_key = (pr, backend, _basename(file_path), line)
            skip_reason = SKIP_REASONS.get(skip_key, "")
            status = "skip" if skip_reason else "open"
            text = texts.get((pr, backend, file_path, line), "")
            rows.append(
                GapEntry(
                    pr_number=pr,
                    backend=backend,
                    file=file_path,
                    line=line,
                    text=text,
                    status=status,
                    attempts=0,
                    llc_map_csv=m["llc_address_line_map_csv"],
                    gap_lines_csv=m["gap_lines_csv"],
                    settings_csv=m.get("settings_csv", ""),
                    pr_run_dir=str(pr_run),
                    skip_reason=skip_reason,
                )
            )

    rows.sort(key=lambda r: (r.status != "open", r.pr_number, r.line))
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "pr_number",
        "backend",
        "file",
        "line",
        "text",
        "status",
        "attempts",
        "llc_map_csv",
        "gap_lines_csv",
        "settings_csv",
        "pr_run_dir",
        "skip_reason",
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for entry in rows:
            writer.writerow(
                {
                    "pr_number": entry.pr_number,
                    "backend": entry.backend,
                    "file": entry.file,
                    "line": entry.line,
                    "text": entry.text,
                    "status": entry.status,
                    "attempts": entry.attempts,
                    "llc_map_csv": entry.llc_map_csv,
                    "gap_lines_csv": entry.gap_lines_csv,
                    "settings_csv": entry.settings_csv,
                    "pr_run_dir": entry.pr_run_dir,
                    "skip_reason": entry.skip_reason,
                }
            )
    open_count = sum(1 for r in rows if r.status == "open")
    print(f"wrote {out_csv}: {open_count} open, {len(rows) - open_count} skip/other", file=sys.stderr)


def _added_lines_snippet(pr_run_dir: Path, rel_path: str, line: int, radius: int = 25) -> str:
    added_csv = pr_run_dir / "added-lines" / "added-lines.csv"
    if not added_csv.is_file():
        return f"# missing {added_csv}\n"
    rows: list[tuple[int, str]] = []
    with added_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["path"] != rel_path:
                continue
            rows.append((int(row["line_no"]), row.get("text", "")))
    rows.sort()
    selected = [f"{ln}: {txt}" for ln, txt in rows if abs(ln - line) <= radius]
    return "\n".join(selected) + ("\n" if selected else "")


def _source_snippet_docker(image: str, rel_path: str, line: int, radius: int = 40) -> str:
    start = max(1, line - radius)
    end = line + radius
    container_path = f"/work/llvm-project/{rel_path}"
    cmd = [
        "docker",
        "run",
        "--rm",
        image,
        "bash",
        "-lc",
        f"sed -n '{start},{end}p' {container_path} 2>/dev/null || true",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return "# docker not available\n"
    if proc.returncode != 0 and not proc.stdout.strip():
        return f"# could not read {container_path} from {image}\n"
    numbered = []
    for idx, text in enumerate(proc.stdout.splitlines(), start=start):
        prefix = ">>>" if idx == line else "   "
        numbered.append(f"{prefix} {idx}: {text}")
    return "\n".join(numbered) + ("\n" if numbered else "")


def build_context(
    root: Path,
    pr_number: str,
    line: int,
    out_dir: Path,
    *,
    image: str | None = None,
) -> None:
    queue_csv = root / "data/gap-fill/agent/gap-queue.csv"
    entry: GapEntry | None = None
    with queue_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["pr_number"] == pr_number and int(row["line"]) == line:
                entry = GapEntry(
                    pr_number=row["pr_number"],
                    backend=row["backend"],
                    file=row["file"],
                    line=int(row["line"]),
                    text=row.get("text", ""),
                    status=row.get("status", "open"),
                    attempts=int(row.get("attempts") or 0),
                    llc_map_csv=row["llc_map_csv"],
                    gap_lines_csv=row["gap_lines_csv"],
                    settings_csv=row.get("settings_csv", ""),
                    pr_run_dir=row["pr_run_dir"],
                    skip_reason=row.get("skip_reason", ""),
                )
                break
    if entry is None:
        raise SystemExit(f"gap not found in queue: pr={pr_number} line={line}")

    rel_path = normalize_llvm_rel_path(entry.file)
    llc_map = Path(entry.llc_map_csv)
    points = _gap_points(llc_map, entry.file, entry.line)
    pr_run_dir = Path(entry.pr_run_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    gap_json = {
        "pr_number": entry.pr_number,
        "backend": entry.backend,
        "file": entry.file,
        "rel_path": rel_path,
        "line": entry.line,
        "text": entry.text,
        "status": entry.status,
        "attempts": entry.attempts,
        "gap_points": points,
        "llc_map_csv": entry.llc_map_csv,
        "gap_lines_csv": entry.gap_lines_csv,
        "settings_csv": entry.settings_csv,
        "skip_reason": entry.skip_reason,
        "requires_global_isel_0": any(
            marker in entry.file
            for marker in ("SIISelLowering", "SIInsertWaitcnts", "/SI")
        ),
        "requires_global_isel_1": "CallLowering" in entry.file,
    }
    (out_dir / "gap.json").write_text(json.dumps(gap_json, indent=2) + "\n", encoding="utf-8")

    added_snippet = _added_lines_snippet(pr_run_dir, rel_path, entry.line)
    (out_dir / "added-lines.snippet").write_text(added_snippet, encoding="utf-8")

    image_ref = image or f"fuzz-fill-test:llvm-pr-{entry.pr_number}"
    source_snippet = _source_snippet_docker(image_ref, rel_path, entry.line)
    (out_dir / "source.snippet").write_text(source_snippet, encoding="utf-8")

    settings_out = out_dir / "candidate_test_settings.csv"
    if entry.settings_csv and Path(entry.settings_csv).is_file():
        settings_out.write_text(Path(entry.settings_csv).read_text(encoding="utf-8"), encoding="utf-8")
    else:
        with settings_out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["llc_flags"])
            for flags in SPIRV_DEFAULT_FLAGS:
                writer.writerow([flags])

    verify_sh = out_dir / "verify.sh"
    verify_sh.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
REPO="{root}"
CTX="{out_dir}"
PR="{entry.pr_number}"
LINE="{entry.line}"
FLAGS="$(tr -d '\\n' < "$CTX/llc_flags.txt")"
exec "$REPO/scripts/verify-gap-candidate.sh" \\
  --pr-id "$PR" \\
  --file "{entry.file}" \\
  --line "$LINE" \\
  --llc-map-csv "{entry.llc_map_csv}" \\
  --test "$CTX/candidate.ll" \\
  --llc-flags "$FLAGS"
""",
        encoding="utf-8",
    )
    verify_sh.chmod(0o755)

    prompt = f"""Fill coverage gap PR {entry.pr_number} ({entry.backend}) at {rel_path}:{entry.line}.

Read these files in order:
1. {out_dir}/gap.json
2. {out_dir}/source.snippet
3. {out_dir}/added-lines.snippet
4. {out_dir}/candidate_test_settings.csv

Write:
- {out_dir}/candidate.ll  (minimal valid LLVM IR)
- {out_dir}/llc_flags.txt  (single line from candidate_test_settings.csv)
- {out_dir}/idea.md         (why this IR should hit the gap)

Then run: {out_dir}/verify.sh

Report HIT or MISS and summarize idea.md.
"""
    (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    print(f"wrote context: {out_dir}", file=sys.stderr)


def check_hit(
    *,
    llc_map_csv: Path,
    file: str,
    line: int,
    sancov_file: Path,
    sancov_bin: Path,
) -> int:
    points = _gap_points(llc_map_csv, file, line)
    if not points:
        print(f"MISS: no llc map points for {file}:{line}", file=sys.stderr)
        return 1

    target_points = {p["point"] for p in points}
    sancov = Sancov(sancov_bin)
    covered = sancov.get_covered_addresses(sancov_file)
    hit = sorted(target_points & covered)
    if hit:
        print(f"HIT: {file}:{line} points={','.join(hit)}")
        return 0
    print(
        f"MISS: {file}:{line} need={','.join(sorted(target_points))} "
        f"covered_sample={','.join(sorted(list(covered)[:5]))}",
        file=sys.stderr,
    )
    return 1


def update_queue_status(
    queue_csv: Path,
    *,
    pr_number: str,
    line: int,
    status: str,
    increment_attempts: bool = False,
) -> None:
    rows: list[dict[str, str]] = []
    with queue_csv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        for row in reader:
            if row["pr_number"] == pr_number and int(row["line"]) == line:
                if increment_attempts:
                    row["attempts"] = str(int(row.get("attempts") or 0) + 1)
                row["status"] = status
            rows.append(row)
    with queue_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def pick_next_gap(queue_csv: Path, max_attempts: int) -> dict[str, str] | None:
    rows: list[dict[str, str]] = []
    with queue_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    open_rows = [
        r
        for r in rows
        if r.get("status") == "open" and int(r.get("attempts") or 0) < max_attempts
    ]
    if not open_rows:
        return None
    open_rows.sort(key=lambda r: (int(r.get("attempts") or 0), r["pr_number"], int(r["line"])))
    return open_rows[0]


def main() -> None:
    root = repo_root()
    parser = argparse.ArgumentParser(description="Gap-fill agent helpers")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_queue = sub.add_parser("generate-queue", help="write data/gap-fill/agent/gap-queue.csv")
    p_queue.add_argument(
        "--out",
        type=Path,
        default=root / "data/gap-fill/agent/gap-queue.csv",
    )

    p_ctx = sub.add_parser("build-context", help="write per-gap context directory")
    p_ctx.add_argument("--pr", required=True)
    p_ctx.add_argument("--line", type=int, required=True)
    p_ctx.add_argument("--out", type=Path, required=True)
    p_ctx.add_argument("--image", default="")

    p_check = sub.add_parser("check-hit", help="check sancov against gap points")
    p_check.add_argument("--llc-map-csv", type=Path, required=True)
    p_check.add_argument("--file", required=True)
    p_check.add_argument("--line", type=int, required=True)
    p_check.add_argument("--sancov-file", type=Path, required=True)
    p_check.add_argument("--sancov", type=Path, required=True)

    p_pick = sub.add_parser("pick-next", help="print next open gap TSV row")
    p_pick.add_argument(
        "--queue",
        type=Path,
        default=root / "data/gap-fill/agent/gap-queue.csv",
    )
    p_pick.add_argument("--max-attempts", type=int, default=5)

    p_update = sub.add_parser("update-queue", help="update one gap row status/attempts")
    p_update.add_argument("--queue", type=Path, default=root / "data/gap-fill/agent/gap-queue.csv")
    p_update.add_argument("--pr", required=True)
    p_update.add_argument("--line", type=int, required=True)
    p_update.add_argument("--status", required=True)
    p_update.add_argument("--increment-attempts", action="store_true")

    args = parser.parse_args()
    if args.cmd == "generate-queue":
        generate_queue(root, args.out)
    elif args.cmd == "build-context":
        queue_csv = root / "data/gap-fill/agent/gap-queue.csv"
        if not queue_csv.is_file():
            generate_queue(root, queue_csv)
        build_context(
            root,
            args.pr,
            args.line,
            args.out,
            image=args.image or None,
        )
    elif args.cmd == "check-hit":
        raise SystemExit(
            check_hit(
                llc_map_csv=args.llc_map_csv,
                file=args.file,
                line=args.line,
                sancov_file=args.sancov_file,
                sancov_bin=args.sancov,
            )
        )
    elif args.cmd == "pick-next":
        nxt = pick_next_gap(args.queue, args.max_attempts)
        if nxt is None:
            return
        print(
            "\t".join(
                [
                    nxt["pr_number"],
                    nxt["backend"],
                    nxt["file"],
                    nxt["line"],
                    nxt.get("attempts", "0"),
                ]
            )
        )
    elif args.cmd == "update-queue":
        update_queue_status(
            args.queue,
            pr_number=args.pr,
            line=args.line,
            status=args.status,
            increment_attempts=args.increment_attempts,
        )


if __name__ == "__main__":
    main()
