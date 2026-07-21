"""Tests for coverage.run_config."""

import json
import tempfile
import unittest
from pathlib import Path

from coverage.constants import DEFAULT_LIT_FILTER, DEFAULT_PATH_FILTER
from coverage.run_config import (
    build_lit_filter_regex,
    build_run_config,
    load_run_config,
    resolved_lit_filters,
    resolved_path_filter,
    write_run_config,
)


class TestRunConfig(unittest.TestCase):
    def test_resolved_lit_filters_default(self) -> None:
        self.assertEqual(resolved_lit_filters(None), [DEFAULT_LIT_FILTER])

    def test_build_lit_filter_regex_single_prefix(self) -> None:
        self.assertEqual(
            build_lit_filter_regex(["CodeGen/AMDGPU"]),
            "CodeGen/AMDGPU",
        )

    def test_build_lit_filter_regex_single_regex_passthrough(self) -> None:
        regex = r"CodeGen/AMDGPU/loop-live-out-copy-undef-subrange\.ll$"
        self.assertEqual(build_lit_filter_regex([regex]), regex)

    def test_build_lit_filter_regex_multiple_prefixes(self) -> None:
        self.assertEqual(
            build_lit_filter_regex(["CodeGen/AMDGPU", "MC/AMDGPU"]),
            "CodeGen/AMDGPU|MC/AMDGPU",
        )

    def test_resolved_path_filter_default(self) -> None:
        self.assertEqual(resolved_path_filter(None), DEFAULT_PATH_FILTER)

    def test_resolved_path_filter_explicit(self) -> None:
        self.assertEqual(
            resolved_path_filter("llvm/lib/Target/SPIRV"),
            "llvm/lib/Target/SPIRV",
        )

    def test_build_run_config_defaults(self) -> None:
        config = build_run_config()
        self.assertEqual(config["lit_filters"], [DEFAULT_LIT_FILTER])
        self.assertEqual(config["lit_filter_regex"], DEFAULT_LIT_FILTER)
        self.assertEqual(config["path_filter"], DEFAULT_PATH_FILTER)

    def test_build_run_config_multi_filter_fixed_path(self) -> None:
        config = build_run_config(
            lit_filters=["CodeGen/AMDGPU", "MC/AMDGPU", "Target/AMDGPU"],
            path_filter="llvm/lib/Target/AMDGPU",
        )
        self.assertEqual(
            config["lit_filter_regex"],
            "CodeGen/AMDGPU|MC/AMDGPU|Target/AMDGPU",
        )
        self.assertEqual(config["path_filter"], "llvm/lib/Target/AMDGPU")

    def test_write_and_load_run_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_run_config(
                out,
                lit_filters=["CodeGen/AMDGPU", "MC/AMDGPU"],
                path_filter="llvm/lib/Target/AMDGPU",
            )
            loaded = load_run_config(out)
            self.assertEqual(loaded["lit_filters"], ["CodeGen/AMDGPU", "MC/AMDGPU"])
            self.assertEqual(loaded["path_filter"], "llvm/lib/Target/AMDGPU")

            with (out / "run_config.json").open(encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("lit_filters", data)
            self.assertIn("lit_filter_regex", data)
            self.assertNotIn("lit_filter", data)


if __name__ == "__main__":
    unittest.main()
