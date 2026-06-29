"""Compare target-lines CSV against test-suite symcov (llc + opt)."""

from __future__ import annotations

import csv
from pathlib import Path

from coverage.constants import DEFAULT_TARGET_LINES_REPORT
from coverage.filepaths import Filepaths
from coverage.run_config import load_run_config
from coverage.sancov import Sancov


def _match_symcov_file(rel_path: str, symcov_files: set[str]) -> str | None:
    """Map git-style relative path to an absolute path string present in symcov."""
    rel_parts = Path(rel_path).as_posix().split("/")
    n = len(rel_parts)
    for abs_f in symcov_files:
        parts = Path(abs_f).as_posix().split("/")
        if len(parts) >= n and parts[-n:] == rel_parts:
            return abs_f
    return None


class TargetLinesAnalyzer:
    def __init__(
        self,
        filepaths: Filepaths,
        *,
        llvm_repo: Path,
        target_lines_csv: Path | None = None,
    ) -> None:
        self.filepaths = filepaths
        self.llvm_repo = llvm_repo.resolve()
        self.target_lines_csv = target_lines_csv or filepaths.target_lines_csv
        if self.target_lines_csv is None:
            raise ValueError("target_lines_csv is required")
        if filepaths.output_test_suite_dir is None:
            raise ValueError("output_test_suite_dir is required")
        report_name = filepaths.target_lines_report or DEFAULT_TARGET_LINES_REPORT
        self.report_path = filepaths.output_dir / report_name

    def run(self) -> None:
        """
        Emit target CSV rows that the **existing** LIT test suite leaves **completely**
        cold on every SanitizerCoverage site for that source line (joint llc/opt view).

        Lines that are **partially** covered are omitted from the CSV but counted in the
        printed summary. Unknown paths and non-instrumented lines are summary-only.
        """
        run_config = load_run_config(self.filepaths.output_test_suite_dir.resolve())
        view = Sancov.load_joint_coverage_from_suite_dir(
            self.filepaths.output_test_suite_dir.resolve(),
            run_config["path_filter"],
        )

        self.report_path.parent.mkdir(parents=True, exist_ok=True)

        uncovered_rows: list[dict[str, str]] = []
        stats = {
            "covered": 0,
            "all_uncovered": 0,
            "partial": 0,
            "not_instrumented": 0,
            "unknown_file": 0,
        }

        with self.target_lines_csv.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise SystemExit(f"Empty or invalid CSV: {self.target_lines_csv}")
            need = {"path", "line_no", "text"}
            if not need.issubset(set(reader.fieldnames)):
                raise SystemExit(
                    f"{self.target_lines_csv}: expected columns {sorted(need)}, "
                    f"got {reader.fieldnames!r}"
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

                sym_file = _match_symcov_file(rel, view.symcov_files)
                if sym_file is None:
                    cand = (self.llvm_repo / rel).resolve()
                    if str(cand) in view.symcov_files:
                        sym_file = str(cand)

                if sym_file is None:
                    stats["unknown_file"] += 1
                else:
                    key = (sym_file, line_no)
                    status = view.line_status.get(key)
                    if status is None:
                        stats["not_instrumented"] += 1
                    elif status == "full":
                        stats["covered"] += 1
                    elif status == "none":
                        stats["all_uncovered"] += 1
                        addrs = view.point_addresses_by_line.get(key, [])
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
        with self.report_path.open("w", encoding="utf-8", newline="") as out:
            w = csv.DictWriter(out, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(uncovered_rows)

        total_in = sum(stats.values())
        print(
            f"Wrote {self.report_path} ({len(uncovered_rows)} all-points-uncovered rows "
            f"of {total_in} target lines). "
            f"covered={stats['covered']} all_uncovered={stats['all_uncovered']} "
            f"partial={stats['partial']} not_instrumented={stats['not_instrumented']} "
            f"unknown_file={stats['unknown_file']}",
            flush=True,
        )
