"""Unit tests for batch-from-coverage helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reduce.batch.candidate_test import parse_test_sh
from reduce.batch.coverage import (
    parse_covered_points_field,
    resolve_covered_hexes,
)
from reduce.batch.pipeline import build_pipeline_steps, parse_pipeline_arg


class ParseCoveredPointsTest(unittest.TestCase):
    def test_empty_field(self) -> None:
        self.assertEqual(parse_covered_points_field(""), [])
        self.assertEqual(parse_covered_points_field("  "), [])

    def test_semicolon_separated_with_prefix(self) -> None:
        self.assertEqual(
            parse_covered_points_field("0x1000;0x2000"),
            ["1000", "2000"],
        )

    def test_resolve_picks_lowest_address(self) -> None:
        covered, hexes = resolve_covered_hexes("0x3000;0x2000")
        self.assertEqual(covered, "0x2000")
        self.assertEqual(hexes, ["2000", "3000"])


class ParseTestShTest(unittest.TestCase):
    def test_parses_llc_flags_and_bc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bc = root / "kernel.bc"
            bc.write_bytes(b"BC")
            llc = root / "bin" / "llc"
            llc.parent.mkdir()
            llc.write_text("#!/bin/sh\n", encoding="utf-8")
            test_sh = root / "test.sh"
            test_sh.write_text(
                f"#!/bin/bash\n{llc} -O1 -mtriple=amdgcn {bc} > /dev/null\n",
                encoding="utf-8",
            )
            info = parse_test_sh(test_sh)
            self.assertEqual(info.bc_path, bc)
            self.assertEqual(info.llc_flags, ("-O1", "-mtriple=amdgcn"))
            self.assertEqual(info.llvm_bin, llc.parent)

    def test_parses_timeout_wrapped_llc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bc = root / "kernel.bc"
            bc.write_bytes(b"BC")
            llc = root / "bin" / "llc"
            llc.parent.mkdir()
            llc.write_text("#!/bin/sh\n", encoding="utf-8")
            test_sh = root / "test.sh"
            test_sh.write_text(
                "#!/bin/bash\n"
                f"timeout -s9 5 {llc} -O3 -global-isel=1 {bc} -o /dev/null\n",
                encoding="utf-8",
            )
            info = parse_test_sh(test_sh)
            self.assertEqual(info.bc_path, bc)
            self.assertEqual(info.llc_flags, ("-O3", "-global-isel=1"))
            self.assertEqual(info.llvm_bin, llc.parent)

    def test_resolves_ll_via_corpus_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "corpus"
            corpus.mkdir()
            ll_file = corpus / "standalone-empty-kernel.ll"
            ll_file.write_text("define void @f() { ret void }\n", encoding="utf-8")
            llc = root / "bin" / "llc"
            llc.parent.mkdir()
            llc.write_text("#!/bin/sh\n", encoding="utf-8")
            test_dir = root / "test_7_standalone-empty-kernel.ll"
            test_dir.mkdir()
            test_sh = test_dir / "test.sh"
            test_sh.write_text(
                "#!/bin/bash\n"
                "timeout -s9 5 /work/llvm-build-sancov/bin/llc -O3 -global-isel=1 "
                "/mounted-candidate-tests/standalone-empty-kernel.ll -o /dev/null\n",
                encoding="utf-8",
            )
            info = parse_test_sh(
                test_sh,
                test_name="test_7_standalone-empty-kernel.ll",
                corpus_dir=corpus,
            )
            self.assertEqual(info.bc_path, ll_file)
            self.assertEqual(info.llc_flags, ("-O3", "-global-isel=1"))


class BuildPipelineStepsTest(unittest.TestCase):
    def test_default_ir_pipeline(self) -> None:
        steps = build_pipeline_steps(
            parse_pipeline_arg("llvm_reduce_ir"),
            pass_under_test=None,
            mtriple=None,
            llc_flags=("-O1",),
            extract_mir_output=None,
            extract_ir_output=None,
            creduce_n=None,
        )
        self.assertEqual(steps[0]["id"], "llvm_reduce_ir")
        self.assertEqual(
            steps[0]["parameters"]["interesting"],
            "interesting_ir.sh",
        )


if __name__ == "__main__":
    unittest.main()
