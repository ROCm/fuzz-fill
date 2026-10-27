"""Intersect a target-lines CSV with a baseline ``line_coverage_summary.csv``."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from coverage.constants import (
    DEFAULT_TARGET_LINES_COVERAGE_SUMMARY,
    DEFAULT_TARGET_LINES_REPORT,
)
from coverage.line_coverage_summary import load_line_coverage_summary
from coverage.revision_check import check_revision_consistency
from fuzz_fill.log import get_logger

logger = get_logger("coverage.target_lines")

MISMATCH_SAMPLE_SIZE = 10


def _match_symcov_file(rel_path: str, summary_files: set[str]) -> str | None:
    """Map git-style relative path to an absolute path string present in the summary."""
    rel_parts = Path(rel_path).as_posix().split("/")
    n = len(rel_parts)
    for abs_f in summary_files:
        parts = Path(abs_f).as_posix().split("/")
        if len(parts) >= n and parts[-n:] == rel_parts:
            return abs_f
    return None


@lru_cache(maxsize=None)
def _read_source_lines(path: str) -> tuple[str, ...]:
    """Return the on-disk lines of ``path``."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return tuple(f.readlines())


def _source_text_mismatches(sym_file: str, line_no: int, text: str) -> bool:
    """True if the on-disk line ``line_no`` in ``sym_file`` differs from ``text``."""
    lines = _read_source_lines(sym_file)
    if not 1 <= line_no <= len(lines):
        return True
    return lines[line_no - 1].strip() != text.strip()


def run_target_lines_check(
    *,
    summary_csv: Path,
    llvm_repo: Path,
    target_lines_csv: Path,
    output_dir: Path,
    commit_check: bool = True,
    source_text_check: bool = True,
) -> None:
    """
    Emit PR/target lines that appear in ``summary_csv``.

    Writes ``target_lines_coverage_summary.csv`` (``file``, ``line``, ``coverage``)
    for every matched target line, and ``target_lines_uncovered.csv``
    (``file``, ``line``, ``text``) for those with ``coverage == uncovered``.

    ``commit_check`` and ``source_text_check`` are enabled by default and abort
    when revisions or on-disk source text disagree with the target-lines CSV.
    """
    if commit_check:
        check_revision_consistency(
            llvm_repo=llvm_repo,
            baseline_dir=summary_csv.parent,
            target_lines_dir=target_lines_csv.parent,
        )

    coverage_by_line, _ = load_line_coverage_summary(summary_csv)
    summary_files: set[str] = {file for file, _ in coverage_by_line}

    llvm_repo = llvm_repo.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / DEFAULT_TARGET_LINES_COVERAGE_SUMMARY
    uncovered_path = output_dir / DEFAULT_TARGET_LINES_REPORT

    summary_rows: list[dict[str, str]] = []
    uncovered_rows: list[dict[str, str]] = []
    mismatch_sample: list[str] = []
    stats = {
        "reported": 0,
        "not_in_summary": 0,
        "source_mismatch": 0,
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

            sym_file = _match_symcov_file(rel, summary_files)
            if sym_file is None:
                cand = (llvm_repo / rel).resolve()
                if str(cand) in summary_files:
                    sym_file = str(cand)

            if sym_file is None:
                stats["unknown_file"] += 1
                continue

            status = coverage_by_line.get((sym_file, line_no))
            if status is None:
                stats["not_in_summary"] += 1
                continue

            if _source_text_mismatches(sym_file, line_no, text):
                stats["source_mismatch"] += 1
                if len(mismatch_sample) < MISMATCH_SAMPLE_SIZE:
                    mismatch_sample.append(f"{sym_file}:{line_no}")
                if source_text_check:
                    continue

            stats["reported"] += 1
            summary_rows.append(
                {
                    "file": sym_file,
                    "line": str(line_no),
                    "coverage": status,
                }
            )
            if status == "uncovered":
                uncovered_rows.append(
                    {
                        "file": sym_file,
                        "line": str(line_no),
                        "text": text,
                    }
                )

    mismatched = stats["source_mismatch"]
    if source_text_check and mismatched:
        sample = "\n".join(f"  {loc}" for loc in mismatch_sample)
        more = f"\n  ... and {mismatched - len(mismatch_sample)} more" if mismatched > len(mismatch_sample) else ""
        raise SystemExit(
            f"{mismatched} target line(s) do not match the source on disk:\n"
            f"{sample}{more}\n"
            "The baseline source tree differs from the tree the target lines "
            "were taken from (different revision or uncommitted changes), so "
            "line numbers cannot be compared. Re-run `coverage baseline` "
            "against that tree, or pass --no-source-text-check to skip this check."
        )

    with summary_path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=["file", "line", "coverage"])
        writer.writeheader()
        writer.writerows(summary_rows)

    with uncovered_path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=["file", "line", "text"])
        writer.writeheader()
        writer.writerows(uncovered_rows)

    total_in = stats["reported"] + stats["not_in_summary"] + stats["unknown_file"]
    logger.info(
        "wrote %s (%d rows) and %s (%d uncovered) of %d target lines. "
        "reported=%d not_in_summary=%d unknown_file=%d source_mismatch=%d",
        summary_path,
        len(summary_rows),
        uncovered_path,
        len(uncovered_rows),
        total_in,
        stats["reported"],
        stats["not_in_summary"],
        stats["unknown_file"],
        stats["source_mismatch"],
    )
    if stats["source_mismatch"]:
        logger.warning(
            "%d reported target line(s) do not match the source on disk "
            "(--no-source-text-check): the baseline may have been built from a "
            "different tree, so these hits can be coincidental.",
            stats["source_mismatch"],
        )
