"""Unit tests for lit failure log parsing."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from coverage.lit_failures import parse_lit_failures_from_log, write_lit_failures_json


class LitFailuresTest(unittest.TestCase):
    def test_parses_failure_like_lit_results_once(self) -> None:
        report = parse_lit_failures_from_log(
            "\n".join(
                [
                    "PASS: LLVM :: CodeGen/AMDGPU/ok.ll (1 of 4)",
                    "FAIL: LLVM :: CodeGen/AMDGPU/fail.ll (2 of 4)",
                    "TIMEOUT: Clang :: Driver/slow.c (3 of 4)",
                    "FAIL: LLVM :: CodeGen/AMDGPU/fail.ll (2 of 4)",
                    "UNRESOLVED: LLVM :: CodeGen/AMDGPU/missing.ll (4 of 4)",
                    "random log line",
                ]
            )
        )

        self.assertEqual(
            report,
            {
                "tests": [
                    {"name": "LLVM :: CodeGen/AMDGPU/fail.ll", "code": "FAIL"},
                    {"name": "Clang :: Driver/slow.c", "code": "TIMEOUT"},
                    {
                        "name": "LLVM :: CodeGen/AMDGPU/missing.ll",
                        "code": "UNRESOLVED",
                    },
                ]
            },
        )

    def test_writes_json_and_returns_failure_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lit_failures.json"
            count = write_lit_failures_json(
                path,
                "XPASS: LLVM :: unexpected.ll (1 of 1)\n",
            )

            self.assertEqual(count, 1)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"tests": [{"name": "LLVM :: unexpected.ll", "code": "XPASS"}]},
            )


if __name__ == "__main__":
    unittest.main()
