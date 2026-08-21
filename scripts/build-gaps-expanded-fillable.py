#!/usr/bin/env python3
"""Build a gaps-expanded CSV from completed pr-check runs, excluding unfillable gaps."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_GITHUB_REPO = "llvm/llvm-project"

DEBUG_RE = re.compile(
    r"\b("
    r"dbgs\s*\("
    r"|LLVM_DEBUG\s*\("
    r"|DEBUG_WITH_TYPE\s*\("
    r"|errs\s*\(\)"
    r")",
    re.IGNORECASE,
)
ASSERT_RE = re.compile(r"\bassert\s*\(", re.IGNORECASE)
CONTROL_FLOW_RE = re.compile(
    r"^\s*(?:}?\s*)?(?:else\s+)?(?:if|while|for)\s*\(",
    re.IGNORECASE,
)
RETURN_RE = re.compile(r"^\s*return\b", re.IGNORECASE)


@dataclass(frozen=True)
class GapDecision:
    include: bool
    reason: str = ""


def classify_gap_text(text: str) -> GapDecision:
    stripped = (text or "").strip()
    if not stripped:
        return GapDecision(True, "")
    if DEBUG_RE.search(stripped):
        return GapDecision(False, "debug")
    if ASSERT_RE.search(stripped):
        return GapDecision(False, "assert")
    if CONTROL_FLOW_RE.search(stripped):
        return GapDecision(False, "control_flow")
    if RETURN_RE.search(stripped):
        return GapDecision(False, "return")
    return GapDecision(True, "")


def abs_path_to_rel_path(file_path: str) -> str:
    normalized = file_path.replace("\\", "/")
    marker = "/llvm/"
    idx = normalized.find(marker)
    if idx >= 0:
        return normalized[idx + 1 :]
    return normalized.lstrip("/")


def parse_run_dir_name(name: str) -> tuple[str, str]:
    pr_number, backend = name.rsplit("-", 1)
    return pr_number, backend


def is_completed_pr_check_run(run_dir: Path) -> bool:
    return (run_dir / "commit_lines_report" / "target_lines_uncovered.csv").is_file()


def iter_gap_rows(
    *,
    pr_check_runs_root: Path,
    github_repo: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    included: list[dict[str, str]] = []
    excluded: list[dict[str, str]] = []

    for run_dir in sorted(pr_check_runs_root.iterdir()):
        if not run_dir.is_dir() or not is_completed_pr_check_run(run_dir):
            continue

        pr_number, backend = parse_run_dir_name(run_dir.name)
        gap_csv = run_dir / "commit_lines_report" / "target_lines_uncovered.csv"
        with gap_csv.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                continue
            for row in reader:
                file_path = (row.get("file") or "").strip()
                if not file_path:
                    continue
                line_text = (row.get("line") or "").strip()
                if not line_text:
                    continue
                line = int(line_text)
                text = (row.get("text") or "").strip()
                rel_path = abs_path_to_rel_path(file_path)
                location = f"{rel_path}:{line}"
                base = {
                    "PR": f"https://github.com/{github_repo}/pull/{pr_number}",
                    "Backend": backend,
                    "Line": str(line),
                    "Location": location,
                    "Text": text,
                }
                decision = classify_gap_text(text)
                if decision.include:
                    included.append(base)
                else:
                    excluded.append({**base, "ExcludeReason": decision.reason})

    return included, excluded


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pr-check-runs-root",
        type=Path,
        default=root / "data/pr-check/runs",
        help="Directory with completed pr-check run artifacts",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "data/gap-fill/inputs/gaps-expanded-fillable.csv",
        help="Filtered gaps-expanded CSV for gap-fill-from-gaps-expanded.sh",
    )
    parser.add_argument(
        "--excluded-output",
        type=Path,
        default=root / "data/gap-fill/inputs/gaps-expanded-excluded.csv",
        help="Audit CSV for filtered-out gap lines",
    )
    parser.add_argument(
        "--github-repo",
        default=DEFAULT_GITHUB_REPO,
        help=f"GitHub repo for PR URLs (default: {DEFAULT_GITHUB_REPO})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.pr_check_runs_root.is_dir():
        print(f"error: pr-check runs root not found: {args.pr_check_runs_root}", file=sys.stderr)
        return 1

    included, excluded = iter_gap_rows(
        pr_check_runs_root=args.pr_check_runs_root.resolve(),
        github_repo=args.github_repo,
    )
    write_csv(
        args.output.resolve(),
        included,
        fieldnames=["PR", "Backend", "Line", "Location", "Text"],
    )
    write_csv(
        args.excluded_output.resolve(),
        excluded,
        fieldnames=["PR", "Backend", "Line", "Location", "Text", "ExcludeReason"],
    )

    print(
        f"wrote {args.output}: {len(included)} fillable gap line(s)",
        file=sys.stderr,
    )
    print(
        f"wrote {args.excluded_output}: {len(excluded)} excluded gap line(s)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
