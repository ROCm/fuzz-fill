from __future__ import annotations

import os
import re
import shlex
import shutil
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from reduce.reducer import ReduceContext
from reduce.test import Test
from fuzz_fill.log import get_logger, run_subprocess

logger = get_logger("reduce.pass")


def tmp_pass_path(tmp_dir: Path, step: int, slug: str, ext: str = "ll") -> Path:
    """``tmp_dir / "00_snapshot.ll"``-style names, ordered by pipeline index."""
    return tmp_dir / f"{step:02d}_{slug}.{ext}"


def tmp_pass_path_mir(tmp_dir: Path, step: int, slug: str) -> Path:
    """Same as ``tmp_pass_path`` but ``.mir`` for ``llvm-reduce -x=mir`` output."""
    return tmp_dir / f"{step:02d}_{slug}.mir"


def tmp_pass_path_for_input(tmp_dir: Path, step: int, slug: str, input_path: Path) -> Path:
    """``NN_<slug>.<ext>`` where ``<ext>`` matches ``input_path`` (``".ll"`` if it has no suffix)."""
    suf = input_path.suffix.lower() or ".ll"
    return tmp_dir / f"{step:02d}_{slug}{suf}"


@dataclass(frozen=True)
class _ExtractMirLlcOptions:
    """Validated fields from ``ReduceContext`` for ``extract_*_before_pass`` llc invocations."""

    pass_under_test: str
    mtriple: str
    llc_O: str


def _require_llvm_dis(ctx: ReduceContext) -> Path:
    if ctx.llvm_dis is None:
        raise SystemExit(
            "--llvm-dis is required when reducing .bc input with llvm_reduce_ir "
            "(or set FUZZ_FILL_LLVM_DIS)."
        )
    return ctx.llvm_dis


def _llc_opt_argv(llc_O: str) -> list[str]:
    """Split config ``llc_O`` into ``llc`` argv tokens; empty / whitespace → no extra args."""
    s = llc_O.strip()
    return shlex.split(s) if s else []


def _interesting_script_for_llvm_reduce_ir(ctx: ReduceContext) -> Path:
    v = ctx.pass_options.get("interesting")
    if v is not None:
        if isinstance(v, Path):
            return v
        if isinstance(v, str):
            return Path(v)
        raise SystemExit(
            f'llvm_reduce_ir / creduce: "interesting" must be a path or string, got {type(v).__name__}.'
        )
    raise SystemExit(
        'llvm_reduce_ir and creduce require "interesting" in this step\'s "parameters" '
        "(path to the interesting script for llvm-reduce --test or creduce; creduce copies "
        'the script and replaces every literal \'"$1"\' with the shell-quoted candidate '
        "basename only, for use when the test runs in creduce’s temp directory)."
    )


def _creduce_n_cores(ctx: ReduceContext) -> int:
    """C-Reduce ``--n``: explicit ``parameters.n``, else half of ``os.cpu_count()`` (at least 1)."""
    v = ctx.pass_options.get("n")
    if v is not None:
        if isinstance(v, bool):
            raise SystemExit('creduce: "n" must be a positive integer, not a boolean.')
        if isinstance(v, int):
            if v < 1:
                raise SystemExit(f'creduce: "n" must be >= 1, got {v}.')
            return v
        raise SystemExit(
            f'creduce: "n" must be a positive integer, got {type(v).__name__}.'
        )
    cpu = os.cpu_count()
    if cpu is None or cpu < 1:
        return 1
    return max(1, cpu // 2)


def _creduce_interesting_copy_with_candidate(
    src: Path,
    dst: Path,
    candidate: Path,
) -> None:
    """Copy ``src`` to ``dst``, embedding the candidate basename by replacing each ``\"$1\"``."""
    raw = src.read_text(encoding="utf-8", errors="replace")
    if '"$1"' not in raw:
        raise SystemExit(
            "creduce: the interesting script must contain the literal token "
            '\'"$1"\' where the candidate file name should appear (one or more times); '
            f"none found in {src}."
        )
    quoted = shlex.quote(candidate.name)
    dst.write_text(raw.replace('"$1"', quoted), encoding="utf-8")
    shutil.copymode(src, dst)


def _require_interesting_mir_script(ctx: ReduceContext) -> Path:
    v = ctx.pass_options.get("interesting_mir")
    if v is None:
        raise SystemExit(
            'llvm_reduce_mir requires "interesting_mir" on this pipeline step '
            "(path to an executable script)."
        )
    if isinstance(v, Path):
        return v
    if isinstance(v, str):
        return Path(v)
    raise SystemExit(
        f'llvm_reduce_mir: "interesting_mir" must be a path, got {type(v).__name__}.'
    )


def _require_extract_mir_context(ctx: ReduceContext) -> _ExtractMirLlcOptions:
    _pass = "extract_mir_before_pass and extract_ir_before_pass"
    put = ctx.pass_options.get("pass_under_test")
    if put is None:
        raise SystemExit(
            f'{_pass} require "pass_under_test" on this pipeline step (LLVM pass id, '
            'e.g. "si-i1-copies").'
        )
    if not isinstance(put, str):
        raise SystemExit(f'{_pass}: "pass_under_test" must be a string.')
    mt = ctx.pass_options.get("mtriple")
    if mt is None:
        raise SystemExit(
            f'{_pass} require "mtriple" on this pipeline step (e.g. "amdgcn-amd-amdhsa").'
        )
    if not isinstance(mt, str):
        raise SystemExit(f'{_pass}: "mtriple" must be a string.')
    llc_O = ctx.pass_options.get("llc_O")
    if llc_O is None:
        raise SystemExit(
            f'{_pass} require "llc_O" on this pipeline step (e.g. "-O1", or "" to omit -O).'
        )
    if not isinstance(llc_O, str):
        raise SystemExit(f'{_pass}: "llc_O" must be a string.')
    return _ExtractMirLlcOptions(
        pass_under_test=put,
        mtriple=mt,
        llc_O=llc_O,
    )


def _llc_stop_before_args(pass_under_test: str, *, simplify_mir: bool) -> list[str]:
    """Argv fragment after ``-mtriple`` for ``llc`` stop-before extraction (optional ``-simplify-mir``)."""
    out = [f"-stop-before={pass_under_test}"]
    if simplify_mir:
        out.append("-simplify-mir")
    return out


def _run_llc_extract_core(
    ctx: ReduceContext,
    test: Test,
    llc_opts: _ExtractMirLlcOptions,
    *,
    dest: Path,
    what: str,
    pass_specific_args: Sequence[str],
) -> Test:
    exe = ctx.llc
    cmd = [
        str(exe),
        "-o",
        str(dest.resolve()),
        *_llc_opt_argv(llc_opts.llc_O),
        f"-mtriple={llc_opts.mtriple}",
        *pass_specific_args,
        str(test.test_path.resolve()),
    ]
    r = run_subprocess(
        logger,
        cmd,
        label=f"llc ({what})",
        capture_output=True,
        text=True,
        cwd=ctx.tmp_dir,
    )
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or "").strip() or "(no output)"
        raise SystemExit(f"llc ({what}) failed ({r.returncode}):\n{msg}")
    if not dest.is_file():
        raise SystemExit(f"llc did not write expected output ({what}): {dest}")
    return Test(dest, test.interesting, test.file, test.line)


