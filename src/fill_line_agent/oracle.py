# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Coverage oracle for the fill-line agent: no LLM code."""

from __future__ import annotations

import difflib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from fill_line_agent.tool_runner import ToolRunner
from coverage.sancov import Sancov
from reduce.batch.coverage import llvm_rel_source_path

UBSAN_COVERAGE_OPTS = "coverage=1:coverage_dir={dir}:print_coverage_summary=0"
NEARBY_WINDOW_LINES = 40
DIFF_MAX_LINES = 200

LineStatus = Literal["covered", "partial", "uncovered", "missed", "hit"]
TargetStatus = Literal["covered", "partial", "uncovered"]
ToolName = Literal["opt", "llc"]
InputFormat = Literal["ll", "mir"]


def _safe_rel_path(path: str) -> str:
    """Normalize a source path to an ``llvm/...`` relative form when possible."""
    try:
        return llvm_rel_source_path(path)
    except ValueError:
        return path.replace("\\", "/")


@dataclass(frozen=True)
class TargetLine:
    rel_path: str
    line: int

    @classmethod
    def parse(cls, value: str) -> TargetLine:
        if ":" not in value:
            raise ValueError(f"target must be path:line, got {value!r}")
        path, _, line_s = value.rpartition(":")
        if not path or not line_s.isdigit():
            raise ValueError(f"target must be path:line, got {value!r}")
        return cls(rel_path=_safe_rel_path(path), line=int(line_s))

    def __str__(self) -> str:
        return f"{self.rel_path}:{self.line}"


@dataclass
class NearbyLine:
    line: int
    distance: int
    status: Literal["hit", "partial", "missed"]
    n_hit: int
    n_points: int


@dataclass
class MeasureResult:
    status: TargetStatus
    n_hit: int
    n_points: int
    function: str | None
    function_n_hit: int
    function_n_points: int
    nearby: list[NearbyLine] = field(default_factory=list)
    closest_hit_distance: int | None = None


@dataclass
class RunResult:
    tool: ToolName
    argv: list[str]
    fmt: InputFormat
    input_text: str
    exit_code: int
    timed_out: bool
    stdout: str
    stderr: str
    capture: str | None
    changed: bool
    diff: str
    hit_points: set[str]
    sancov_path: Path | None
    run_dir: Path
    measure: MeasureResult | None = None


class SymcovIndex:
    """Index of instrumentation points from one tool's symcov JSON."""

    def __init__(
        self,
        *,
        line_points: dict[tuple[str, int], set[str]],
        point_function: dict[str, str],
        line_function: dict[tuple[str, int], str],
        path: Path | None = None,
    ) -> None:
        self.line_points = line_points
        self.point_function = point_function
        self.line_function = line_function
        self.path = path

    @classmethod
    def load(cls, path: Path) -> SymcovIndex:
        data = json.loads(path.read_text(encoding="utf-8"))
        psi = data.get("point-symbol-info") or {}
        line_points: dict[tuple[str, int], set[str]] = {}
        point_function: dict[str, str] = {}
        line_function: dict[tuple[str, int], str] = {}

        for file_path, functions in psi.items():
            rel = _safe_rel_path(str(file_path))
            if not isinstance(functions, dict):
                continue
            for fn_name, addr_to_line in functions.items():
                if not isinstance(addr_to_line, dict):
                    continue
                for addr, line_col in addr_to_line.items():
                    point = Sancov.format_hex_address(addr)
                    line = int(str(line_col).partition(":")[0])
                    key = (rel, line)
                    line_points.setdefault(key, set()).add(point)
                    point_function[point] = str(fn_name)
                    line_function.setdefault(key, str(fn_name))

        return cls(
            line_points=line_points,
            point_function=point_function,
            line_function=line_function,
            path=path,
        )

    def points_for(self, target: TargetLine) -> set[str]:
        return set(self.line_points.get((target.rel_path, target.line), ()))

    def is_instrumented(self, target: TargetLine) -> bool:
        return bool(self.points_for(target))

    def function_for(self, target: TargetLine) -> str | None:
        return self.line_function.get((target.rel_path, target.line))

    def function_line_range(self, target: TargetLine) -> tuple[str, int, int] | None:
        """Return ``(function, first, last)`` instrumented lines of the target's function."""
        fn = self.function_for(target)
        if fn is None:
            return None
        lines = [
            line
            for (path, line), name in self.line_function.items()
            if path == target.rel_path and name == fn
        ]
        if not lines:
            return None
        return fn, min(lines), max(lines)

    def instrumented_lines(
        self, rel_path: str, start: int, end: int
    ) -> list[dict[str, object]]:
        rel = _safe_rel_path(rel_path)
        lo, hi = sorted((int(start), int(end)))
        out: list[dict[str, object]] = []
        for (path, line), points in sorted(self.line_points.items()):
            if path != rel or line < lo or line > hi:
                continue
            out.append(
                {
                    "path": path,
                    "line": line,
                    "n_points": len(points),
                    "function": self.line_function.get((path, line)),
                }
            )
        return out


