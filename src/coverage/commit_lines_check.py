"""Compare added-lines CSV against test-suite symcov (llc + opt)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from coverage.constants import DEFAULT_PATH_FILTER
from coverage.sancov import Sancov


def _processed_symcov_paths(test_suite_output_dir: Path) -> tuple[Path, Path]:
    base = test_suite_output_dir / "processed_sancov"
    return base / "llc.0.symcov", base / "opt.0.symcov"


def _match_symcov_file(rel_path: str, symcov_files: set[str]) -> str | None:
    """Map git-style relative path to an absolute path string present in symcov."""
    rel_parts = Path(rel_path).as_posix().split("/")
    n = len(rel_parts)
    for abs_f in symcov_files:
        parts = Path(abs_f).as_posix().split("/")
        if len(parts) >= n and parts[-n:] == rel_parts:
            return abs_f
    return None


def _instrumented_line_keys(
    this_df: pd.DataFrame, other_df: pd.DataFrame
) -> set[tuple[str, int]]:
    a = set(zip(this_df["file"], this_df["line"].astype(int)))
    b = set(zip(other_df["file"], other_df["line"].astype(int)))
    return a | b


def run_commit_lines_check(
    *,
    test_suite_output_dir: Path,
    llvm_repo: Path,
    added_lines_csv: Path,
    path_filter: str = DEFAULT_PATH_FILTER,
    report_path: Path,
) -> None:
    """
    Emit added source lines from *added_lines_csv* that the **existing** LIT test suite
    leaves **completely** cold on every SanitizerCoverage site for that source line
    (joint llc/opt view).

    A line is listed only when it appears in symcov ``point-symbol-info`` (after
    *path_filter*) and **every** merged instrumentation point on that ``(file, line)``
    is **absent** from ``covered-points`` (no llc/opt hit on any of those addresses).

    Each row includes **``point_addresses``**: distinct SanitizerCoverage point ids for
    that ``(file, line)`` (``point_this`` / ``point_other`` from the llc/opt merge),
    **semicolon-separated** in one cell (same list style as ``covered-points`` elsewhere).

    Lines that are **partially** covered (some points hit, some not) are omitted from
    the CSV but counted in the printed summary as ``partial``.

    Rows with unknown path, or no instrumentation for that line under the filter, are
    counted in the printed summary only (they are omitted from the CSV).
    """
    llc_path, opt_path = _processed_symcov_paths(test_suite_output_dir)
    if not llc_path.is_file():
        raise SystemExit(
            f"Missing {llc_path}. Run ``coverage test-suite`` first (or pass the same "
            f"--output-dir you used for that run as --test-suite-output-dir)."
        )
    if not opt_path.is_file():
        raise SystemExit(
            f"Missing {opt_path}. Run ``coverage test-suite`` first so llc and opt symcov exist."
        )

    with llc_path.open(encoding="utf-8") as f:
        llc_symcov = json.load(f)
    with opt_path.open(encoding="utf-8") as f:
        opt_symcov = json.load(f)

    this_df = Sancov.get_coverage_df(llc_symcov, path_filter)
    other_df = Sancov.get_coverage_df(opt_symcov, path_filter)
    merged_cov = Sancov.merged_llc_opt_coverage_df(this_df, other_df)
    baseline_lines = Sancov.jointly_fully_covered_line_keys_from_merged(merged_cov)
    all_uncovered_lines = Sancov.jointly_all_points_uncovered_line_keys_from_merged(
        merged_cov
    )
    addr_map = Sancov.all_uncovered_line_point_addresses(
        merged_cov, all_uncovered_lines
    )
    instrumented = _instrumented_line_keys(this_df, other_df)
    symcov_files: set[str] = set(this_df["file"].unique()) | set(other_df["file"].unique())

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

    with added_lines_csv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise SystemExit(f"Empty or invalid CSV: {added_lines_csv}")
        need = {"path", "line_no", "text"}
        if not need.issubset(set(reader.fieldnames)):
            raise SystemExit(
                f"{added_lines_csv}: expected columns {sorted(need)}, got {reader.fieldnames!r}"
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

            sym_file = _match_symcov_file(rel, symcov_files)
            if sym_file is None:
                cand = (llvm_repo / rel).resolve()
                if str(cand) in symcov_files:
                    sym_file = str(cand)

            if sym_file is None:
                stats["unknown_file"] += 1
            else:
                key = (sym_file, line_no)
                if key not in instrumented:
                    stats["not_instrumented"] += 1
                elif key in baseline_lines:
                    stats["covered"] += 1
                elif key in all_uncovered_lines:
                    stats["all_uncovered"] += 1
                    addrs = addr_map.get(key, [])
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
        f"Wrote {report_path} ({len(uncovered_rows)} all-points-uncovered rows of {total_in} added lines). "
        f"covered={stats['covered']} all_uncovered={stats['all_uncovered']} partial={stats['partial']} "
        f"not_instrumented={stats['not_instrumented']} unknown_file={stats['unknown_file']}",
        flush=True,
    )
