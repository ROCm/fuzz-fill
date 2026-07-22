"""Tests for coverage.lit_config lit filter helpers."""

from __future__ import annotations

import unittest

from coverage.lit_config import build_lit_filter_regex, resolved_lit_filter


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

    def test_escapes_regex_metacharacters_for_multiple_prefixes(self) -> None:
        self.assertEqual(
            build_lit_filter_regex(["CodeGen/AMDGPU", "(^|/)AMDGPU/"]),
            r"CodeGen/AMDGPU|\(\^\|/\)AMDGPU",
        )

    def test_empty_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_lit_filter_regex([])

    def test_blank_entries_ignored(self) -> None:
        self.assertEqual(
            build_lit_filter_regex(["", "  ", "CodeGen/AMDGPU"]),
            "CodeGen/AMDGPU",
        )


class TestResolvedLitFilter(unittest.TestCase):
    def test_default(self) -> None:
        self.assertEqual(resolved_lit_filter(None), "AMDGPU")

    def test_explicit_single(self) -> None:
        self.assertEqual(
            resolved_lit_filter(["CodeGen/SPIRV"]),
            "CodeGen/SPIRV",
        )

    def test_explicit_multiple(self) -> None:
        self.assertEqual(
            resolved_lit_filter(["CodeGen/AMDGPU", "Transforms/InstCombine/AMDGPU"]),
            "CodeGen/AMDGPU|Transforms/InstCombine/AMDGPU",
        )


if __name__ == "__main__":
    unittest.main()
