"""Build ``lit_failures.json`` from a captured ``check-all`` / lit log."""

from __future__ import annotations

import json
import re
from pathlib import Path

# Same failure codes as scripts/count_lit_failures.py.
FAILURE_CODES = frozenset({"FAIL", "TIMEOUT", "UNRESOLVED", "XPASS"})

# Lit progress lines look like:
#   FAIL: LLVM :: CodeGen/AMDGPU/foo.ll (12 of 100)
#   TIMEOUT: Clang :: Driver/bar.c (1 of 5)
_LIT_RESULT_RE = re.compile(
    r"^(?P<code>FAIL|TIMEOUT|UNRESOLVED|XPASS):\s+(?P<name>.+?)\s+\(\d+\s+of\s+\d+\)\s*$"
)


def parse_lit_failures_from_log(log_text: str) -> dict:
    """Return a lit-style report dict with only failure-like tests."""
    tests: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in log_text.splitlines():
        match = _LIT_RESULT_RE.match(line.strip())
        if not match:
            continue
        name = match.group("name").strip()
        code = match.group("code")
        key = f"{code}:{name}"
        if key in seen:
            continue
        seen.add(key)
        tests.append({"name": name, "code": code})
    return {"tests": tests}


def write_lit_failures_json(path: Path, log_text: str) -> int:
    """Write ``lit_failures.json`` from *log_text*; return failure count."""
    report = parse_lit_failures_from_log(log_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return sum(1 for t in report["tests"] if t.get("code") in FAILURE_CODES)
