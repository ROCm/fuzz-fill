"""Aggregation skips lit ``%t`` copies and still fails on other missing binaries."""

from __future__ import annotations

import io
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from coverage.constants import (
    DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
    SYMBOLIZE_MEMORY_BYTES,
)
from coverage.filepaths import Filepaths
from coverage.sancov import Sancov, _quote_rsp_path
from coverage.test_runner import (
    TestRunner,
    _merge_and_symbolize_sancovs,
    _resolve_symbolize_target,
    available_memory_bytes,
    global_chunk_size,
    split_into_chunks,
    symbolize_worker_count,
    tool_chunk_count,
)


def _runner(root: Path) -> TestRunner:
    bin_dir = root / "build-sancov" / "bin"
    bin_dir.mkdir(parents=True)
    llc = bin_dir / "llc"
    llc.write_text("", encoding="utf-8")
    output = root / "out"
    output.mkdir()
    return TestRunner(
        mode="lit",
        filepaths=Filepaths(
            output_dir=output,
            sancov=bin_dir / "sancov",
            llc=llc,
            line_coverage_summary_file=DEFAULT_LINE_COVERAGE_SUMMARY_FILE,
        ),
        lit_suites=["llvm/test"],
    )


def _dump(raw: Path, name: str) -> None:
    raw.mkdir(parents=True, exist_ok=True)
    (raw / name).write_bytes(b"")


class AggregateLitTemporaryCoverageTest(unittest.TestCase):
    def test_skips_lit_temporary_and_symbolizes_real_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(Path(tmp))
            raw = runner.raw_sancov_output_dir
            _dump(raw, "llc.42.sancov")
            _dump(raw, "exec-options.ll.tmp.bin--.7.sancov")
            _dump(raw, "execname-options.ll.tmp.bin--gisel.8.sancov")
            seen: list[str] = []

            def record(
                sancovs: list[Sancov],
                dumps_by_tool: dict[str, list[str]],
                workers: int,
            ) -> None:
                del dumps_by_tool, workers
                for sancov in sancovs:
                    seen.append(sancov.suffix or "")
                    sancov.get_merged_symcov_path().write_text("{}", encoding="utf-8")

            covered = pd.DataFrame(
                [{"file": "a.cpp", "line": 1, "point": "0x1", "covered": 0}]
            )
            stdout = io.StringIO()
            with (
                patch("coverage.test_runner._merge_and_symbolize_sancovs", record),
                patch.object(
                    Sancov, "load_coverage_dfs", return_value=[covered]
                ),
                redirect_stdout(stdout),
            ):
                runner.get_aggregate_coverage()

            self.assertEqual(seen, ["llc"])
            text = stdout.getvalue()
            self.assertIn("exec-options.ll.tmp.bin--", text)
            self.assertIn("execname-options.ll.tmp.bin--gisel", text)
            output = runner.filepaths.output_dir
            self.assertTrue((output / "llc_address_line_map.csv").is_file())
            self.assertFalse(
                (output / "exec-options.ll.tmp.bin--_address_line_map.csv").exists()
            )

    def test_ignores_release_utility_sancovs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(Path(tmp))
            raw = runner.raw_sancov_output_dir
            _dump(raw, "llc.42.sancov")
            for name in (
                "sancov.1.sancov",
                "FileCheck.2.sancov",
                "not.3.sancov",
                "count.4.sancov",
                "split-file.5.sancov",
            ):
                _dump(raw, name)
            seen: list[str] = []

            def record(
                sancovs: list[Sancov],
                dumps_by_tool: dict[str, list[str]],
                workers: int,
            ) -> None:
                del dumps_by_tool, workers
                for sancov in sancovs:
                    seen.append(sancov.suffix or "")
                    sancov.get_merged_symcov_path().write_text("{}", encoding="utf-8")

            covered = pd.DataFrame(
                [{"file": "a.cpp", "line": 1, "point": "0x1", "covered": 0}]
            )
            stdout = io.StringIO()
            with (
                patch("coverage.test_runner._merge_and_symbolize_sancovs", record),
                patch.object(
                    Sancov, "load_coverage_dfs", return_value=[covered]
                ),
                redirect_stdout(stdout),
            ):
                runner.get_aggregate_coverage()

            self.assertEqual(seen, ["llc"])
            text = stdout.getvalue()
            for tool in ("sancov", "FileCheck", "not", "count", "split-file"):
                self.assertIn(tool, text)
            output = runner.filepaths.output_dir
            self.assertTrue((output / "llc_address_line_map.csv").is_file())
            self.assertFalse((output / "FileCheck_address_line_map.csv").exists())
            self.assertFalse((output / "not_address_line_map.csv").exists())

    def test_release_utility_dumps_alone_are_not_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(Path(tmp))
            raw = runner.raw_sancov_output_dir
            _dump(raw, "FileCheck.2.sancov")
            _dump(raw, "count.4.sancov")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as ctx:
                    runner.get_aggregate_coverage()
            self.assertIn("no sancov files", str(ctx.exception))
            self.assertIn("FileCheck", stdout.getvalue())

    def test_missing_real_binary_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(Path(tmp))
            raw = runner.raw_sancov_output_dir
            _dump(raw, "exec-options.ll.tmp.bin--.7.sancov")
            _dump(raw, "not-a-real-tool.9.sancov")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as ctx:
                    runner.get_aggregate_coverage()
            message = str(ctx.exception)
            self.assertIn("not-a-real-tool", message)
            self.assertNotIn("exec-options.ll.tmp.bin--", message)
            self.assertIn("exec-options.ll.tmp.bin--", stdout.getvalue())

    def test_resolves_clang_unittest_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / "build-sancov" / "bin"
            bin_dir.mkdir(parents=True)
            clang_ut = (
                root / "build-sancov" / "tools" / "clang" / "unittests" / "AllClangUnitTests"
            )
            clang_ut.parent.mkdir(parents=True)
            clang_ut.write_text("", encoding="utf-8")
            clang_ut.chmod(0o755)
            resolved = _resolve_symbolize_target(
                bin_dir, root / "build-sancov", "AllClangUnitTests"
            )
            self.assertEqual(resolved, clang_ut)


