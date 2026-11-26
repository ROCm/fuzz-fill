"""Unit tests for batch-from-coverage helpers."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from reduce.batch.candidate_test import parse_test_sh
from reduce.batch.coverage import (
    parse_covered_points_field,
    resolve_covered_hexes,
)
from reduce.batch.gap_fill import resolve_batch_inputs
from reduce.batch.pipeline import build_pipeline_steps, parse_pipeline_arg
from reduce.batch.templates import render_interesting_ir


def _interesting_ir_template() -> str:
    return (
        Path(__file__).resolve().parents[1]
        / "src"
        / "reduce"
        / "template_interesting_ir.sh"
    ).read_text(encoding="utf-8")


class ParseCoveredPointsTest(unittest.TestCase):
    def test_empty_field(self) -> None:
        self.assertEqual(parse_covered_points_field(""), [])
        self.assertEqual(parse_covered_points_field("  "), [])

    def test_semicolon_separated_with_prefix(self) -> None:
        self.assertEqual(
            parse_covered_points_field("0x1000;0x2000"),
            ["1000", "2000"],
        )

    def test_resolve_returns_all_points_space_separated(self) -> None:
        covered, hexes = resolve_covered_hexes("0x3000;0x2000")
        self.assertEqual(covered, "0x2000 0x3000")
        self.assertEqual(hexes, ["2000", "3000"])

    def test_resolve_single_point(self) -> None:
        covered, hexes = resolve_covered_hexes("0xabc")
        self.assertEqual(covered, "0xabc")
        self.assertEqual(hexes, ["abc"])


class InterestingIrFullLineTest(unittest.TestCase):
    def _run_interesting(
        self, *, print_addrs: list[str], covered: str
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            llc = bin_dir / "llc"
            llc.write_text(
                "#!/bin/bash\n"
                'covdir="${UBSAN_OPTIONS#*coverage_dir=}"\n'
                'covdir="${covdir%%:*}"\n'
                'touch "$covdir/llc.$$.sancov"\n',
                encoding="utf-8",
            )
            llc.chmod(llc.stat().st_mode | stat.S_IXUSR)
            sancov = bin_dir / "sancov"
            print_body = "\n".join(print_addrs) + "\n"
            sancov.write_text(
                "#!/bin/bash\n"
                'if [[ "$1" == "--print" ]]; then\n'
                f"  cat <<'EOF'\n{print_body}EOF\n"
                "  exit 0\n"
                "fi\n"
                "exit 1\n",
                encoding="utf-8",
            )
            sancov.chmod(sancov.stat().st_mode | stat.S_IXUSR)

            script = root / "interesting_ir.sh"
            script.write_text(
                render_interesting_ir(
                    _interesting_ir_template(),
                    covered=covered,
                    llvm_bin=bin_dir,
                    llc_flags=(),
                ),
                encoding="utf-8",
            )
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
            candidate = root / "candidate.ll"
            candidate.write_text("define void @f() { ret void }\n", encoding="utf-8")
            return subprocess.run(
                [str(script), str(candidate)],
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": os.environ.get("PATH", "")},
            )

    def test_interesting_when_all_points_present(self) -> None:
        proc = self._run_interesting(
            print_addrs=["0x1000", "0x2000", "0x9999"],
            covered="0x1000 0x2000",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_not_interesting_when_one_point_missing(self) -> None:
        proc = self._run_interesting(
            print_addrs=["0x1000"],
            covered="0x1000 0x2000",
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("0x2000 is NOT present", proc.stderr)


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


class ResolveBatchInputsTest(unittest.TestCase):
    def test_resolves_default_output_and_validates_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gap_fill = root / "gap-fill"
            gap_fill.mkdir()
            (gap_fill / "incremental").mkdir()
            (gap_fill / "candidate_tests").mkdir()
            csv = gap_fill / "incremental" / "new_coverage.csv"
            csv.write_text(
                "test_name,file,line,covered-points\n",
                encoding="utf-8",
            )

            csv_path, candidate_tests, out = resolve_batch_inputs(
                gap_fill_dir=gap_fill,
                output=None,
            )
            self.assertEqual(csv_path, csv)
            self.assertEqual(candidate_tests, gap_fill / "candidate_tests")
            self.assertEqual(out, gap_fill / "reduced")

    def test_missing_csv_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gap_fill = Path(tmp) / "gap-fill"
            gap_fill.mkdir()
            (gap_fill / "candidate_tests").mkdir()
            with self.assertRaisesRegex(ValueError, "gap-fill CSV not found"):
                resolve_batch_inputs(gap_fill_dir=gap_fill, output=None)


if __name__ == "__main__":
    unittest.main()
