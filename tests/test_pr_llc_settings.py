"""Tests for PR-derived llc flag settings."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from coverage.pr_llc_settings import (
    cross_with_o_levels,
    default_exclude_completed_o_levels,
    derive_llc_flag_variants,
    exclude_variants,
    join_llvm_abs_path,
    merge_run_bases_with_gap_isel,
    normalize_llvm_rel_path,
    parse_run_llc_flags,
    path_heuristic_flag_sets,
)


class ParseRunLlcFlagsTests(unittest.TestCase):
    def test_simple_run_line(self) -> None:
        line = "; RUN: llc -mtriple=amdgcn-amd-amdhsa -mcpu=gfx900 < %s | FileCheck %s"
        self.assertEqual(
            parse_run_llc_flags(line),
            ["-mtriple=amdgcn-amd-amdhsa", "-mcpu=gfx900"],
        )

    def test_not_llc_with_global_isel(self) -> None:
        line = (
            "; RUN: not llc -global-isel -mtriple=amdgpu6.00-mesa-mesa3d "
            "-tailcallopt < %s 2>&1 | FileCheck %s"
        )
        self.assertEqual(
            parse_run_llc_flags(line),
            ["-global-isel=1", "-mtriple=amdgpu6.00-mesa-mesa3d", "-tailcallopt"],
        )

    def test_pipe_llc(self) -> None:
        line = "; RUN:   | llc -global-isel=0 -mtriple=amdgpu12.00-- -filetype=null"
        self.assertEqual(
            parse_run_llc_flags(line),
            ["-global-isel=0", "-mtriple=amdgpu12.00--"],
        )


class CrossWithOLevelsTests(unittest.TestCase):
    def test_expands_suffix_with_four_o_levels(self) -> None:
        out = cross_with_o_levels(["-global-isel=0"])
        self.assertEqual(
            out,
            ["-O0 -global-isel=0", "-O1 -global-isel=0", "-O2 -global-isel=0", "-O3 -global-isel=0"],
        )

    def test_preserves_explicit_o_level(self) -> None:
        out = cross_with_o_levels(["-O2 -global-isel=0"])
        self.assertEqual(out, ["-O2 -global-isel=0"])


class ExcludeVariantsTests(unittest.TestCase):
    def test_drops_plain_o_levels(self) -> None:
        variants = ["-O0", "-O1", "-O0 -global-isel=0", "-O2"]
        exclude = default_exclude_completed_o_levels()
        self.assertEqual(exclude_variants(variants, exclude), ["-O0 -global-isel=0"])


class PathHeuristicTests(unittest.TestCase):
    def test_si_and_gisel_from_paths(self) -> None:
        flags = path_heuristic_flag_sets(
            [
                "llvm/lib/Target/AMDGPU/SIISelLowering.cpp",
                "llvm/lib/Target/AMDGPU/AMDGPUCallLowering.cpp",
            ]
        )
        self.assertEqual(
            {f.llc_flags for f in flags},
            {"-global-isel=0", "-global-isel=1"},
        )


class MergeGapIselTests(unittest.TestCase):
    def test_adds_global_isel_zero_for_si_gap_targets(self) -> None:
        merged = merge_run_bases_with_gap_isel(
            ["-mtriple=amdgcn-amd-amdhsa -mcpu=gfx900"],
            ["llvm/lib/Target/AMDGPU/SIISelLowering.cpp"],
        )
        self.assertEqual(
            merged,
            ["-mtriple=amdgcn-amd-amdhsa -mcpu=gfx900 -global-isel=0"],
        )

    def test_ir_gap_targets_get_both_isel_paths(self) -> None:
        merged = merge_run_bases_with_gap_isel(
            [""],
            ["llvm/lib/Target/AMDGPU/AMDGPULibFunc.cpp"],
        )
        self.assertEqual(
            set(merged),
            {"-global-isel=0", "-global-isel=1"},
        )


class NormalizePathTests(unittest.TestCase):
    def test_join_avoids_double_llvm_prefix(self) -> None:
        self.assertEqual(
            join_llvm_abs_path(
                "/work/llvm-project/llvm",
                "llvm/lib/Target/AMDGPU/AMDGPUInstCombineIntrinsic.cpp",
            ),
            "/work/llvm-project/llvm/lib/Target/AMDGPU/AMDGPUInstCombineIntrinsic.cpp",
        )

    def test_normalize_collapses_duplicate_llvm(self) -> None:
        self.assertEqual(
            normalize_llvm_rel_path("llvm/llvm/lib/Foo.cpp"),
            "llvm/lib/Foo.cpp",
        )


class DeriveFromAddedLinesTests(unittest.TestCase):
    def test_derive_from_fixture_added_lines(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        pr_run = repo / "data/pr-check/runs/214936-amdgpu"
        if not (pr_run / "added-lines/added-lines.csv").is_file():
            self.skipTest("pr-check fixture not available")

        variants, _sources = derive_llc_flag_variants(
            pr_run_dir=pr_run,
            gap_target_paths=["llvm/lib/Target/AMDGPU/SIISelLowering.cpp"],
            exclude_flags=default_exclude_completed_o_levels(),
        )
        self.assertTrue(variants)
        self.assertTrue(all(v not in default_exclude_completed_o_levels() for v in variants))
        self.assertTrue(any("-mcpu=gfx900" in v for v in variants))
        self.assertTrue(all("-global-isel=0" in v for v in variants))
        self.assertTrue(all(v.startswith("-O") for v in variants))

    def test_heuristic_only_when_no_run_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            added = root / "added-lines"
            added.mkdir()
            with (added / "added-lines.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["path", "line_no", "text"])
                writer.writerow(["llvm/lib/Target/AMDGPU/AMDGPUPromoteAlloca.cpp", "1", "code"])

            variants, _sources = derive_llc_flag_variants(
                pr_run_dir=root,
                gap_target_paths=["llvm/lib/Target/AMDGPU/AMDGPUPromoteAlloca.cpp"],
                exclude_flags=default_exclude_completed_o_levels(),
            )
            self.assertEqual(len(variants), 8)
            self.assertIn("-O0 -global-isel=0", variants)
            self.assertIn("-O3 -global-isel=1", variants)


if __name__ == "__main__":
    unittest.main()
