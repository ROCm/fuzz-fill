# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Load instrumented opt/llc/clang/sancov from one bin dir and build symcov indexes."""

from __future__ import annotations

import concurrent.futures
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from fill_line_agent.oracle import (
    UBSAN_COVERAGE_OPTS,
    SymcovIndex,
    find_sancov_files,
)
from fill_line_agent.steps import StepTracker
from fill_line_agent.tool_runner import ToolRunner
from fill_line_agent.toolset import CLANG_TOOLS, ToolName
from fuzz_fill.log import get_logger

logger = get_logger("fill_line_agent.instrumented")

SYMBOLIZE_TIMEOUT_S = 300.0
VERSION_TIMEOUT_S = 60.0
SMOKE_TIMEOUT_S = 30.0
# Binary keys that get their own --version symbolize pass.
BINARY_TOOL_NAMES: tuple[str, ...] = ("opt", "llc", "clang")


def resolve_clang_resource_include(bin_dir: Path) -> Path | None:
    """Return the unique ``lib/clang/<ver>/include`` next to *bin_dir*, or None."""
    root = bin_dir.expanduser().resolve()
    resource_dirs = sorted(
        p for p in (root.parent / "lib" / "clang").glob("*/include") if p.is_dir()
    )
    if len(resource_dirs) != 1:
        return None
    return resource_dirs[0]


def _try_add_clang(
    root: Path, runner: ToolRunner
) -> dict[ToolName, Path] | None:
    """Return agent tool → binary map for clang, or None if safecheck fails.

    The smoke ``-cc1`` runs through *runner* so docker mode works when the
    host glibc is too old for the CI-built clang binary.
    """
    clang = root / "clang"
    clangxx = root / "clang++"
    if not (clang.is_file() and os.access(clang, os.X_OK)):
        logger.info("clang not offered: %s missing or not executable", clang)
        return None
    if not (clangxx.is_file() and os.access(clangxx, os.X_OK)):
        logger.info("clang not offered: %s missing or not executable", clangxx)
        return None
    clang_real = clang.resolve()
    clangxx_real = clangxx.resolve()
    if clang_real != clangxx_real:
        logger.info(
            "clang not offered: clang++ resolves to %s, clang to %s",
            clangxx_real,
            clang_real,
        )
        return None
    resource = resolve_clang_resource_include(root)
    if resource is None:
        logger.info(
            "clang not offered: expected one resource include under %s/../lib/clang/*/include",
            root,
        )
        return None
    # Smoke: empty .c through -cc1 -fsyntax-only (via runner).
    try:
        with tempfile.TemporaryDirectory(prefix="clang-smoke-") as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "empty.c"
            src.write_text("\n", encoding="utf-8")
            proc = runner.run(
                [
                    str(clang_real),
                    "-cc1",
                    "-internal-isystem",
                    str(resource),
                    "-nostdsysteminc",
                    "-triple",
                    "x86_64-unknown-linux-gnu",
                    "-fsyntax-only",
                    str(src),
                ],
                timeout_s=SMOKE_TIMEOUT_S,
                bind_paths=[clang_real, resource, tmp_path, root.parent],
                check=False,
            )
            if proc.returncode != 0:
                logger.info(
                    "clang not offered: smoke -cc1 failed (exit %s): %s",
                    proc.returncode,
                    (proc.stderr or proc.stdout or "").strip()[:500],
                )
                return None
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        logger.info("clang not offered: smoke -cc1 error: %s", exc)
        return None

    return {
        "clang_cc1": clang,
        "clang": clang,
        "clangxx": clangxx,
    }


def resolve_bin_dir(
    bin_dir: Path,
    runner: ToolRunner,
) -> tuple[dict[ToolName, Path], Path, Path | None]:
    """Find opt/llc/sancov under *bin_dir*; optionally clang + resource include.

    Returns ``(tools, sancov, resource_include)``. Requires sancov and at least
    one of opt/llc. Clang is omitted (not a hard failure) when safechecks fail.
    """
    root = bin_dir.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"instrumented-bin-dir not found: {root}")

    tools: dict[ToolName, Path] = {}
    for name in ("opt", "llc"):
        path = root / name
        if path.is_file() and os.access(path, os.X_OK):
            tools[name] = path  # type: ignore[assignment]
    sancov = root / "sancov"
    if not (sancov.is_file() and os.access(sancov, os.X_OK)):
        raise SystemExit(f"sancov not found (or not executable) in {root}")
    if not tools:
        raise SystemExit(f"neither opt nor llc found in {root}")

    resource: Path | None = None
    clang_tools = _try_add_clang(root, runner)
    if clang_tools is not None:
        tools.update(clang_tools)
        resource = resolve_clang_resource_include(root)

    return tools, sancov, resource

