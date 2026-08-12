"""Unit tests for batch-from-coverage scaffolding."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from reduce.batch.candidate_test import parse_test_sh
from reduce.batch.coverage import (
    parse_covered_points_field,
    resolve_covered_hexes,
)
from reduce.batch.pipeline import build_pipeline_steps, parse_pipeline_arg
from reduce.batch_from_coverage import main as batch_main

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "reduction-batch"
REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "example" / "amd" / "new-test-1"


def _materialize_candidate_tests(root: Path) -> Path:
    """Build candidate_tests/ tree with absolute paths in each test.sh."""
    candidate_tests = root / "candidate_tests"
    llc = root / "fake-llvm" / "bin" / "llc"
    llc.parent.mkdir(parents=True)
    llc.write_text("#!/bin/sh\n", encoding="utf-8")
    llc.chmod(0o755)
    sample_bc = FIXTURES / "sample.bc"

    for name in ("test-a", "test-b", "test-c"):
        test_dir = candidate_tests / name
        test_dir.mkdir(parents=True)
        bc_dest = test_dir / "sample.bc"
        shutil.copy2(sample_bc, bc_dest)
        script = test_dir / "test.sh"
        script.write_text(
            f"#!/bin/bash\n{llc} -O1 -mtriple=amdgcn-amd-amdhsa {bc_dest}\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
    return candidate_tests


def _run_batch_scaffold(*, output: Path, n: int | None) -> int:
    args = [
        "--csv",
        str(FIXTURES / "new_coverage.csv"),
        "--candidate-tests",
        str(output / "candidate_tests"),
        "--output",
        str(output / "out"),
        "--template-dir",
        str(TEMPLATE_DIR),
    ]
    if n is not None:
        args.extend(["--n", str(n)])
    return batch_main(args)


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


class PrepareBatchCasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _materialize_candidate_tests(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_n1_creates_one_case(self) -> None:
        rc = _run_batch_scaffold(output=self.root, n=1)
        self.assertEqual(rc, 0)
        out = self.root / "out"
        cases = sorted(out.glob("t-*"))
        self.assertEqual(len(cases), 1)
        self.assertTrue(cases[0].name.startswith("t-00001-test-a"))
        config = json.loads((cases[0] / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["line"], 100)
        self.assertEqual(config["file"], "llvm/lib/Target/AMDGPU/FooA.cpp")
        self.assertTrue((cases[0] / "interesting_ir.sh").is_file())
        ir = (cases[0] / "interesting_ir.sh").read_text(encoding="utf-8")
        self.assertIn('COVERED="0x1000"', ir)

    def test_n3_creates_three_cases(self) -> None:
        rc = _run_batch_scaffold(output=self.root, n=3)
        self.assertEqual(rc, 0)
        out = self.root / "out"
        cases = sorted(out.glob("t-*"))
        self.assertEqual(len(cases), 3)
        self.assertTrue(cases[0].name.startswith("t-00001-test-a"))
        self.assertTrue(cases[1].name.startswith("t-00002-test-b"))
        self.assertTrue(cases[2].name.startswith("t-00003-test-c"))
        ir_b = (cases[1] / "interesting_ir.sh").read_text(encoding="utf-8")
        self.assertIn('COVERED="0x2000"', ir_b)

    def test_n_exceeds_row_count_processes_all_rows(self) -> None:
        rc = _run_batch_scaffold(output=self.root, n=5)
        self.assertEqual(rc, 0)
        out = self.root / "out"
        self.assertEqual(len(list(out.glob("t-*"))), 3)


if __name__ == "__main__":
    unittest.main()