_PIPE_ONLY_LINE = re.compile(r"^\s*\|\s*$")


def _min_leading_space_count(lines: list[str]) -> int:
    """Smallest leading space run among non-blank lines that start with a space (LLVM print-before style)."""
    m: int | None = None
    for ln in lines:
        if not ln.strip() or not ln.startswith(" "):
            continue
        n = len(ln) - len(ln.lstrip(" "))
        if m is None or n < m:
            m = n
    return m if m is not None else 0


def _dedent_leading_spaces(lines: list[str], m: int) -> list[str]:
    """Remove up to ``m`` leading spaces from space-indented lines; blank lines become ``\"\"``."""
    if m <= 0:
        return list(lines)
    out: list[str] = []
    for ln in lines:
        if not ln.strip():
            out.append("")
            continue
        if not ln.startswith(" "):
            out.append(ln)
            continue
        i = 0
        while i < m and i < len(ln) and ln[i] == " ":
            i += 1
        out.append(ln[i:])
    return out


def _normalize_extract_ir_ll_text(s: str) -> str:
    """Normalize ``llc`` print-before dump: drop pipe column lines, dedent common space indent, strip trailing ``...``."""
    lines = s.splitlines()
    while lines and _PIPE_ONLY_LINE.match(lines[0]):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    m = _min_leading_space_count(lines)
    lines = _dedent_leading_spaces(lines, m)
    if lines:
        last = lines[-1].rstrip()
        if last.endswith("..."):
            last = last[:-3].rstrip()
        lines[-1] = last
    return "\n".join(lines) + "\n"


def _finalize_extract_ir_before_pass_output(path: Path, *, what: str) -> None:
    """Keep text between the first two ``---`` markers, then apply `_normalize_extract_ir_ll_text`."""
    marker = "---"
    raw = path.read_text(encoding="utf-8", errors="replace")
    start = raw.find(marker)
    if start == -1:
        raise SystemExit(
            f"llc ({what}): expected two {marker!r} delimiters in {path}; found none."
        )
    after_first = start + len(marker)
    end = raw.find(marker, after_first)
    if end == -1:
        raise SystemExit(
            f"llc ({what}): expected a second {marker!r} delimiter in {path}; found only one."
        )
    inner = raw[after_first:end].strip()
    path.write_text(_normalize_extract_ir_ll_text(inner), encoding="utf-8")


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
        interesting = _interesting_script_for_llvm_reduce_ir(ctx)
        exe = ctx.llvm_reduce
        out = tmp_pass_path(ctx.tmp_dir, step, "llvmreduce", test.test_path.suffix)
        cmd = [
            str(exe),
            f"--test={interesting.resolve()}",
            f"-o={out}",
            str(test.test_path.resolve()),
        ]
        r = run_subprocess(
            logger,
            cmd,
            label="llvm-reduce",
            capture_output=True,
            text=True,
            cwd=ctx.tmp_dir,
        )
        if r.returncode != 0:
            msg = (r.stderr or r.stdout or "").strip() or "(no output)"
            raise SystemExit(f"llvm-reduce failed ({r.returncode}):\n{msg}")
        if not out.is_file():
            raise SystemExit(f"llvm-reduce did not write expected output: {out}")

        if test.test_path.suffix == ".bc":
            llvm_dis = _require_llvm_dis(ctx)
            cmd = [
                str(llvm_dis),
                "-o",
                str(out.with_suffix(".ll").resolve()),
                str(out.resolve()),
            ]
            r = run_subprocess(
                logger,
                cmd,
                label="llvm-dis",
                capture_output=True,
                text=True,
                cwd=ctx.tmp_dir,
            )
            if r.returncode != 0:
                msg = (r.stderr or r.stdout or "").strip() or "(no output)"
                raise SystemExit(f"llvm-dis failed ({r.returncode}):\n{msg}")
            if not out.is_file():
                raise SystemExit(f"llvm-dis did not write expected output: {out}")
            out = out.with_suffix(".ll")
        return Test(out, interesting, test.file, test.line)


