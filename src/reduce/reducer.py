from __future__ import annotations

import shlex
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from reduce.test import Test


def tmp_pass_path(tmp_dir: Path, step: int, slug: str) -> Path:
    """``tmp_dir / "00_snapshot.ll"``-style names, ordered by pipeline index."""
    return tmp_dir / f"{step:02d}_{slug}.ll"


@dataclass(frozen=True)
class ReduceContext:
    """Per-run context. Passes read/write intermediates under ``tmp_dir`` only."""

    llvm_bin: Path
    output_dir: Path
    tmp_dir: Path
    pass_under_test: str | None
    mtriple: str | None
    llc_O: str | None
    extract_mir_output: str | None


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


class LlvmReduceMirPlaceholderPass(ReducePass):
    """TODO: ``llvm-reduce -x=mir`` with the same ``--test`` pattern as IR."""

    def run(self, ctx: ReduceContext, test: Test, *, step: int) -> Test:
        dest = tmp_pass_path(ctx.tmp_dir, step, "llvmreduce_mir")
        shutil.copy2(test.test_path, dest)
        return Test(dest, test.interesting, test.file, test.line)


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


# Registry of pass ids for config ``pipeline`` arrays (order = run order; repeats allowed).
_PASS_BY_ID: dict[str, type[ReducePass]] = {
    "snapshot": SnapshotPass,
    "llvm_reduce_ir": LlvmReduceIrPass,
    "llvm_reduce_mir": LlvmReduceMirPlaceholderPass,
    "extract_mir_before_pass": ExtractMirBeforePass,
}


def known_pass_ids() -> frozenset[str]:
    """Ids valid in JSON ``pipeline`` and ``--only-pass``."""
    return frozenset(_PASS_BY_ID)


def passes_from_ids(pass_ids: list[str]) -> list[ReducePass]:
    out: list[ReducePass] = []
    for pid in pass_ids:
        cls = _PASS_BY_ID.get(pid)
        if cls is None:
            known = ", ".join(sorted(_PASS_BY_ID))
            raise SystemExit(f"Unknown pass id {pid!r}. Known ids: {known}")
        out.append(cls())
    return out


class Reducer:
    def __init__(
        self,
        llvm_bin: Path,
        output_dir: Path,
        test: Test,
        *,
        pass_ids: list[str],
        pass_under_test: str | None = None,
        mtriple: str | None = None,
        llc_O: str | None = None,
        extract_mir_output: str | None = None,
    ):
        self.llvm_bin: Path = llvm_bin
        self.output_dir: Path = output_dir
        self.test: Test = test
        self._pass_under_test: str | None = pass_under_test
        self._mtriple: str | None = mtriple
        self._llc_O: str | None = llc_O
        self._extract_mir_output: str | None = extract_mir_output
        self._pass_ids: list[str] = list(pass_ids)
        self._passes_list: list[ReducePass] = passes_from_ids(pass_ids)

    def reduce(self) -> Test:
        tmp_dir = self.output_dir / "tmp"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        ctx = ReduceContext(
            llvm_bin=self.llvm_bin,
            output_dir=self.output_dir,
            tmp_dir=tmp_dir,
            pass_under_test=self._pass_under_test,
            mtriple=self._mtriple,
            llc_O=self._llc_O,
            extract_mir_output=self._extract_mir_output,
        )
        test = self.test
        n = len(self._passes_list)
        for step, (pass_id, p) in enumerate(zip(self._pass_ids, self._passes_list)):
            print(f"[reduce] pass {step + 1}/{n}: {pass_id}", flush=True)
            test = p.run(ctx, test, step=step)

        suffix = test.test_path.suffix if test.test_path.suffix else ".ll"
        final_name = "reduced.ll" if suffix == ".ll" else f"reduced{suffix}"
        final_path = self.output_dir / final_name
        shutil.copy2(test.test_path, final_path)
        print(f"[reduce] wrote {final_path}", flush=True)
        return Test(final_path, test.interesting, test.file, test.line)
