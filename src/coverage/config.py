"""Resolved settings for a coverage run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CoverageConfig:
    """Paths and options after CLI / caller resolution."""

    build_bin_dir: Path
    coverage_dir: Path
    cwd: Path
    binaries: tuple[str, ...]
    command: str | None
    skip_run: bool
    union_batch: int
    outline_json: Path | None
    merged_suffix_id: str
    new_tests_dir: Path | None
    new_tests_limit: int | None
    new_tests_baseline_csv: Path | None
    new_tests_line_address_map: Path | None
    new_tests_source_path_prefix: str | None
    new_tests_sense_check: bool
    # If set, new-tests does not run llc; reads raw llc.*.sancov from this directory instead.
    new_tests_existing_sancov_dir: Path | None
    # Optional previous llc_test_report.csv mapping test -> raw_sancov_files JSON (and exit codes).
    new_tests_reuse_report: Path | None
