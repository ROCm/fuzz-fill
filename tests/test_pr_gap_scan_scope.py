"""Discovery's file check stays aligned with gap-scope --auto."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from gap_scope.classifier import classify_changed_paths

_SCAN = (
    Path(__file__).resolve().parents[1]
    / ".claude/skills/pr-gap-scan/scripts/scan.py"
)
_spec = importlib.util.spec_from_file_location("pr_gap_scan", _SCAN)
assert _spec is not None and _spec.loader is not None
scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scan)


class AutoWouldRunTest(unittest.TestCase):
    def test_agrees_with_classifier(self) -> None:
        cases = [
            ["llvm/lib/Target/AMDGPU/SIFoldOperands.cpp"],
            [
                "llvm/lib/Target/SPIRV/SPIRVAsmPrinter.cpp",
                "llvm/test/CodeGen/SPIRV/foo.ll",
            ],
            ["clang/lib/Driver/ToolChains/AMDGPU.cpp"],
            ["llvm/lib/Transforms/Scalar/SROA.cpp"],
            ["llvm/lib/Target/AMDGPU/AMDGPU.h", "llvm/lib/IR/Function.cpp"],
            ["llvm/test/CodeGen/AMDGPU/foo.ll"],
            ["llvm/docs/AMDGPUUsage.rst"],
            ["llvm/lib/Target/CMakeLists.txt"],
            [
                "llvm/unittests/Target/AMDGPU/DwarfRegMappings.cpp",
                "llvm/lib/Target/AMDGPU/SIInstrInfo.cpp",
            ],
        ]
        for paths in cases:
            with self.subTest(paths=paths):
                would_run = classify_changed_paths(paths).action == "run"
                self.assertEqual(scan.auto_would_run(paths), would_run)

    def test_target_dirs_attribute_both_backends(self) -> None:
        paths = [
            "llvm/lib/Target/AMDGPU/AMDGPU.h",
            "llvm/lib/Target/SPIRV/SPIRVAsmPrinter.cpp",
        ]
        self.assertEqual(
            scan.attribute_backends(paths, {"backend:AMDGPU"}, {"amdgpu", "spirv"}),
            ["amdgpu", "spirv"],
        )

    def test_label_fallback_for_non_target_lib_change(self) -> None:
        paths = [
            "clang/lib/Driver/ToolChains/AMDGPU.cpp",
            "llvm/test/CodeGen/AMDGPU/foo.ll",
        ]
        self.assertTrue(scan.auto_would_run(paths))
        self.assertEqual(
            scan.attribute_backends(paths, {"backend:AMDGPU"}, {"amdgpu", "spirv"}),
            ["amdgpu"],
        )

    def test_test_only_is_not_analyzable(self) -> None:
        paths = [
            "llvm/test/CodeGen/AMDGPU/foo.ll",
            "llvm/test/CodeGen/SPIRV/bar.ll",
        ]
        self.assertFalse(scan.auto_would_run(paths))

    def test_source_path_wins_over_an_extra_label(self) -> None:
        paths = [
            "llvm/lib/Target/AMDGPU/SIInstrInfo.cpp",
            "llvm/test/CodeGen/SPIRV/foo.ll",
        ]
        self.assertEqual(
            scan.attribute_backends(
                paths,
                {"backend:AMDGPU", "backend:SPIR-V"},
                {"amdgpu", "spirv"},
            ),
            ["amdgpu"],
        )


class GroupLibGateTest(unittest.TestCase):
    def test_llvm_lib_paths_match(self) -> None:
        prefixes = scan.GROUP_CONFIGS["llvm"]["lib_prefixes"]
        self.assertTrue(
            scan.group_has_lib_change(
                ["llvm/lib/Transforms/Scalar/SROA.cpp", "llvm/test/Transforms/foo.ll"],
                prefixes,
            )
        )
        self.assertTrue(
            scan.group_has_lib_change(["llvm/lib/IR/Function.cpp"], prefixes)
        )
        self.assertTrue(
            scan.group_has_lib_change(["llvm/lib/Analysis/ValueTracking.cpp"], prefixes)
        )

    def test_llvm_test_only_does_not_match(self) -> None:
        prefixes = scan.GROUP_CONFIGS["llvm"]["lib_prefixes"]
        self.assertFalse(
            scan.group_has_lib_change(
                [
                    "llvm/test/Transforms/SROA/foo.ll",
                    "llvm/unittests/Transforms/Foo.cpp",
                    "llvm/include/llvm/Transforms/Scalar/SROA.h",
                    "llvm/docs/LangRef.md",
                ],
                prefixes,
            )
        )

    def test_clang_lib_paths_match(self) -> None:
        prefixes = scan.GROUP_CONFIGS["clang"]["lib_prefixes"]
        self.assertTrue(
            scan.group_has_lib_change(
                ["clang/lib/CodeGen/CodeGenAction.cpp", "clang/test/CodeGen/foo.c"],
                prefixes,
            )
        )

    def test_clang_test_only_does_not_match(self) -> None:
        prefixes = scan.GROUP_CONFIGS["clang"]["lib_prefixes"]
        self.assertFalse(
            scan.group_has_lib_change(
                ["clang/test/CodeGen/foo.c", "clang/unittests/CodeGen/Foo.cpp"],
                prefixes,
            )
        )


class LibDiffSizeTest(unittest.TestCase):
    def test_sums_matching_lib_files_only(self) -> None:
        prefixes = scan.GROUP_CONFIGS["llvm"]["lib_prefixes"]
        files = [
            {"filename": "llvm/lib/Transforms/Scalar/SROA.cpp", "additions": 10, "deletions": 2},
            {"filename": "llvm/lib/IR/Function.cpp", "additions": 3, "deletions": 1},
            {"filename": "llvm/test/Transforms/SROA/foo.ll", "additions": 1000, "deletions": 500},
            {"filename": "llvm/unittests/Transforms/Foo.cpp", "additions": 200, "deletions": 0},
            {"filename": "llvm/include/llvm/Transforms/Scalar/SROA.h", "additions": 50, "deletions": 0},
            {"filename": "clang/lib/Driver/Driver.cpp", "additions": 99, "deletions": 0},
        ]
        self.assertEqual(scan.lib_diff_size(files, prefixes), 16)

    def test_clang_excludes_tests(self) -> None:
        prefixes = scan.GROUP_CONFIGS["clang"]["lib_prefixes"]
        files = [
            {"filename": "clang/lib/Sema/SemaExpr.cpp", "additions": 7, "deletions": 3},
            {"filename": "clang/test/Sema/foo.c", "additions": 400, "deletions": 0},
        ]
        self.assertEqual(scan.lib_diff_size(files, prefixes), 10)


class SelectTopByLibSizeTest(unittest.TestCase):
    def test_larger_lib_diff_wins_quota(self) -> None:
        candidates = [
            {
                "number": 1,
                "lib_diff_size": 5,
                "updated_at": "2026-10-27T12:00:00Z",
            },
            {
                "number": 2,
                "lib_diff_size": 50,
                "updated_at": "2026-10-20T12:00:00Z",
            },
            {
                "number": 3,
                "lib_diff_size": 20,
                "updated_at": "2026-10-26T12:00:00Z",
            },
        ]
        kept = scan.select_top_by_lib_size(candidates, limit=2)
        self.assertEqual([c["number"] for c in kept], [2, 3])

    def test_tie_breaks_toward_more_recent(self) -> None:
        candidates = [
            {
                "number": 1,
                "lib_diff_size": 10,
                "updated_at": "2026-10-01T00:00:00Z",
            },
            {
                "number": 2,
                "lib_diff_size": 10,
                "updated_at": "2026-10-27T00:00:00Z",
            },
        ]
        kept = scan.select_top_by_lib_size(candidates, limit=1)
        self.assertEqual(kept[0]["number"], 2)

    def test_test_only_never_eligible_via_gate(self) -> None:
        prefixes = scan.GROUP_CONFIGS["llvm"]["lib_prefixes"]
        self.assertFalse(
            scan.group_has_lib_change(["llvm/test/Transforms/foo.ll"], prefixes)
        )


class MergeCandidatesTest(unittest.TestCase):
    def test_dedupes_overlap_and_merges_categories(self) -> None:
        amdgpu = [
            {
                "number": 10,
                "backends": ["amdgpu"],
                "title": "gpu",
                "updated_at": "2026-10-01T00:00:00Z",
            },
            {
                "number": 11,
                "backends": ["amdgpu"],
                "title": "gpu-only",
                "updated_at": "2026-10-02T00:00:00Z",
            },
        ]
        llvm = [
            {
                "number": 10,
                "backends": ["llvm"],
                "group": "llvm",
                "labels": ["llvm:transforms"],
                "lib_diff_size": 40,
                "title": "gpu",
                "updated_at": "2026-10-01T00:00:00Z",
            },
            {
                "number": 12,
                "backends": ["llvm"],
                "group": "llvm",
                "labels": ["llvm:ir"],
                "lib_diff_size": 5,
                "title": "ir-only",
                "updated_at": "2026-10-03T00:00:00Z",
            },
        ]
        merged = scan.merge_candidates_by_number([amdgpu, llvm])
        by_num = {c["number"]: c for c in merged}
        self.assertEqual(sorted(by_num), [10, 11, 12])
        self.assertEqual(by_num[10]["categories"], ["amdgpu", "llvm"])
        self.assertEqual(by_num[10]["backends"], ["amdgpu", "llvm"])
        self.assertEqual(by_num[10]["lib_diff_size"], 40)
        self.assertEqual(by_num[11]["categories"], ["amdgpu"])
        self.assertEqual(by_num[12]["categories"], ["llvm"])

    def test_normalize_categories_folds_aliases(self) -> None:
        self.assertEqual(
            scan.normalize_categories(
                categories=["llvm", "amdgpu"],
                backends=["amdgpu", "spirv"],
                group=["clang", "llvm"],
            ),
            ["llvm", "amdgpu", "spirv", "clang"],
        )
        self.assertEqual(scan.normalize_categories(), [])


if __name__ == "__main__":
    unittest.main()
