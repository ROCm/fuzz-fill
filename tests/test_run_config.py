"""Tests for coverage.run_config."""

import json
import tempfile
import unittest
from pathlib import Path

from coverage.constants import (
    DEFAULT_LIT_FILTER,
    DEFAULT_LIT_FILTER_AMDGPU_DIRS,
    DEFAULT_PATH_FILTER,
)
from coverage.run_config import (
    _is_simple_codegen_lit_filter,
    build_run_config,
    resolved_path_filter,
    write_run_config,
)


class TestRunConfig(unittest.TestCase):
    def test_is_simple_codegen_lit_filter(self) -> None:
        self.assertTrue(_is_simple_codegen_lit_filter("CodeGen/AMDGPU"))
        self.assertTrue(_is_simple_codegen_lit_filter("CodeGen/AMDGPU/loop"))
        self.assertFalse(_is_simple_codegen_lit_filter(DEFAULT_LIT_FILTER_AMDGPU_DIRS))
        self.assertFalse(_is_simple_codegen_lit_filter("MC/AMDGPU"))

    def test_resolved_path_filter_explicit(self) -> None:
        self.assertEqual(
            resolved_path_filter(
                lit_filter=DEFAULT_LIT_FILTER_AMDGPU_DIRS,
                path_filter="llvm/lib/Target/SPIRV",
            ),
            "llvm/lib/Target/SPIRV",
        )

    def test_resolved_path_filter_codegen_derived(self) -> None:
        self.assertEqual(
            resolved_path_filter(lit_filter="CodeGen/SPIRV", path_filter=None),
            "llvm/lib/Target/SPIRV",
        )

    def test_resolved_path_filter_regex_default(self) -> None:
        self.assertEqual(
            resolved_path_filter(
                lit_filter=DEFAULT_LIT_FILTER_AMDGPU_DIRS,
                path_filter=None,
            ),
            DEFAULT_PATH_FILTER,
        )

    def test_build_run_config_defaults(self) -> None:
        config = build_run_config(lit_filter=None)
        self.assertEqual(config["lit_filter"], DEFAULT_LIT_FILTER)
        self.assertEqual(config["path_filter"], "llvm/lib/Target/AMDGPU")

    def test_build_run_config_amdgpu_dirs_regex(self) -> None:
        config = build_run_config(lit_filter=DEFAULT_LIT_FILTER_AMDGPU_DIRS)
        self.assertEqual(config["lit_filter"], DEFAULT_LIT_FILTER_AMDGPU_DIRS)
        self.assertEqual(config["path_filter"], DEFAULT_PATH_FILTER)

    def test_build_run_config_explicit_path_filter(self) -> None:
        config = build_run_config(
            lit_filter=DEFAULT_LIT_FILTER_AMDGPU_DIRS,
            path_filter="llvm/lib/Target/AMDGPU",
        )
        self.assertEqual(config["path_filter"], "llvm/lib/Target/AMDGPU")

    def test_write_run_config_json_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_run_config(
                out,
                lit_filter=DEFAULT_LIT_FILTER_AMDGPU_DIRS,
                path_filter=DEFAULT_PATH_FILTER,
            )
            with (out / "run_config.json").open(encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["lit_filter"], DEFAULT_LIT_FILTER_AMDGPU_DIRS)
            self.assertEqual(data["path_filter"], DEFAULT_PATH_FILTER)


if __name__ == "__main__":
    unittest.main()
