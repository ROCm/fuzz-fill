"""Compare analysed novel lines with original vs replacement snippets (WIP).

The input CSV is ``coverage analyse`` stacked output
(``per_test_csv``, ``file``, ``function``, ``line``) plus ``line_original`` and
``line_replacement``.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from coverage.stage_log import stage_line


def check_uncovered_main(args: Namespace) -> int:
    csv_path = Path(args.csv).resolve()
    build_dir = Path(args.llvm_build).resolve()
    stage_line("check-uncovered", f"csv: {csv_path}")
    stage_line("check-uncovered", f"llvm-build: {build_dir}")
    return 0