def _line_status(n_hit: int, n_points: int) -> Literal["hit", "partial", "missed"]:
    if n_points == 0:
        return "missed"
    if n_hit == n_points:
        return "hit"
    if n_hit == 0:
        return "missed"
    return "partial"


def measure_hits(
    index: SymcovIndex,
    target: TargetLine,
    hit_points: set[str],
    *,
    nearby_window: int = NEARBY_WINDOW_LINES,
) -> MeasureResult:
    points = index.points_for(target)
    n_points = len(points)
    n_hit = len(points & hit_points)
    if n_points == 0:
        status: TargetStatus = "uncovered"
    elif n_hit == n_points:
        status = "covered"
    elif n_hit == 0:
        status = "uncovered"
    else:
        status = "partial"

    function = index.function_for(target)
    fn_points: set[str] = set()
    if function is not None:
        for point, fn in index.point_function.items():
            if fn == function:
                fn_points.add(point)
    function_n_hit = len(fn_points & hit_points)
    function_n_points = len(fn_points)

    nearby: list[NearbyLine] = []
    closest: int | None = None
    for (path, line), pts in index.line_points.items():
        if path != target.rel_path:
            continue
        same_fn = index.line_function.get((path, line)) == function
        distance = abs(line - target.line)
        if line == target.line:
            continue
        if not same_fn and distance > nearby_window:
            continue
        n_p = len(pts)
        n_h = len(pts & hit_points)
        st = _line_status(n_h, n_p)
        nearby.append(
            NearbyLine(
                line=line,
                distance=distance,
                status=st,
                n_hit=n_h,
                n_points=n_p,
            )
        )
        if st in ("hit", "partial") and (closest is None or distance < closest):
            closest = distance
    nearby.sort(key=lambda row: (row.distance, row.line))

    return MeasureResult(
        status=status,
        n_hit=n_hit,
        n_points=n_points,
        function=function,
        function_n_hit=function_n_hit,
        function_n_points=function_n_points,
        nearby=nearby,
        closest_hit_distance=closest,
    )


def _unified_diff(a: str, b: str, *, max_lines: int = DIFF_MAX_LINES) -> str:
    lines = list(
        difflib.unified_diff(
            a.splitlines(),
            b.splitlines(),
            fromfile="input",
            tofile="output",
            lineterm="",
        )
    )
    if len(lines) > max_lines:
        omitted = len(lines) - max_lines
        lines = lines[:max_lines] + [f"... truncated {omitted} more lines ..."]
    return "\n".join(lines)


def _find_sancov(run_dir: Path, tool: str) -> Path | None:
    matches = sorted(run_dir.glob(f"{tool}.*.sancov"))
    if not matches:
        return None
    return matches[-1]


