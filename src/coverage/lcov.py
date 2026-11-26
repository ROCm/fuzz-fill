"""Parse llvm-cov LCOV export into covered/uncovered line rows."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from coverage.paths import canonicalize_source_path


def parse_lcov_to_summary(
    lcov_text: str,
    *,
    llvm_src: Path,
) -> pd.DataFrame:
    """Parse LCOV ``DA:`` records into ``file,line,coverage`` rows.

    ``execution_count == 0`` → uncovered; ``> 0`` → covered. Lines with no
    ``DA`` record are omitted. Paths outside ``llvm_src`` are dropped.
    """
    rows: list[dict[str, object]] = []
    current_raw: str | None = None
    current_rel: str | None = None

    for raw_line in lcov_text.splitlines():
        line = raw_line.strip()
        if line.startswith("SF:"):
            current_raw = line[3:]
            current_rel = canonicalize_source_path(current_raw, llvm_src)
            continue
        if line.startswith("DA:") and current_rel is not None:
            # DA:<line>,<execution_count>[,checksum]
            body = line[3:]
            parts = body.split(",")
            if len(parts) < 2:
                continue
            try:
                lineno = int(parts[0])
                count = int(parts[1])
            except ValueError:
                continue
            rows.append(
                {
                    "file": current_rel,
                    "line": lineno,
                    "coverage": "covered" if count > 0 else "uncovered",
                }
            )
            continue
        if line == "end_of_record":
            current_raw = None
            current_rel = None

    if not rows:
        return pd.DataFrame(columns=["file", "line", "coverage"])
    frame = pd.DataFrame(rows)
    # Same (file, line) can appear once per object; any hit → covered.
    frame = (
        frame.groupby(["file", "line"], as_index=False)
        .agg(coverage=("coverage", lambda s: "covered" if (s == "covered").any() else "uncovered"))
    )
    return frame
