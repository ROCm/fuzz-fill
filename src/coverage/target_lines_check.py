"""Compare target-lines CSV against baseline uncovered line coverage."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from coverage.line_coverage_summary import load_uncovered_lines_csv
from coverage.revision_check import check_revision_consistency
from fuzz_fill.log import get_logger

logger = get_logger("coverage.target_lines")

# Number of mismatching locations listed in the source-text check error.
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
    line_coverage_uncovered_csv: Path,
    llvm_repo: Path,
    target_lines_csv: Path,
    report_path: Path,
    commit_check: bool = True,
    source_text_check: bool = True,
) -> None:
    """
    Emit target source lines that appear in ``line_coverage_uncovered.csv``.

    A line is listed only when its matched ``(file, line)`` is present in the
    baseline uncovered CSV produced by ``coverage baseline``.

    Two checks guard against comparing line numbers across different trees:
    ``commit_check`` compares the revisions recorded by the earlier stages, and
    ``source_text_check`` compares each target line against the source on disk,
    which also catches uncommitted changes. Both are enabled by default and
    abort the run.

    The report uses the same uncovered-lines contract as ``coverage baseline``:
    columns ``file`` and ``line`` with absolute paths matching the baseline
    summary / LLC address map. An optional ``text`` column preserves the source
    line for review.
    """
    if commit_check:
        check_revision_consistency(
            llvm_repo=llvm_repo,
            baseline_dir=line_coverage_uncovered_csv.parent,
            target_lines_dir=target_lines_csv.parent,
        )

    uncovered_lines = load_uncovered_lines_csv(line_coverage_uncovered_csv)
    summary_files: set[str] = {file for file, _ in uncovered_lines}

    llvm_repo = llvm_repo.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    uncovered_rows: list[dict[str, str]] = []
    # Locations of the first few mismatches, for the error message.
    mismatch_sample: list[str] = []
    stats = {
        "reported": 0,
        "not_in_uncovered_list": 0,
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

            if (sym_file, line_no) not in uncovered_lines:
                stats["not_in_uncovered_list"] += 1
                continue

            if _source_text_mismatches(sym_file, line_no, text):
                # Text differs: baseline and commit come from different trees,
                # so the line-number match is coincidental, not a real gap.
                stats["source_mismatch"] += 1
                if len(mismatch_sample) < MISMATCH_SAMPLE_SIZE:
                    mismatch_sample.append(f"{sym_file}:{line_no}")
                if source_text_check:
                    continue

            stats["reported"] += 1
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

    fieldnames = ["file", "line", "text"]
    with report_path.open("w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(uncovered_rows)

    total_in = stats["reported"] + stats["not_in_uncovered_list"] + stats["unknown_file"]
    logger.info(
        "wrote %s (%d uncovered rows of %d target lines). "
        "reported=%d not_in_uncovered_list=%d unknown_file=%d source_mismatch=%d",
        report_path,
        len(uncovered_rows),
        total_in,
        stats["reported"],
        stats["not_in_uncovered_list"],
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
