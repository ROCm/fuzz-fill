"""Parse sancov -print-coverage-stats output."""

from __future__ import annotations

import re

_STATS_RE = re.compile(
    r"^(all-edges|cov-edges|all-functions|cov-functions):\s*(\d+)\s*$", re.MULTILINE
)


def parse_stats_text(stats_stdout: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for m in _STATS_RE.finditer(stats_stdout):
        key = m.group(1).replace("-", "_")
        out[key] = int(m.group(2))
    return out
