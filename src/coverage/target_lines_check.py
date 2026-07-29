"""Compare target-lines CSV against baseline uncovered line coverage."""

from __future__ import annotations

import csv
from pathlib import Path

from coverage.line_coverage_summary import load_uncovered_lines_csv
from fuzz_fill.log import get_logger

logger = get_logger("coverage.target_lines")


def _build_symcov_suffix_index(
    summary_files: set[str],
) -> dict[tuple[str, ...], str]:
    """Index summary file paths by every trailing path-component suffix."""
    index: dict[tuple[str, ...], str] = {}
    for abs_f in sorted(summary_files):
        parts = Path(abs_f).as_posix().split("/")
        for n in range(1, len(parts) + 1):
            index.setdefault(tuple(parts[-n:]), abs_f)
    return index


def _match_symcov_file(
    rel_path: str, symcov_suffix_index: dict[tuple[str, ...], str]
) -> str | None:
    """Map git-style relative path to an absolute path string present in the summary."""
    rel_parts = tuple(Path(rel_path).as_posix().split("/"))
    return symcov_suffix_index.get(rel_parts)


def run_target_lines_check(
    *,
    line_coverage_uncovered_csv: Path,
    llvm_repo: Path,
    target_lines_csv: Path,
    report_path: Path,
) -> None:
    """
    Emit target source lines that appear in ``line_coverage_uncovered.csv``.

    A line is listed only when its matched ``(file, line)`` is present in the
    baseline uncovered CSV produced by ``coverage baseline``.

    The report uses the same uncovered-lines contract as ``coverage baseline``:
    columns ``file`` and ``line`` with absolute paths matching the baseline
    summary / LLC address map. An optional ``text`` column preserves the source
    line for review.
    """
    uncovered_lines = load_uncovered_lines_csv(line_coverage_uncovered_csv)
    summary_files: set[str] = {file for file, _ in uncovered_lines}
    symcov_suffix_index = _build_symcov_suffix_index(summary_files)

    llvm_repo = llvm_repo.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    uncovered_rows: list[dict[str, str]] = []
    stats = {
        "reported": 0,
        "not_in_uncovered_list": 0,
        "unknown_file": 0,
    }

    with target_lines_csv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise SystemExit(f"Empty or invalid CSV: {target_lines_csv}")
        need = {"path", "line_no", "text"}
        if not need.issubset(set(reader.fieldnames)):
            raise SystemExit(
                f"{target_lines_csv}: expected columns {sorted(need)}, got {reader.fieldnames!r}"
            )
        for row in reader:
            rel = row["path"].strip()
            try:
                line_no = int(row["line_no"])
            except ValueError as e:
                raise SystemExit(
                    f"Invalid line_no {row['line_no']!r} for path {rel!r}"
                ) from e
            text = row.get("text", "")

            sym_file = _match_symcov_file(rel, symcov_suffix_index)
            if sym_file is None:
                cand = (llvm_repo / rel).resolve()
                if str(cand) in summary_files:
                    sym_file = str(cand)

            if sym_file is None:
                stats["unknown_file"] += 1
                continue

            if (sym_file, line_no) in uncovered_lines:
                stats["reported"] += 1
                uncovered_rows.append(
                    {
                        "file": sym_file,
                        "line": str(line_no),
                        "text": text,
                    }
                )
            else:
                stats["not_in_uncovered_list"] += 1

    fieldnames = ["file", "line", "text"]
    with report_path.open("w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(uncovered_rows)

    total_in = sum(stats.values())
    logger.info(
        "wrote %s (%d uncovered rows of %d target lines). "
        "reported=%d not_in_uncovered_list=%d unknown_file=%d",
        report_path,
        len(uncovered_rows),
        total_in,
        stats["reported"],
        stats["not_in_uncovered_list"],
        stats["unknown_file"],
    )
