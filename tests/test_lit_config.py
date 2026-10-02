"""Tests for coverage.lit_config helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coverage.constants import (
    BASELINE_LIT_PRIORITY_ELAPSED,
    BASELINE_LIT_PRIORITY_TESTS,
)
from coverage.lit_config import (
    LitSuiteRun,
    _read_lit_test_times,
    _write_lit_test_times,
    build_lit_filter_regex,
    ensure_lit_suites_sancov_env_forwarding,
    filter_existing_lit_priority_tests,
    finalize_lit_suite_runs,
    find_lit_site_config,
    is_llvm_lit_suite,
    lit_suite_root_name,
    lit_suite_subdir,
    lit_test_suite_path,
    lit_test_times_path,
    llvm_test_source_root,
    normalize_lit_suite_spec,
    resolve_lit_suite_paths,
    seed_lit_priority_test_times,
)


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

    def test_multiple_regex_prefixes(self) -> None:
        self.assertEqual(
            build_lit_filter_regex(["CodeGen/AMDGPU", "Analysis/[^/]+/AMDGPU"]),
            "CodeGen/AMDGPU|Analysis/[^/]+/AMDGPU",
        )

    def test_multiple_regex_passthrough(self) -> None:
        self.assertEqual(
            build_lit_filter_regex(["CodeGen/AMDGPU", "(^|/)AMDGPU/"]),
            "CodeGen/AMDGPU|(^|/)AMDGPU",
        )

    def test_empty_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_lit_filter_regex([])

    def test_blank_entries_ignored(self) -> None:
        self.assertEqual(
            build_lit_filter_regex(["", "  ", "CodeGen/AMDGPU"]),
            "CodeGen/AMDGPU",
        )

    def test_amdgpu_workflow_filters(self) -> None:
        # Keep in sync with scripts/lit-filters-amdgpu.sh
        filters = [r"(?:^|/)AMDGPU(?:/|$)"]
        combined = build_lit_filter_regex(filters)
        self.assertEqual(combined, r"(?:^|/)AMDGPU(?:/|$)")


class TestLitSuiteSpec(unittest.TestCase):
    def test_normalize_strips_slashes(self) -> None:
        self.assertEqual(
            normalize_lit_suite_spec("/llvm/test/CodeGen/AMDGPU/"),
            "llvm/test/CodeGen/AMDGPU",
        )

    def test_root_and_subdir(self) -> None:
        self.assertEqual(lit_suite_root_name("llvm/test"), "llvm/test")
        self.assertEqual(lit_suite_subdir("llvm/test"), "")
        self.assertEqual(
            lit_suite_root_name("llvm/test/CodeGen/AMDGPU"),
            "llvm/test",
        )
        self.assertEqual(
            lit_suite_subdir("llvm/test/CodeGen/AMDGPU"),
            "CodeGen/AMDGPU",
        )
        self.assertEqual(
            lit_suite_root_name("clang/test/Sema"),
            "clang/test",
        )
        self.assertEqual(lit_suite_root_name("lld/test/ELF"), "lld/test")
        self.assertEqual(lit_suite_subdir("lld/test/ELF"), "ELF")
        self.assertTrue(is_llvm_lit_suite("llvm/test/MC/AMDGPU"))
        self.assertFalse(is_llvm_lit_suite("clang/test"))

    def test_unsupported_suite(self) -> None:
        with self.assertRaises(ValueError):
            lit_suite_root_name("CodeGen/AMDGPU")


class TestResolveLitSuitePaths(unittest.TestCase):
    def test_root_and_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp) / "build"
            llvm_lit = build_root / "bin" / "llvm-lit"
            suite_root = lit_test_suite_path(llvm_lit)
            suite_root.mkdir(parents=True)
            llvm_lit.parent.mkdir(parents=True)

            self.assertEqual(
                resolve_lit_suite_paths(llvm_lit, ["llvm/test"]),
                [suite_root],
            )
            self.assertEqual(
                resolve_lit_suite_paths(
                    llvm_lit,
                    ["llvm/test/CodeGen/AMDGPU"],
                ),
                [suite_root / "CodeGen" / "AMDGPU"],
            )
            clang_root = build_root / "tools" / "clang" / "test"
            lld_root = build_root / "tools" / "lld" / "test"
            clang_root.mkdir(parents=True)
            lld_root.mkdir(parents=True)
            self.assertEqual(
                resolve_lit_suite_paths(llvm_lit, ["clang/test/Sema", "lld/test/ELF"]),
                [clang_root / "Sema", lld_root / "ELF"],
            )


class TestLitSuiteRun(unittest.TestCase):
    def test_unfiltered_suite(self) -> None:
        run = LitSuiteRun(suite="llvm/test")
        self.assertIsNone(run.lit_filter())

    def test_single_filter(self) -> None:
        run = LitSuiteRun(suite="llvm/test", filters=["CodeGen/AMDGPU"])
        self.assertEqual(run.lit_filter(), "CodeGen/AMDGPU")

    def test_multiple_filters_or(self) -> None:
        run = LitSuiteRun(
            suite="llvm/test",
            filters=["CodeGen/AMDGPU", "MC/AMDGPU"],
        )
        self.assertEqual(run.lit_filter(), "CodeGen/AMDGPU|MC/AMDGPU")

    def test_finalize_accepts_subdirectory(self) -> None:
        runs = finalize_lit_suite_runs(
            [LitSuiteRun(suite="llvm/test/CodeGen/AMDGPU")]
        )
        self.assertEqual(runs[0].suite, "llvm/test/CodeGen/AMDGPU")

    def test_finalize_requires_tests(self) -> None:
        with self.assertRaises(ValueError):
            finalize_lit_suite_runs(None)
        with self.assertRaises(ValueError):
            finalize_lit_suite_runs([])

    def test_finalize_rejects_unknown_suite(self) -> None:
        with self.assertRaises(ValueError):
            finalize_lit_suite_runs([LitSuiteRun(suite="CodeGen/AMDGPU")])


class TestLitSiteConfigDiscovery(unittest.TestCase):
    def test_walks_up_to_suite_site_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp) / "build"
            llvm_lit = build_root / "bin" / "llvm-lit"
            llvm_lit.parent.mkdir(parents=True)
            for relative in (
                Path("test") / "lit.site.cfg.py",
                Path("tools") / "lld" / "test" / "lit.site.cfg.py",
            ):
                path = build_root / relative
                path.parent.mkdir(parents=True)
                path.write_text("config.test_exec_root = path(r'.')\n", encoding="utf-8")

            lld_case = build_root / "tools" / "lld" / "test" / "ELF"
            self.assertEqual(
                find_lit_site_config(lld_case, build_root),
                build_root / "tools" / "lld" / "test" / "lit.site.cfg.py",
            )

            patched = ensure_lit_suites_sancov_env_forwarding(
                llvm_lit,
                ["llvm/test/CodeGen/AMDGPU", "lld/test/ELF", "llvm/test/MC/AMDGPU"],
            )
            self.assertEqual(
                patched,
                [
                    build_root / "test" / "lit.site.cfg.py",
                    build_root / "tools" / "lld" / "test" / "lit.site.cfg.py",
                ],
            )
            for path in patched:
                self.assertIn("fuzz-fill: SanitizerCoverage env forwarding", path.read_text())

class LitTestTimesIOTest(unittest.TestCase):
    def test_read_skips_malformed_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".lit_test_times.txt"
            path.write_text(
                "1.5 good.txt\n"
                "bad-line\n"
                "not-a-float other.txt\n",
                encoding="utf-8",
            )
            self.assertEqual(_read_lit_test_times(path), {"good.txt": 1.5})

    def test_write_uses_scientific_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".lit_test_times.txt"
            _write_lit_test_times(path, {"bbb.txt": 2.0, "aaa.txt": 0.1})
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "1.000000e-01 aaa.txt\n2.000000e+00 bbb.txt\n",
            )


class SeedLitPriorityTestTimesTest(unittest.TestCase):
    def _make_build_tree(self, tmp: str) -> tuple[Path, Path]:
        build_root = Path(tmp) / "build"
        llvm_lit = build_root / "bin" / "llvm-lit"
        llvm_src = Path(tmp) / "llvm"
        test_root = llvm_src / "test"
        site_cfg = build_root / "test" / "lit.site.cfg.py"
        site_cfg.parent.mkdir(parents=True)
        site_cfg.write_text(
            f'config.llvm_src_root = path(r"{llvm_src}")\n',
            encoding="utf-8",
        )
        llvm_lit.parent.mkdir(parents=True)
        return llvm_lit, test_root

    def test_creates_file_with_priority_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            llvm_lit, test_root = self._make_build_tree(tmp)
            for path_in_suite in BASELINE_LIT_PRIORITY_TESTS:
                test_path = test_root / path_in_suite
                test_path.parent.mkdir(parents=True, exist_ok=True)
                test_path.write_text("; lit test\n", encoding="utf-8")

            path = seed_lit_priority_test_times(llvm_lit, BASELINE_LIT_PRIORITY_TESTS)

            self.assertEqual(path, lit_test_times_path(llvm_lit))
            times = _read_lit_test_times(path)
            for test_path in BASELINE_LIT_PRIORITY_TESTS:
                self.assertEqual(times[test_path], BASELINE_LIT_PRIORITY_ELAPSED)

    def test_filter_existing_skips_missing_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            llvm_lit, test_root = self._make_build_tree(tmp)
            present = BASELINE_LIT_PRIORITY_TESTS[0]
            present_path = test_root / present
            present_path.parent.mkdir(parents=True, exist_ok=True)
            present_path.write_text("; lit test\n", encoding="utf-8")

            filtered = filter_existing_lit_priority_tests(
                llvm_lit,
                (present, "CodeGen/AMDGPU/does-not-exist.ll"),
            )

            self.assertEqual(filtered, (present,))

    def test_filter_existing_returns_empty_when_none_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            llvm_lit, _test_root = self._make_build_tree(tmp)

            filtered = filter_existing_lit_priority_tests(
                llvm_lit,
                ("CodeGen/AMDGPU/does-not-exist.ll",),
            )

            self.assertEqual(filtered, ())

    def test_resolves_relative_llvm_src_root_from_site_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "work"
            build_root = work / "llvm-build-sancov"
            llvm_src = work / "llvm-project" / "llvm"
            llvm_lit = build_root / "bin" / "llvm-lit"
            site_cfg = build_root / "test" / "lit.site.cfg.py"
            site_cfg.parent.mkdir(parents=True)
            llvm_lit.parent.mkdir(parents=True)
            site_cfg.write_text(
                'config.llvm_src_root = path(r"../../llvm-project/llvm")\n',
                encoding="utf-8",
            )

            path_in_suite = "CodeGen/AMDGPU/example.ll"
            test_path = llvm_src / "test" / path_in_suite
            test_path.parent.mkdir(parents=True)
            test_path.write_text("; lit test\n", encoding="utf-8")

            self.assertEqual(
                llvm_test_source_root(llvm_lit),
                (llvm_src / "test").resolve(),
            )
            self.assertEqual(
                filter_existing_lit_priority_tests(llvm_lit, (path_in_suite,)),
                (path_in_suite,),
            )

    def test_preserves_unrelated_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp) / "build"
            llvm_lit = build_root / "bin" / "llvm-lit"
            times_path = lit_test_times_path(llvm_lit)
            times_path.parent.mkdir(parents=True)
            _write_lit_test_times(times_path, {"other.txt": 42.0})

            seed_lit_priority_test_times(llvm_lit, BASELINE_LIT_PRIORITY_TESTS)

            times = _read_lit_test_times(times_path)
            self.assertEqual(times["other.txt"], 42.0)

    def test_boosts_low_existing_priority_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp) / "build"
            llvm_lit = build_root / "bin" / "llvm-lit"
            times_path = lit_test_times_path(llvm_lit)
            times_path.parent.mkdir(parents=True)
            priority = BASELINE_LIT_PRIORITY_TESTS[0]
            _write_lit_test_times(times_path, {priority: 1.0})

            seed_lit_priority_test_times(llvm_lit, (priority,))

            times = _read_lit_test_times(times_path)
            self.assertEqual(times[priority], BASELINE_LIT_PRIORITY_ELAPSED)

    def test_keeps_higher_existing_priority_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_root = Path(tmp) / "build"
            llvm_lit = build_root / "bin" / "llvm-lit"
            times_path = lit_test_times_path(llvm_lit)
            times_path.parent.mkdir(parents=True)
            priority = BASELINE_LIT_PRIORITY_TESTS[0]
            existing = BASELINE_LIT_PRIORITY_ELAPSED * 2
            _write_lit_test_times(times_path, {priority: existing})

            seed_lit_priority_test_times(llvm_lit, (priority,))

            times = _read_lit_test_times(times_path)
            self.assertEqual(times[priority], existing)


if __name__ == "__main__":
    unittest.main()