@dataclass
class CoverageOracle:
    """Run instrumented opt/llc and measure coverage for a fixed target."""

    tools: dict[ToolName, Path]
    indexes: dict[ToolName, SymcovIndex]
    sancov_bin: Path
    target: TargetLine
    work_root: Path
    timeout_s: float = 30.0
    runner: ToolRunner = field(default_factory=ToolRunner)

    def __post_init__(self) -> None:
        self.work_root.mkdir(parents=True, exist_ok=True)
        self._run_counter = 0

    @property
    def run_counter(self) -> int:
        return self._run_counter

    def set_run_counter(self, value: int) -> None:
        self._run_counter = max(0, int(value))

    def tools_instrumenting(self) -> list[ToolName]:
        return [name for name, idx in self.indexes.items() if idx.is_instrumented(self.target)]

    def function_line_range(self, target: TargetLine) -> tuple[str, int, int] | None:
        for idx in self.indexes.values():
            found = idx.function_line_range(target)
            if found is not None:
                return found
        return None

    def run(
        self,
        tool: ToolName,
        argv: list[str],
        input_text: str,
        fmt: InputFormat,
    ) -> RunResult:
        if tool not in self.tools:
            raise ValueError(f"tool {tool!r} is not available")
        if tool not in self.indexes:
            raise ValueError(f"no symcov for tool {tool!r}")

        self._run_counter += 1
        run_dir = self.work_root / f"run_{self._run_counter:04d}"
        # A reused --work-dir may hold a previous session's .sancov here.
        shutil.rmtree(run_dir, ignore_errors=True)
        run_dir.mkdir(parents=True, exist_ok=True)

        input_path = run_dir / f"input.{fmt}"
        capture_path = run_dir / f"output.{fmt}"
        input_path.write_text(input_text, encoding="utf-8")

        tool_bin = self.tools[tool].resolve()
        cmd = [
            str(tool_bin),
            *argv,
            str(input_path.resolve()),
            "-o",
            str(capture_path.resolve()),
        ]
        env = os.environ.copy()
        cov_opts = UBSAN_COVERAGE_OPTS.format(dir=str(run_dir.resolve()))
        prev = env.get("UBSAN_OPTIONS", "").strip()
        env["UBSAN_OPTIONS"] = f"{cov_opts}:{prev}" if prev else cov_opts

        timed_out = False
        try:
            proc = self.runner.run(
                cmd,
                env=env,
                timeout_s=self.timeout_s,
                bind_paths=[tool_bin, run_dir.resolve()],
            )
            exit_code = proc.returncode
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = -1
            stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else "timed out"

        capture: str | None = None
        if capture_path.is_file():
            capture = capture_path.read_text(encoding="utf-8", errors="replace")
        changed = capture is not None and capture != input_text
        diff = (
            _unified_diff(input_text, capture)
            if capture is not None
            else ("(no capture; process exited non-zero or produced no -o file)")
        )

        sancov_path = _find_sancov(run_dir, tool)
        hit_points: set[str] = set()
        if sancov_path is not None:
            try:
                printed = self.runner.run(
                    [
                        str(self.sancov_bin.resolve()),
                        "--print",
                        str(sancov_path.resolve()),
                    ],
                    timeout_s=self.timeout_s,
                    bind_paths=[self.sancov_bin.resolve(), sancov_path.resolve()],
                    check=True,
                )
                hit_points = Sancov.parse_print_output(printed.stdout)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
                hit_points = set()

        measure = measure_hits(self.indexes[tool], self.target, hit_points)
        return RunResult(
            tool=tool,
            argv=list(argv),
            fmt=fmt,
            input_text=input_text,
            exit_code=exit_code,
            timed_out=timed_out,
            stdout=stdout,
            stderr=stderr,
            capture=capture,
            changed=changed,
            diff=diff,
            hit_points=hit_points,
            sancov_path=sancov_path,
            run_dir=run_dir,
            measure=measure,
        )


def stream_tail(text: str, *, n_lines: int = 100) -> str:
    lines = text.splitlines()
    if len(lines) <= n_lines:
        return text
    return "\n".join(lines[-n_lines:])


def stream_page(text: str, *, offset: int = 0, n_lines: int = 100) -> dict[str, object]:
    lines = text.splitlines()
    start = max(0, int(offset))
    end = min(len(lines), start + n_lines)
    return {
        "offset": start,
        "end": end,
        "total_lines": len(lines),
        "text": "\n".join(lines[start:end]),
    }
