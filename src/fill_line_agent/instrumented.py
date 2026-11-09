# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Load instrumented opt/llc/sancov from one bin dir and build symcov indexes."""

from __future__ import annotations

import concurrent.futures
import os
import shutil
import subprocess
from pathlib import Path

from fill_line_agent.oracle import (
    UBSAN_COVERAGE_OPTS,
    SymcovIndex,
    ToolName,
    _find_sancov,
)
from fill_line_agent.steps import StepTracker
from fill_line_agent.tool_runner import ToolRunner
from fuzz_fill.log import get_logger

logger = get_logger("fill_line_agent.instrumented")

SYMBOLIZE_TIMEOUT_S = 300.0
VERSION_TIMEOUT_S = 60.0
TOOL_NAMES: tuple[ToolName, ...] = ("opt", "llc")


def resolve_bin_dir(bin_dir: Path) -> tuple[dict[ToolName, Path], Path]:
    """Find opt/llc/sancov under *bin_dir*. Require sancov and at least one tool."""
    root = bin_dir.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"instrumented-bin-dir not found: {root}")

    tools: dict[ToolName, Path] = {}
    for name in TOOL_NAMES:
        path = root / name
        if path.is_file() and os.access(path, os.X_OK):
            tools[name] = path
    sancov = root / "sancov"
    if not (sancov.is_file() and os.access(sancov, os.X_OK)):
        raise SystemExit(f"sancov not found (or not executable) in {root}")
    if not tools:
        raise SystemExit(f"neither opt nor llc found in {root}")
    return tools, sancov


def build_symcov(
    *,
    tool: ToolName,
    tool_bin: Path,
    sancov_bin: Path,
    work_dir: Path,
    runner: ToolRunner,
    timeout_s: float = SYMBOLIZE_TIMEOUT_S,
) -> Path:
    """Run ``tool --version`` under coverage and symbolize into *work_dir*.

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

    try:
        runner.run(
            [str(tool_bin), "--version"],
            env=env,
            timeout_s=min(timeout_s, VERSION_TIMEOUT_S),
            bind_paths=[tool_bin, dump_dir.resolve()],
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f"{tool} --version timed out while collecting coverage") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"{tool} --version failed (exit {exc.returncode}): {exc.stderr}"
        ) from exc

    sancov_path = _find_sancov(dump_dir, tool)
    if sancov_path is None:
        raise SystemExit(
            f"no {tool}.*.sancov produced by {tool} --version under {dump_dir}"
        )

    symcov_path = work_dir / f"{tool}.symcov"
    try:
        with symcov_path.open("w", encoding="utf-8") as out:
            proc = runner.run(
                [
                    str(sancov_bin),
                    "-symbolize",
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
    tool: ToolName,
    tool_bin: Path,
    sancov_bin: Path,
    work_dir: Path,
    runner: ToolRunner,
) -> tuple[ToolName, Path, SymcovIndex]:
    symcov_path = build_symcov(
        tool=tool,
        tool_bin=tool_bin,
        sancov_bin=sancov_bin,
        work_dir=work_dir,
        runner=runner,
    )
    return tool, symcov_path, SymcovIndex.load(symcov_path)


def load_instrumented(
    *,
    bin_dir: Path,
    work_dir: Path,
    runner: ToolRunner,
    steps: StepTracker,
) -> tuple[dict[ToolName, Path], dict[ToolName, SymcovIndex], Path]:
    """Resolve binaries under *bin_dir* and build fresh symcov indexes in *work_dir*."""
    tools, sancov = resolve_bin_dir(bin_dir)
    work_dir = work_dir.expanduser().resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "instrumented-bin-dir=%s tools=%s sancov=%s",
        bin_dir.resolve(),
        sorted(tools),
        sancov,
    )

    indexes: dict[ToolName, SymcovIndex] = {}
    # Symbolize tools in parallel; each gets its own step timer via the outer loop log.
    with steps.step("symbolize", ",".join(sorted(tools))):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(tools)) as pool:
            futures = {
                pool.submit(
                    _build_one,
                    tool=name,
                    tool_bin=path,
                    sancov_bin=sancov,
                    work_dir=work_dir,
                    runner=runner,
                ): name
                for name, path in tools.items()
            }
            for fut in concurrent.futures.as_completed(futures):
                name, symcov_path, index = fut.result()
                indexes[name] = index
                logger.info("symbolize done: %s -> %s", name, symcov_path)

    return tools, indexes, sancov