class CreducePass(ReducePass):
    """Run ``creduce`` with a generated copy of the interesting-ness script."""

    def run(self, ctx: ReduceContext, test: Test, *, step: int) -> Test:
        interesting_src = _interesting_script_for_llvm_reduce_ir(ctx)
        exe = shutil.which("creduce")
        if exe is None:
            raise SystemExit("creduce not found in PATH")

        out = tmp_pass_path_for_input(ctx.tmp_dir, step, "creduce", test.test_path)
        shutil.copy2(test.test_path, out)

        interesting_copy = ctx.tmp_dir / (
            f"{step:02d}_creduce_interesting{interesting_src.suffix or '.sh'}"
        )
        _creduce_interesting_copy_with_candidate(interesting_src, interesting_copy, out)

        n = _creduce_n_cores(ctx)
        cmd = [
            exe,
            "--n",
            str(n),
            str(interesting_copy.resolve()),
            str(out.resolve()),
        ]
        r = run_subprocess(
            logger,
            cmd,
            label="creduce",
            capture_output=True,
            text=True,
            cwd=ctx.tmp_dir,
        )
        if r.returncode != 0:
            msg = (r.stderr or r.stdout or "").strip() or "(no output)"
            raise SystemExit(f"creduce failed ({r.returncode}):\n{msg}")
        if not out.is_file():
            raise SystemExit(f"creduce did not write expected output: {out}")
        return Test(out, interesting_copy, test.file, test.line)


class LlvmReduceMirPass(ReducePass):
    """Run ``llvm-reduce -x=mir`` with ``--test=<interesting_mir>``."""

    def run(self, ctx: ReduceContext, test: Test, *, step: int) -> Test:
        interesting_mir = _require_interesting_mir_script(ctx)
        exe = ctx.llvm_reduce
        out = tmp_pass_path_mir(ctx.tmp_dir, step, "llvmreduce_mir")
        cmd = [
            str(exe),
            "-x=mir",
            f"--test={interesting_mir.resolve()}",
            f"-o={out}",
            str(test.test_path.resolve()),
        ]
        r = run_subprocess(
            logger,
            cmd,
            label="llvm-reduce (-x=mir)",
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
        emo = ctx.pass_options.get("extract_mir_output")
        if emo:
            if not isinstance(emo, str):
                raise SystemExit('extract_mir_before_pass: "extract_mir_output" must be a string.')
            name = Path(emo).name
            dest = ctx.tmp_dir / f"{step:02d}_{name}"
        else:
            dest = ctx.tmp_dir / f"{step:02d}_mir_before_pass.mir"

        return _run_llc_extract_core(
            ctx,
            test,
            llc_opts,
            dest=dest,
            what="extract_mir_before_pass",
            pass_specific_args=_llc_stop_before_args(
                llc_opts.pass_under_test, simplify_mir=True
            ),
        )


class ExtractIrBeforePass(ReducePass):
    """``llc`` stop-before without ``-simplify-mir``; output is sliced on ``---`` then cleaned for LLVM IR."""

    _what = "extract_ir_before_pass"

    def run(self, ctx: ReduceContext, test: Test, *, step: int) -> Test:
        llc_opts = _require_extract_mir_context(ctx)
        eio = ctx.pass_options.get("extract_ir_before_output")
        if eio:
            if not isinstance(eio, str):
                raise SystemExit('extract_ir_before_pass: "extract_ir_before_output" must be a string.')
            name = Path(eio).name
            dest = ctx.tmp_dir / f"{step:02d}_{name}"
        else:
            dest = ctx.tmp_dir / f"{step:02d}_ir_before_pass.ll"

        out = _run_llc_extract_core(
            ctx,
            test,
            llc_opts,
            dest=dest,
            what=self._what,
            pass_specific_args=_llc_stop_before_args(
                llc_opts.pass_under_test, simplify_mir=False
            ),
        )
        _finalize_extract_ir_before_pass_output(out.test_path, what=self._what)
        return out
