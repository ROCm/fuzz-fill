from __future__ import annotations

import shlex
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from reduce.reducer import ReduceContext
from reduce.test import Test


def tmp_pass_path(tmp_dir: Path, step: int, slug: str) -> Path:
    """``tmp_dir / "00_snapshot.ll"``-style names, ordered by pipeline index."""
    return tmp_dir / f"{step:02d}_{slug}.ll"


def tmp_pass_path_mir(tmp_dir: Path, step: int, slug: str) -> Path:
    """Same as ``tmp_pass_path`` but ``.mir`` for ``llvm-reduce -x=mir`` output."""
    return tmp_dir / f"{step:02d}_{slug}.mir"


@dataclass(frozen=True)
class _ExtractMirLlcOptions:
    """Validated fields from ``ReduceContext`` for ``extract_mir_before_pass``."""

    pass_under_test: str
    mtriple: str
    llc_O: str


def _require_tool(llvm_bin: Path, exe_name: str) -> Path:
    exe = llvm_bin / exe_name
    if not exe.is_file():
        raise SystemExit(f"{exe_name} not found: {exe}")
    return exe


def _llc_opt_argv(llc_O: str) -> list[str]:
    """Split config ``llc_O`` into ``llc`` argv tokens; empty / whitespace → no extra args."""
    s = llc_O.strip()
    return shlex.split(s) if s else []


def _require_interesting_script(test: Test) -> None:
    if test.interesting is None:
        raise SystemExit('llvm-reduce requires an "interesting" script in the config.')


def _require_interesting_mir_script(ctx: ReduceContext) -> Path:
    if ctx.interesting_mir is None:
        raise SystemExit(
            'llvm_reduce_mir requires "interesting_mir" in the config (path to an executable script).'
        )
    return ctx.interesting_mir


def _require_extract_mir_context(ctx: ReduceContext) -> _ExtractMirLlcOptions:
    if ctx.pass_under_test is None:
        raise SystemExit(
            'extract_mir_before_pass requires "pass_under_test" in the config (LLVM pass id, '
            'e.g. "si-i1-copies").'
        )
    if ctx.mtriple is None:
        raise SystemExit(
            'extract_mir_before_pass requires "mtriple" in the config (e.g. "amdgcn-amd-amdhsa").'
        )
    if ctx.llc_O is None:
        raise SystemExit(
            'extract_mir_before_pass requires "llc_O" in the config (e.g. "-O1", or "" to omit -O).'
        )
    return _ExtractMirLlcOptions(
        pass_under_test=ctx.pass_under_test,
        mtriple=ctx.mtriple,
        llc_O=ctx.llc_O,
    )


class ReducePass(ABC):
    """One step in the pipeline; returns the test state for the next pass."""

    @abstractmethod
    def run(self, ctx: ReduceContext, test: Test, *, step: int) -> Test:
        raise NotImplementedError


class SnapshotPass(ReducePass):
    """Copy the current IR into ``ctx.tmp_dir`` (baseline for later passes)."""

    def run(self, ctx: ReduceContext, test: Test, *, step: int) -> Test:
        dest = tmp_pass_path(ctx.tmp_dir, step, "snapshot")
        shutil.copy2(test.test_path, dest)
        return Test(dest, test.interesting, test.file, test.line)


class LlvmReduceIrPass(ReducePass):
    """Run ``llvm-reduce`` (IR) with the config interesting-ness script."""

    def run(self, ctx: ReduceContext, test: Test, *, step: int) -> Test:
        _require_interesting_script(test)
        exe = _require_tool(ctx.llvm_bin, "llvm-reduce")
        out = tmp_pass_path(ctx.tmp_dir, step, "llvmreduce")
        cmd = [
            str(exe),
            f"--test={test.interesting.resolve()}",
            f"-o={out}",
            str(test.test_path.resolve()),
        ]
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=ctx.tmp_dir,
        )
        if r.returncode != 0:
            msg = (r.stderr or r.stdout or "").strip() or "(no output)"
            raise SystemExit(f"llvm-reduce failed ({r.returncode}):\n{msg}")
        if not out.is_file():
            raise SystemExit(f"llvm-reduce did not write expected output: {out}")
        return Test(out, test.interesting, test.file, test.line)


class LlvmReduceMirPass(ReducePass):
    """Run ``llvm-reduce -x=mir`` with ``--test=<interesting_mir>``."""

    def run(self, ctx: ReduceContext, test: Test, *, step: int) -> Test:
        interesting_mir = _require_interesting_mir_script(ctx)
        exe = _require_tool(ctx.llvm_bin, "llvm-reduce")
        out = tmp_pass_path_mir(ctx.tmp_dir, step, "llvmreduce_mir")
        cmd = [
            str(exe),
            "-x=mir",
            f"--test={interesting_mir.resolve()}",
            f"-o={out}",
            str(test.test_path.resolve()),
        ]
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=ctx.tmp_dir,
        )
        if r.returncode != 0:
            msg = (r.stderr or r.stdout or "").strip() or "(no output)"
            raise SystemExit(f"llvm-reduce (-x=mir) failed ({r.returncode}):\n{msg}")
        if not out.is_file():
            raise SystemExit(f"llvm-reduce (-x=mir) did not write expected output: {out}")
        return Test(out, test.interesting, test.file, test.line)


class ExtractMirBeforePass(ReducePass):
    """Run ``llc`` with ``-stop-before=<pass_under_test> -simplify-mir`` and write MIR to ``-o``."""

    def run(self, ctx: ReduceContext, test: Test, *, step: int) -> Test:
        llc_opts = _require_extract_mir_context(ctx)

        if ctx.extract_mir_output:
            name = Path(ctx.extract_mir_output).name
            dest = ctx.tmp_dir / f"{step:02d}_{name}"
        else:
            dest = ctx.tmp_dir / f"{step:02d}_mir_before_pass.mir"

        exe = _require_tool(ctx.llvm_bin, "llc")

        cmd = [
            str(exe),
            "-o",
            str(dest.resolve()),
            *_llc_opt_argv(llc_opts.llc_O),
            f"-mtriple={llc_opts.mtriple}",
            f"-stop-before={llc_opts.pass_under_test}",
            "-simplify-mir",
            str(test.test_path.resolve()),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=ctx.tmp_dir)
        if r.returncode != 0:
            msg = (r.stderr or r.stdout or "").strip() or "(no output)"
            raise SystemExit(f"llc (extract MIR) failed ({r.returncode}):\n{msg}")
        if not dest.is_file():
            raise SystemExit(f"llc did not write expected MIR output: {dest}")
        return Test(dest, test.interesting, test.file, test.line)


class ExtractIrAfterPass(ReducePass):
    """Placeholder: extract IR after the pass under test (not implemented yet)."""

    def run(self, ctx: ReduceContext, test: Test, *, step: int) -> Test:
        return test
