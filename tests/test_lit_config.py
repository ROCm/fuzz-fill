"""Tests for live coverage.lit_config helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coverage.lit_config import (
    build_lit_filter_regex,
    ensure_lit_sancov_env_forwarding,
)


class TestBuildLitFilterRegex(unittest.TestCase):
    def test_single_prefix(self) -> None:
        self.assertEqual(build_lit_filter_regex(["CodeGen/AMDGPU"]), "CodeGen/AMDGPU")

    def test_strips_slashes(self) -> None:
        self.assertEqual(build_lit_filter_regex(["/CodeGen/AMDGPU/"]), "CodeGen/AMDGPU")

    def test_multiple_prefixes(self) -> None:
        self.assertEqual(
            build_lit_filter_regex(["CodeGen/AMDGPU", "MC/AMDGPU"]),
            "CodeGen/AMDGPU|MC/AMDGPU",
        )

    def test_multiple_regex_prefixes(self) -> None:
        self.assertEqual(
            build_lit_filter_regex(["CodeGen/AMDGPU", "Analysis/[^/]+/AMDGPU"]),
            "CodeGen/AMDGPU|Analysis/[^/]+/AMDGPU",
        )

    def test_multiple_regex_passthrough(self) -> None:
        self.assertEqual(
            build_lit_filter_regex(["CodeGen/AMDGPU", "(^|/)AMDGPU/"]),
            "CodeGen/AMDGPU|(^|/)AMDGPU",
        )

    def test_empty_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_lit_filter_regex([])

    def test_blank_entries_ignored(self) -> None:
        self.assertEqual(
            build_lit_filter_regex(["", "  ", "CodeGen/AMDGPU"]),
            "CodeGen/AMDGPU",
        )

    def test_amdgpu_workflow_filters(self) -> None:
        # Keep in sync with scripts/lit-filters-amdgpu.sh
        filters = [r"(?:^|/)AMDGPU(?:/|$)"]
        self.assertEqual(
            build_lit_filter_regex(filters),
            r"(?:^|/)AMDGPU(?:/|$)",
        )


class TestLitSiteConfigPatch(unittest.TestCase):
    def test_appends_env_forwarding_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp) / "build"
            llvm_lit = build_root / "bin" / "llvm-lit"
            site_cfg = build_root / "test" / "lit.site.cfg.py"
            llvm_lit.parent.mkdir(parents=True)
            site_cfg.parent.mkdir(parents=True)
            site_cfg.write_text("config.name = 'LLVM'\n", encoding="utf-8")

            patched = ensure_lit_sancov_env_forwarding(llvm_lit)
            ensure_lit_sancov_env_forwarding(llvm_lit)

            text = patched.read_text(encoding="utf-8")
            self.assertIn("fuzz-fill: SanitizerCoverage env forwarding", text)
            self.assertEqual(text.count("fuzz-fill: SanitizerCoverage env forwarding"), 1)


if __name__ == "__main__":
    unittest.main()
