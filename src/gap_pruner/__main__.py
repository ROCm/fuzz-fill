from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from gap_pruner.noncoverable_spans import find_noncoverable_lines

FIELDNAMES = ["file", "line", "text"]


def read_target_lines(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_target_lines(csv_path: Path, rows: list[dict[str, str]]) -> None:
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def prune_noncoverable_lines(
    rows: list[dict[str, str]], llvm_src_dir: Path | None
) -> list[dict[str, str]]:
    """Drop rows whose line is blank, a standalone '{'/'}', or belongs to an
    assert/report_fatal_error/... call or multi-line control-flow header.

    What a line actually is comes from ``source_file`` on disk, never from a
    CSV's own ``text`` column (which may be stale, absent, or simply not
    trusted). A relative ``file`` is resolved against ``llvm_src_dir``; an
    absolute ``file`` is used as-is and ``llvm_src_dir`` is not needed for it.

    Coverage gaps can land in files outside the llvm-project checkout entirely
    (e.g. libstdc++ headers pulled in by template instantiation), which may not
    exist on disk in every environment. A row whose file can't be read is kept
    rather than crashing: with no ability to inspect it, there's no basis to
    call it non-coverable.
    """
    pruned_lines_by_file: dict[str, set[int]] = {}
    kept: list[dict[str, str]] = []
    for row in rows:
        file = row["file"]
        if file not in pruned_lines_by_file:
            path = Path(file)
            if not path.is_absolute():
                path = llvm_src_dir / path
            try:
                pruned_lines_by_file[file] = find_noncoverable_lines(path)
            except OSError as e:
                print(f"warning: gap-pruner: skipping unreadable file {file}: {e}", file=sys.stderr)
                pruned_lines_by_file[file] = set()
        if int(row["line"]) not in pruned_lines_by_file[file]:
            kept.append(row)
    return kept


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gap-pruner",
        description="Prune uninteresting target lines from a coverage-gap CSV.",
    )
    parser.add_argument(
        "input_csv", type=Path, help="CSV with file,line columns to prune (an optional text column is ignored)"
    )
    parser.add_argument(
        "--llvm-src-dir",
        type=Path,
        default=None,
        help="LLVM project source checkout, required only if input_csv has relative file paths",
    )
    parser.add_argument("--output", required=True, type=Path, help="Where to write the pruned CSV")
    args = parser.parse_args(argv)

    if args.llvm_src_dir is not None and not args.llvm_src_dir.is_dir():
        parser.error(f"llvm_src_dir is not a directory: {args.llvm_src_dir}")
    if not args.input_csv.is_file():
        parser.error(f"input_csv is not a file: {args.input_csv}")

    rows = read_target_lines(args.input_csv)
    if args.llvm_src_dir is None and any(not Path(r["file"]).is_absolute() for r in rows):
        parser.error("input_csv has relative file paths, --llvm-src-dir is required")

    rows = prune_noncoverable_lines(rows, args.llvm_src_dir)
    write_target_lines(args.output, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
