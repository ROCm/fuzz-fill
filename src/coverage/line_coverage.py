"""Export and load per-line baseline coverage status for target-lines."""

from __future__ import annotations

import csv
import dataclasses
from pathlib import Path
from typing import Literal

from coverage.sancov import JointCoverageView

LineStatus = Literal["full", "partial", "none"]
_VALID_STATUSES = frozenset({"full", "partial", "none"})
_REQUIRED_COLUMNS = frozenset({"file", "line", "status", "point_addresses"})


@dataclasses.dataclass(frozen=True)
class BaselineLineCoverage:
    """Line-level baseline coverage index loaded from ``line_coverage_status.csv``."""

    source_files: frozenset[str]
    line_status: dict[tuple[str, int], LineStatus]
    point_addresses_by_line: dict[tuple[str, int], list[str]]


def export_line_coverage_status(view: JointCoverageView, path: Path) -> None:
    """Write one row per instrumented ``(file, line)`` with status and point ids."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str | int]] = []
    for (file_path, line_no), status in sorted(
        view.line_status.items(), key=lambda item: (item[0][0], item[0][1])
    ):
        addrs = view.point_addresses_by_line.get((file_path, line_no), [])
        rows.append(
            {
                "file": file_path,
                "line": line_no,
                "status": status,
                "point_addresses": ";".join(addrs) if status == "none" else "",
            }
        )
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["file", "line", "status", "point_addresses"]
        )
        writer.writeheader()
        writer.writerows(rows)


def load_line_coverage_status(path: Path) -> BaselineLineCoverage:
    """Load baseline line coverage from ``line_coverage_status.csv``."""
    if not path.is_file():
        raise SystemExit(
            f"Missing {path}. Run ``coverage test-suite`` first to generate "
            f"``line_coverage_status.csv``."
        )

    line_status: dict[tuple[str, int], LineStatus] = {}
    point_addresses_by_line: dict[tuple[str, int], list[str]] = {}
    source_files: set[str] = set()

    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise SystemExit(f"Empty or invalid CSV: {path}")
        if not _REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
            raise SystemExit(
                f"{path}: expected columns {sorted(_REQUIRED_COLUMNS)}, "
                f"got {reader.fieldnames!r}"
            )
        for row in reader:
            file_path = row["file"].strip()
            try:
                line_no = int(row["line"])
            except ValueError as e:
                raise SystemExit(
                    f"{path}: invalid line {row['line']!r} for file {file_path!r}"
                ) from e
            status = row["status"].strip()
            if status not in _VALID_STATUSES:
                raise SystemExit(
                    f"{path}: invalid status {status!r} for {file_path}:{line_no}"
                )
            key = (file_path, line_no)
            line_status[key] = status  # type: ignore[assignment]
            source_files.add(file_path)
            raw_addrs = row.get("point_addresses", "").strip()
            if raw_addrs:
                point_addresses_by_line[key] = [
                    part.strip() for part in raw_addrs.split(";") if part.strip()
                ]

    return BaselineLineCoverage(
        source_files=frozenset(source_files),
        line_status=line_status,
        point_addresses_by_line=point_addresses_by_line,
    )