class ChunkSplitTest(unittest.TestCase):
    def test_splits_nearly_equal_contiguous_chunks(self) -> None:
        items = [Path(f"f{i}.sancov") for i in range(10)]
        chunks = split_into_chunks(items, 3)
        self.assertEqual(len(chunks), 3)
        self.assertEqual([len(c) for c in chunks], [4, 3, 3])
        self.assertEqual([p for c in chunks for p in c], items)

    def test_caps_chunks_at_file_count(self) -> None:
        items = [Path("a.sancov"), Path("b.sancov")]
        chunks = split_into_chunks(items, 8)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], [items[0]])
        self.assertEqual(chunks[1], [items[1]])

    def test_empty_input(self) -> None:
        self.assertEqual(split_into_chunks([], 4), [])


class GlobalChunkSizeTest(unittest.TestCase):
    def test_small_tools_skip_round1(self) -> None:
        # tools of 1000, 10, 3 files with 4 workers:
        # chunk_size = ceil(1013 / 4) = 254
        # only the 1000-file tool is split (ceil(1000/254)=4); others fit in one.
        sizes = [1000, 10, 3]
        workers = 4
        chunk_size = global_chunk_size(sum(sizes), workers)
        self.assertEqual(chunk_size, 254)
        self.assertEqual(tool_chunk_count(1000, chunk_size), 4)
        self.assertEqual(tool_chunk_count(10, chunk_size), 1)
        self.assertEqual(tool_chunk_count(3, chunk_size), 1)


GIB = 1024**3


def _write_meminfo(root: Path, available_bytes: int) -> Path:
    path = root / "meminfo"
    path.write_text(
        "MemTotal:       999999999 kB\n"
        f"MemAvailable:   {available_bytes // 1024} kB\n",
        encoding="utf-8",
    )
    return path


def _write_cgroup(root: Path, limit: str, current: int, file_cache: int) -> Path:
    cgroup = root / "cgroup"
    cgroup.mkdir()
    (cgroup / "memory.max").write_text(f"{limit}\n", encoding="utf-8")
    (cgroup / "memory.current").write_text(f"{current}\n", encoding="utf-8")
    (cgroup / "memory.stat").write_text(
        f"anon {current - file_cache}\nfile {file_cache}\n", encoding="utf-8"
    )
    return cgroup


class AvailableMemoryBytesTest(unittest.TestCase):
    def test_no_cgroup_uses_mem_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meminfo = _write_meminfo(root, 100 * GIB)
            self.assertEqual(
                available_memory_bytes(meminfo, root / "missing"), 100 * GIB
            )

    def test_unlimited_cgroup_uses_mem_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meminfo = _write_meminfo(root, 100 * GIB)
            cgroup = _write_cgroup(root, "max", 90 * GIB, 0)
            self.assertEqual(available_memory_bytes(meminfo, cgroup), 100 * GIB)

    def test_cgroup_limit_ignores_page_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meminfo = _write_meminfo(root, 100 * GIB)
            # 40 GiB used, 30 GiB of it page cache: 10 GiB charged, 22 GiB free.
            cgroup = _write_cgroup(root, str(32 * GIB), 40 * GIB, 30 * GIB)
            self.assertEqual(available_memory_bytes(meminfo, cgroup), 22 * GIB)

    def test_host_smaller_than_cgroup_headroom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meminfo = _write_meminfo(root, 5 * GIB)
            cgroup = _write_cgroup(root, str(64 * GIB), 0, 0)
            self.assertEqual(available_memory_bytes(meminfo, cgroup), 5 * GIB)


