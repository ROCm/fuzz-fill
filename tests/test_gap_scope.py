"""Unit tests for gap_scope.classifier."""

from __future__ import annotations

import unittest
from pathlib import Path

from gap_scope.classifier import classify_changed_paths
from gap_scope.constants import (
    ALLOWLIST_CLANG,
    ALLOWLIST_LLVM,
    ALLOWLIST_LLVM_CLANG,
)


class ClassifyChangedPathsTest(unittest.TestCase):
    def test_rule1_single_backend(self) -> None:
        scope = classify_changed_paths(
            ["llvm/lib/Target/AMDGPU/SIFoldOperands.cpp"]
        )
        self.assertEqual(scope.rule, 1)
        self.assertEqual(scope.action, "run")
        self.assertEqual(scope.backends, "X86;AMDGPU")
        self.assertEqual(scope.tests, ("llvm/test",))
        self.assertEqual(scope.allowlist, str(ALLOWLIST_LLVM.resolve()))

    def test_rule1_multi_backend(self) -> None:
        scope = classify_changed_paths(
            [
                "llvm/lib/Target/AMDGPU/AMDGPU.h",
                "llvm/lib/Target/SPIRV/SPIRVAsmPrinter.cpp",
                "llvm/test/CodeGen/AMDGPU/foo.ll",
            ]
        )
        self.assertEqual(scope.rule, 1)
        self.assertEqual(scope.action, "run")
        self.assertEqual(scope.backends, "X86;AMDGPU;SPIRV")
        self.assertEqual(scope.tests, ("llvm/test",))
        self.assertEqual(scope.allowlist, str(ALLOWLIST_LLVM.resolve()))

    def test_rule1_ignores_test_paths(self) -> None:
        scope = classify_changed_paths(
            [
                "llvm/lib/Target/AMDGPU/SIInstrInfo.cpp",
                "llvm/test/CodeGen/AMDGPU/new.ll",
                "llvm/unittests/Target/AMDGPU/DwarfRegMappings.cpp",
            ]
        )
        self.assertEqual(scope.rule, 1)
        self.assertEqual(scope.backends, "X86;AMDGPU")

    def test_rule2_clang_lib_only(self) -> None:
        scope = classify_changed_paths(
            [
                "clang/lib/CodeGen/CodeGenAction.cpp",
                "clang/test/CodeGen/foo.c",
            ]
        )
        self.assertEqual(scope.rule, 2)
        self.assertEqual(scope.action, "run")
        self.assertEqual(scope.backends, "all")
        self.assertEqual(scope.tests, ("clang/test",))
        self.assertEqual(scope.allowlist, str(ALLOWLIST_CLANG.resolve()))

    def test_rule3_llvm_lib_non_backend(self) -> None:
        scope = classify_changed_paths(
            ["llvm/lib/Transforms/Scalar/SROA.cpp"]
        )
        self.assertEqual(scope.rule, 3)
        self.assertEqual(scope.action, "run")
        self.assertEqual(scope.backends, "all")
        self.assertEqual(scope.tests, ("llvm/test", "clang/test"))
        self.assertEqual(scope.allowlist, str(ALLOWLIST_LLVM_CLANG.resolve()))

    def test_rule3_mixed_backend_and_middle_end(self) -> None:
        scope = classify_changed_paths(
            [
                "llvm/lib/Target/AMDGPU/AMDGPU.h",
                "llvm/lib/IR/Function.cpp",
            ]
        )
        self.assertEqual(scope.rule, 3)
        self.assertEqual(scope.backends, "all")

    def test_rule3_llvm_and_clang_lib(self) -> None:
        scope = classify_changed_paths(
            [
                "llvm/lib/Support/raw_ostream.cpp",
                "clang/lib/Driver/Driver.cpp",
            ]
        )
        self.assertEqual(scope.rule, 3)
        self.assertEqual(scope.tests, ("llvm/test", "clang/test"))
        self.assertEqual(scope.allowlist, str(ALLOWLIST_LLVM_CLANG.resolve()))

    def test_rule4_test_only(self) -> None:
        scope = classify_changed_paths(
            ["llvm/test/CodeGen/AMDGPU/foo.ll", "clang/test/Sema/bar.c"]
        )
        self.assertEqual(scope.rule, 4)
        self.assertEqual(scope.action, "skip")
        self.assertEqual(scope.tests, ())
        self.assertEqual(scope.allowlist, "")

    def test_rule4_docs_only(self) -> None:
        scope = classify_changed_paths(["llvm/docs/LangRef.rst"])
        self.assertEqual(scope.rule, 4)
        self.assertEqual(scope.action, "skip")

    def test_rule4_target_cmake_alone_is_not_backend_file(self) -> None:
        # Target/CMakeLists.txt is under Target/ but not Target/<Backend>/.
        scope = classify_changed_paths(["llvm/lib/Target/CMakeLists.txt"])
        self.assertEqual(scope.rule, 3)

    def test_allowlist_files_exist(self) -> None:
        for path in (ALLOWLIST_LLVM, ALLOWLIST_CLANG, ALLOWLIST_LLVM_CLANG):
            self.assertTrue(Path(path).is_file(), msg=str(path))


if __name__ == "__main__":
    unittest.main()
