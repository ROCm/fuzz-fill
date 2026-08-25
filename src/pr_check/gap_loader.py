# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Load uncovered gap lines from completed pr-check run artifacts."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from pr_check.checker import PrCheckerError, is_evaluable_run, parse_run_dir_name

TARGET_LINES_UNCOVERED = Path("commit_lines_report") / "target_lines_uncovered.csv"


@dataclass(frozen=True)
class UncoveredGapLine:
    pr_number: int
    backend: str
    run_dir: Path
    file_path: str
    line: int
    text: str


def _gap_line_no(row: dict[str, str]) -> int | None:
    for key in ("line", "line_no"):
        raw = (row.get(key) or "").strip()
        if raw:
            return int(raw)
    return None


def iter_uncovered_gap_lines(pr_check_runs_root: Path) -> Iterator[UncoveredGapLine]:
    """Yield uncovered lines from each completed pr-check run under *pr_check_runs_root*."""
    if not pr_check_runs_root.is_dir():
        return

    for run_dir in sorted(pr_check_runs_root.iterdir()):
        if not run_dir.is_dir() or not is_evaluable_run(run_dir):
            continue
        try:
            pr_number, backend = parse_run_dir_name(run_dir.name)
        except PrCheckerError:
            continue

        gap_csv = run_dir / TARGET_LINES_UNCOVERED
        with gap_csv.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                continue
            for row in reader:
                file_path = (row.get("file") or "").strip()
                line = _gap_line_no(row)
                if not file_path or line is None:
                    continue
                yield UncoveredGapLine(
                    pr_number=pr_number,
                    backend=backend,
                    run_dir=run_dir,
                    file_path=file_path,
                    line=line,
                    text=(row.get("text") or "").strip(),
                )
