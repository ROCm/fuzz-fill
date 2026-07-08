"""Compare target-lines CSV against test-suite line coverage summary."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from coverage.constants import DEFAULT_LINE_COVERAGE_SUMMARY_FILE
from coverage.line_rules import LineCoverageIndex


def _match_symcov_file(rel_path: str, summary_files: set[str]) -> str | None:
    """Map git-style relative path to an absolute path string present in the summary."""
    rel_parts = Path(rel_path).as_posix().split("/")
    n = len(rel_parts)
    for abs_f in summary_files:
        parts = Path(abs_f).as_posix().split("/")
        if len(parts) >= n and parts[-n:] == rel_parts:
            return abs_f
    return None


def _load_line_coverage_summary(test_suite_output_dir: Path) -> pd.DataFrame:
    summary_path = test_suite_output_dir / DEFAULT_LINE_COVERAGE_SUMMARY_FILE
    if not summary_path.is_file():
        raise SystemExit(
            f"Missing {summary_path}. Run ``coverage test-suite`` first (or pass the same "
            f"--output-dir you used for that run as --test-suite-output-dir)."
        )
    summary = pd.read_csv(summary_path)
    summary["line"] = summary["line"].astype(int)
    return summary


def run_target_lines_check(
    *,
    baseline_output_dir: Path,
    llvm_repo: Path,
    target_lines_csv: Path,
    report_path: Path,
) -> None:
    """
    Emit target source lines from *target_lines_csv* that the **existing** LIT test suite
    leaves **completely** cold on every SanitizerCoverage site for that source line
    (joint llc/opt view).

    Reads ``line_coverage_summary.csv`` produced by ``coverage test-suite`` (scoped by
    that run's lit filter). A line is listed only when it appears in the summary and
    ``coverage`` is ``none`` — every merged instrumentation point on that ``(file, line)``
    was absent from the suite's covered points.

    Each row includes **``point_addresses``** from the summary CSV (semicolon-separated).

    Lines with ``coverage`` ``full`` or ``partial`` are omitted from the report;
    ``partial`` is counted in the printed summary.

    Rows with unknown path, or no instrumentation for that line in the summary, are
    counted in the printed summary only (they are omitted from the CSV).
    """
    summary = _load_line_coverage_summary(baseline_output_dir)
    index = LineCoverageIndex.from_summary_df(summary)
    summary_files: set[str] = {file for file, _ in index.instrumented}

    llvm_repo = llvm_repo.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    uncovered_rows: list[dict[str, str]] = []
    stats = {
        "covered": 0,
        "all_uncovered": 0,
        "partial": 0,
        "not_instrumented": 0,
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
            else:
                coverage = index.classify(sym_file, line_no)
                if coverage == "not_instrumented":
                    stats["not_instrumented"] += 1
                elif coverage == "full":
                    stats["covered"] += 1
                elif coverage == "none":
                    stats["all_uncovered"] += 1
                    addrs = index.point_addresses.get((sym_file, line_no), [])
                    uncovered_rows.append(
                        {
                            "path": rel,
                            "line_no": str(line_no),
                            "text": text,
                            "symcov_file": sym_file,
                            "point_addresses": ";".join(addrs),
                        }
                    )
                else:
                    stats["partial"] += 1

    fieldnames = ["path", "line_no", "text", "symcov_file", "point_addresses"]
    with report_path.open("w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(uncovered_rows)

    total_in = sum(stats.values())
    print(
        f"Wrote {report_path} ({len(uncovered_rows)} all-points-uncovered rows of {total_in} target lines). "
        f"covered={stats['covered']} all_uncovered={stats['all_uncovered']} partial={stats['partial']} "
        f"not_instrumented={stats['not_instrumented']} unknown_file={stats['unknown_file']}",
        flush=True,
    )
