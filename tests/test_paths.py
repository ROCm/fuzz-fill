from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coverage.paths import canonicalize_source_path


class TestCanonicalizeSourcePath(unittest.TestCase):
    def test_relative_in_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "llvm-project"
            source = root / "llvm/lib/IR/Value.cpp"
            source.parent.mkdir(parents=True)
            source.touch()

            self.assertEqual(
                canonicalize_source_path("llvm/lib/IR/Value.cpp", root),
                "llvm/lib/IR/Value.cpp",
            )

    def test_absolute_in_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "llvm-project"
            source = root / "clang/lib/Basic/SourceManager.cpp"
            source.parent.mkdir(parents=True)
            source.touch()

            self.assertEqual(
                canonicalize_source_path(source, root),
                "clang/lib/Basic/SourceManager.cpp",
            )

    def test_outside_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "llvm-project"
            outside = base / "outside.cpp"
            root.mkdir()
            outside.touch()

            self.assertIsNone(canonicalize_source_path(outside, root))


if __name__ == "__main__":
    unittest.main()
