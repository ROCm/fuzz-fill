"""Gap-fill output layout for batch reduction."""

from __future__ import annotations

import shutil
from pathlib import Path


def gap_fill_coverage_csv(gap_fill_dir: Path) -> Path:
    return gap_fill_dir / "incremental" / "new_coverage.csv"


def gap_fill_candidate_tests_dir(gap_fill_dir: Path) -> Path:
    return gap_fill_dir / "candidate_tests"


def gap_fill_reduced_dir(gap_fill_dir: Path) -> Path:
    return gap_fill_dir / "reduced"


def resolve_batch_inputs(
    *,
    gap_fill_dir: Path,
    output: Path | None,
) -> tuple[Path, Path, Path]:
    """Resolve CSV, candidate_tests, and output paths from a gap-fill directory."""
    gap_fill_dir = gap_fill_dir.expanduser().resolve()
    if not gap_fill_dir.is_dir():
        raise ValueError(f"--gap-fill-dir is not a directory: {gap_fill_dir}")

    csv_path = gap_fill_coverage_csv(gap_fill_dir)
    candidate_tests = gap_fill_candidate_tests_dir(gap_fill_dir)
    out_parent = output.expanduser().resolve() if output is not None else gap_fill_reduced_dir(
        gap_fill_dir
    )

    if not csv_path.is_file():
        raise ValueError(
            f"gap-fill CSV not found: {csv_path} (run gap-filling first)"
        )
    if not candidate_tests.is_dir():
        raise ValueError(
            f"candidate_tests directory not found: {candidate_tests}"
        )

    return csv_path, candidate_tests, out_parent


def clear_output_dir(out_parent: Path) -> None:
    """Remove existing contents under *out_parent* (matches scripts/reduction.sh)."""
    out_parent.mkdir(parents=True, exist_ok=True)
    for child in out_parent.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