def build_symcov(
    *,
    tool: str,
    tool_bin: Path,
    sancov_bin: Path,
    work_dir: Path,
    runner: ToolRunner,
    timeout_s: float = SYMBOLIZE_TIMEOUT_S,
    bind_extra: list[Path] | None = None,
) -> Path:
    """Run ``tool --version`` under coverage and symbolize into *work_dir*.

    Uses ``sancov -symbolize --no-skip-dead-files`` so files never touched by
    ``--version`` still appear in ``point-symbol-info``.

    Returns the path of the written ``.symcov`` file. Never writes into the bin dir.
    """
    dump_dir = work_dir / tool
    shutil.rmtree(dump_dir, ignore_errors=True)
    dump_dir.mkdir(parents=True, exist_ok=True)
    tool_bin = tool_bin.resolve()
    sancov_bin = sancov_bin.resolve()

    env = os.environ.copy()
    cov_opts = UBSAN_COVERAGE_OPTS.format(dir=str(dump_dir.resolve()))
    prev = env.get("UBSAN_OPTIONS", "").strip()
    env["UBSAN_OPTIONS"] = f"{cov_opts}:{prev}" if prev else cov_opts

    binds = [tool_bin, dump_dir.resolve()]
    if bind_extra:
        binds.extend(bind_extra)

    try:
        runner.run(
            [str(tool_bin), "--version"],
            env=env,
            timeout_s=min(timeout_s, VERSION_TIMEOUT_S),
            bind_paths=binds,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f"{tool} --version timed out while collecting coverage") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"{tool} --version failed (exit {exc.returncode}): {exc.stderr}"
        ) from exc

    dumps = find_sancov_files(dump_dir, tool)
    if not dumps:
        raise SystemExit(
            f"no {tool}-named .sancov produced by {tool} --version under {dump_dir}"
        )
    # One dump for --version; take the newest matching name.
    sancov_path = dumps[-1]

    symcov_path = work_dir / f"{tool}.symcov"
    try:
        with symcov_path.open("w", encoding="utf-8") as out:
            proc = runner.run(
                [
                    str(sancov_bin),
                    "-symbolize",
                    "--no-skip-dead-files",
                    str(sancov_path.resolve()),
                    str(tool_bin),
                ],
                timeout_s=timeout_s,
                bind_paths=[sancov_bin, sancov_path.resolve(), tool_bin],
                check=True,
            )
            out.write(proc.stdout or "")
    except subprocess.TimeoutExpired as exc:
        symcov_path.unlink(missing_ok=True)
        raise SystemExit(f"sancov -symbolize for {tool} timed out") from exc
    except subprocess.CalledProcessError as exc:
        symcov_path.unlink(missing_ok=True)
        raise SystemExit(
            f"sancov -symbolize for {tool} failed (exit {exc.returncode}): {exc.stderr}"
        ) from exc

    if not symcov_path.is_file() or symcov_path.stat().st_size == 0:
        raise SystemExit(f"empty symcov written for {tool}: {symcov_path}")
    return symcov_path


def _build_one(
    *,
    tool: str,
    tool_bin: Path,
    sancov_bin: Path,
    work_dir: Path,
    runner: ToolRunner,
    bind_extra: list[Path] | None,
) -> tuple[str, Path, SymcovIndex]:
    symcov_path = build_symcov(
        tool=tool,
        tool_bin=tool_bin,
        sancov_bin=sancov_bin,
        work_dir=work_dir,
        runner=runner,
        bind_extra=bind_extra,
    )
    return tool, symcov_path, SymcovIndex.load(symcov_path)


def load_instrumented(
    *,
    bin_dir: Path,
    work_dir: Path,
    runner: ToolRunner,
    steps: StepTracker,
) -> tuple[dict[ToolName, Path], dict[ToolName, SymcovIndex], Path, Path | None]:
    """Resolve binaries under *bin_dir* and build fresh symcov indexes in *work_dir*.

    Returns ``(tools, indexes, sancov, resource_include)``. When clang is present,
    ``clang.symcov`` is built once and shared by ``clang_cc1`` / ``clang`` / ``clangxx``.
    """
    tools, sancov, resource = resolve_bin_dir(bin_dir, runner)
    work_dir = work_dir.expanduser().resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "instrumented-bin-dir=%s tools=%s sancov=%s resource=%s",
        bin_dir.resolve(),
        sorted(tools),
        sancov,
        resource,
    )

    # Symbolize each distinct binary once (clang shared across three agent tools).
    binary_jobs: dict[str, Path] = {}
    for name, path in tools.items():
        if name in ("opt", "llc"):
            binary_jobs[name] = path
        elif name in CLANG_TOOLS and "clang" not in binary_jobs:
            binary_jobs["clang"] = path.resolve()

    bind_extra = [bin_dir.expanduser().resolve().parent]
    if resource is not None:
        bind_extra.append(resource)

    binary_indexes: dict[str, SymcovIndex] = {}
    with steps.step("symbolize", ",".join(sorted(binary_jobs))):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(binary_jobs)) as pool:
            futures = {
                pool.submit(
                    _build_one,
                    tool=name,
                    tool_bin=path,
                    sancov_bin=sancov,
                    work_dir=work_dir,
                    runner=runner,
                    bind_extra=bind_extra if name == "clang" else None,
                ): name
                for name, path in binary_jobs.items()
            }
            for fut in concurrent.futures.as_completed(futures):
                name, symcov_path, index = fut.result()
                binary_indexes[name] = index
                logger.info("symbolize done: %s -> %s", name, symcov_path)

    indexes: dict[ToolName, SymcovIndex] = {}
    for name in tools:
        if name in ("opt", "llc"):
            indexes[name] = binary_indexes[name]
        else:
            indexes[name] = binary_indexes["clang"]

    return tools, indexes, sancov, resource