class SymbolizeWorkerCountTest(unittest.TestCase):
    def test_under_one_budget_yields_one(self) -> None:
        self.assertEqual(
            symbolize_worker_count(
                workers=64,
                tool_count=10,
                available_bytes=SYMBOLIZE_MEMORY_BYTES - 1,
            ),
            1,
        )

    def test_32_gib_yields_four(self) -> None:
        self.assertEqual(
            symbolize_worker_count(
                workers=64,
                tool_count=10,
                available_bytes=32 * 1024**3,
            ),
            4,
        )

    def test_capped_by_jobs_and_tools(self) -> None:
        self.assertEqual(
            symbolize_worker_count(
                workers=2,
                tool_count=10,
                available_bytes=64 * 1024**3,
            ),
            2,
        )
        self.assertEqual(
            symbolize_worker_count(
                workers=64,
                tool_count=3,
                available_bytes=64 * 1024**3,
            ),
            3,
        )


class UnionFilesResponseFileTest(unittest.TestCase):
    def test_single_file_copies_without_sancov(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "a.sancov"
            src.write_bytes(b"raw")
            out = root / "out.sancov"
            sancov = Sancov(root / "sancov")
            with patch("coverage.sancov.run_subprocess") as run:
                sancov.union_files([src], out)
            run.assert_not_called()
            self.assertEqual(out.read_bytes(), b"raw")

    def test_multi_file_uses_quoted_response_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.sancov"
            b = root / "b.sancov"
            a.write_bytes(b"a")
            b.write_bytes(b"b")
            out = root / "out.sancov"
            sancov_bin = root / "sancov"
            sancov = Sancov(sancov_bin)
            captured: dict[str, object] = {}

            def fake_run(logger, cmd, **kwargs):
                del logger, kwargs
                captured["cmd"] = list(cmd)
                rsp = Path(str(cmd[2])[1:])
                captured["rsp_text"] = rsp.read_text(encoding="utf-8")
                out.write_bytes(b"merged")
                return MagicMock(returncode=0)

            with patch("coverage.sancov.run_subprocess", side_effect=fake_run):
                sancov.union_files([a, b], out)

            cmd = captured["cmd"]
            assert isinstance(cmd, list)
            self.assertEqual(cmd[0], str(sancov_bin))
            self.assertEqual(cmd[1], "-union")
            self.assertTrue(str(cmd[2]).startswith("@"))
            self.assertEqual(cmd[3], "--output")
            self.assertEqual(cmd[4], str(out))
            self.assertEqual(
                captured["rsp_text"],
                f"{_quote_rsp_path(str(a))}\n{_quote_rsp_path(str(b))}\n",
            )
            self.assertEqual(out.read_bytes(), b"merged")

    def test_quotes_paths_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spaced = root / "dir with space"
            spaced.mkdir()
            a = spaced / "a.sancov"
            b = spaced / 'b"quote.sancov'
            a.write_bytes(b"a")
            b.write_bytes(b"b")
            out = root / "out.sancov"
            sancov = Sancov(root / "sancov")
            captured: dict[str, object] = {}

            def fake_run(logger, cmd, **kwargs):
                del logger, kwargs
                rsp = Path(str(cmd[2])[1:])
                captured["rsp_text"] = rsp.read_text(encoding="utf-8")
                out.write_bytes(b"merged")
                return MagicMock(returncode=0)

            with patch("coverage.sancov.run_subprocess", side_effect=fake_run):
                sancov.union_files([a, b], out)

            text = str(captured["rsp_text"])
            self.assertIn(_quote_rsp_path(str(a)), text)
            self.assertIn(_quote_rsp_path(str(b)), text)
            self.assertTrue(text.startswith('"'))
            # Plain path round-trips through quoting.
            plain = "/tmp/plain.sancov"
            self.assertEqual(_quote_rsp_path(plain), f'"{plain}"')


class TwoStageMergeOrderTest(unittest.TestCase):
    def test_chunk_unions_finish_before_reduce_and_symbolize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw_sancov"
            raw.mkdir()
            # Force round-1 chunks for llc: many files, few workers.
            for i in range(8):
                (raw / f"llc.{i}.sancov").write_bytes(b"x")
            for i in range(2):
                (raw / f"opt.{i}.sancov").write_bytes(b"y")

            dumps = Sancov.group_raw_dumps(raw)
            events: list[str] = []
            lock = threading.Lock()
            opt_symbolized = threading.Event()

            def fake_union(
                self: Sancov, inputs: list[str | Path], output: Path
            ) -> None:
                del inputs
                tool = self.suffix or ""
                kind = "chunk" if "chunk" in output.name else "reduce"
                with lock:
                    events.append(f"union:{kind}:{tool}")
                if kind == "reduce" and tool == "llc":
                    # Hold llc's reduce until opt has symbolized.
                    if not opt_symbolized.wait(timeout=5):
                        raise AssertionError("opt did not symbolize while llc reduced")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"u")

            def fake_symbolize(
                self: Sancov, sancov_path: Path, symcov_path: Path
            ) -> None:
                del sancov_path
                tool = self.suffix or ""
                with lock:
                    events.append(f"symbolize:{tool}")
                if tool == "opt":
                    opt_symbolized.set()
                symcov_path.write_text("{}", encoding="utf-8")

            llc = Sancov(root / "sancov", root / "llc", raw, "llc")
            opt = Sancov(root / "sancov", root / "opt", raw, "opt")
            with (
                patch.object(Sancov, "union_files", fake_union),
                patch.object(Sancov, "symbolize", fake_symbolize),
                patch(
                    "coverage.test_runner.symbolize_worker_count",
                    return_value=2,
                ),
                patch(
                    "coverage.test_runner.available_memory_bytes",
                    return_value=32 * 1024**3,
                ),
            ):
                # workers=2 => chunk_size=ceil(10/2)=5; llc(8) splits, opt(2) skips
                _merge_and_symbolize_sancovs([llc, opt], dumps, workers=2)

            chunk_idxs = [
                i for i, e in enumerate(events) if e.startswith("union:chunk:")
            ]
            reduce_idxs = [
                i for i, e in enumerate(events) if e.startswith("union:reduce:")
            ]
            symbolize_idxs = [
                i for i, e in enumerate(events) if e.startswith("symbolize:")
            ]
            self.assertTrue(chunk_idxs)
            self.assertTrue(reduce_idxs)
            self.assertTrue(symbolize_idxs)
            self.assertLess(max(chunk_idxs), min(reduce_idxs))
            # Only llc has round-1 chunks; opt goes straight to round 2.
            self.assertTrue(all(e.endswith(":llc") for e in events if e.startswith("union:chunk:")))
            self.assertIn("symbolize:opt", events)
            self.assertIn("symbolize:llc", events)
            self.assertTrue(opt_symbolized.is_set())

    def test_small_tools_union_raw_dumps_in_round2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw_sancov"
            raw.mkdir()
            for i in range(1000):
                (raw / f"llc.{i}.sancov").write_bytes(b"x")
            for i in range(10):
                (raw / f"opt.{i}.sancov").write_bytes(b"y")
            for i in range(3):
                (raw / f"llvm-mc.{i}.sancov").write_bytes(b"z")

            dumps = Sancov.group_raw_dumps(raw)
            round1_tools: set[str] = set()
            round2_inputs: dict[str, list[str]] = {}

            def fake_union(
                self: Sancov, inputs: list[str | Path], output: Path
            ) -> None:
                tool = self.suffix or ""
                if "chunk" in output.name:
                    round1_tools.add(tool)
                else:
                    round2_inputs[tool] = [str(p) for p in inputs]
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"u")

            def fake_symbolize(
                self: Sancov, sancov_path: Path, symcov_path: Path
            ) -> None:
                del sancov_path
                symcov_path.write_text("{}", encoding="utf-8")

            tools = ["llc", "llvm-mc", "opt"]
            sancovs = [
                Sancov(root / "sancov", root / t, raw, t) for t in tools
            ]
            with (
                patch.object(Sancov, "union_files", fake_union),
                patch.object(Sancov, "symbolize", fake_symbolize),
                patch(
                    "coverage.test_runner.symbolize_worker_count",
                    return_value=3,
                ),
                patch(
                    "coverage.test_runner.available_memory_bytes",
                    return_value=64 * 1024**3,
                ),
            ):
                _merge_and_symbolize_sancovs(sancovs, dumps, workers=4)

            self.assertEqual(round1_tools, {"llc"})
            self.assertEqual(round2_inputs["opt"], dumps["opt"])
            self.assertEqual(round2_inputs["llvm-mc"], dumps["llvm-mc"])
            # llc round 2 receives partials, not the raw dumps.
            self.assertNotEqual(round2_inputs["llc"], dumps["llc"])
            self.assertTrue(
                all("chunk" in Path(p).name for p in round2_inputs["llc"])
            )
