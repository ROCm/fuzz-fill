from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from reduce.pass_registry import known_pass_ids, passes_from_ids
from reduce.test import Test

from reduce.config import PipelineStep
from fuzz_fill.llvm_tools import ReduceTools
from fuzz_fill.log import get_logger, log_timing, run_subprocess

logger = get_logger("reduce")

_INTERESTING_SCRIPT_KEY_BY_PASS: dict[str, str] = {
    "llvm_reduce_ir": "interesting",
    "creduce": "interesting",
    "llvm_reduce_mir": "interesting_mir",
}


def _interesting_script_for_final_check(
    pipeline_steps: tuple[PipelineStep, ...],
) -> Path | None:
    """Return the interesting-ness script for the last reducing pass in the pipeline."""
    for step in reversed(pipeline_steps):
        key = _INTERESTING_SCRIPT_KEY_BY_PASS.get(step.id)
        if key is None:
            continue
        script = step.options.get(key)
        if script is None:
            continue
        if isinstance(script, Path):
            return script
        if isinstance(script, str):
            return Path(script)
        raise SystemExit(
            f"pipeline step {step.id!r}: {key!r} must be a path string, "
            f"got {type(script).__name__}."
        )
    return None


def _verify_final_interesting(script: Path, candidate: Path) -> None:
    script = script.resolve()
    candidate = candidate.resolve()
    if not script.is_file():
        raise SystemExit(f"interesting-ness script not found: {script}")
    r = run_subprocess(
        logger,
        [str(script), str(candidate)],
        label="interesting-ness check",
        capture_output=True,
        text=True,
    )
    if r.returncode == 0:
        return
    msg = (r.stderr or r.stdout or "").strip() or "(no output)"
    raise SystemExit(
        "final reduced file failed interesting-ness test "
        f"({r.returncode}):\n"
        f"  script: {script}\n"
        f"  candidate: {candidate}\n"
        f"{msg}"
    )


@dataclass(frozen=True)
class ReduceContext:
    """Per-run context. Passes read/write intermediates under ``tmp_dir`` only."""

    llc: Path
    llvm_reduce: Path
    llvm_dis: Path | None
    output_dir: Path
    tmp_dir: Path
    pass_options: Mapping[str, Any]
    """Options for the current pipeline step (from that step's ``parameters``)."""


class Reducer:
    def __init__(
        self,
        tools: ReduceTools,
        output_dir: Path,
        test: Test,
        *,
        pipeline_steps: tuple[PipelineStep, ...],
    ):
        self.tools = tools
        self.output_dir: Path = output_dir
        self.test: Test = test
        self._pipeline_steps: tuple[PipelineStep, ...] = pipeline_steps
        self._pass_ids: list[str] = [s.id for s in pipeline_steps]
        self._passes_list = passes_from_ids(self._pass_ids)

    def reduce(self) -> Test:
        tmp_dir = self.output_dir / "tmp"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        test = self.test
        n = len(self._passes_list)
        for step, (pass_id, p) in enumerate(zip(self._pass_ids, self._passes_list)):
            print(f"[reduce] pass {step + 1}/{n}: {pass_id}", flush=True)
            ctx = ReduceContext(
                llc=self.tools.llc,
                llvm_reduce=self.tools.llvm_reduce,
                llvm_dis=self.tools.llvm_dis,
                output_dir=self.output_dir,
                tmp_dir=tmp_dir,
                pass_options=MappingProxyType(dict(self._pipeline_steps[step].options)),
            )
            with log_timing(logger, f"pass {step + 1}/{n}: {pass_id}"):
                test = p.run(ctx, test, step=step)

        suffix = test.test_path.suffix if test.test_path.suffix else ".ll"
        final_name = "reduced.ll" if suffix == ".ll" else f"reduced{suffix}"
        final_path = self.output_dir / final_name
        shutil.copy2(test.test_path, final_path)
        print(f"[reduce] wrote {final_path}", flush=True)

        interesting = _interesting_script_for_final_check(self._pipeline_steps)
        if interesting is not None:
            print(
                f"[reduce] verifying final interesting-ness ({interesting})...",
                flush=True,
            )
            with log_timing(logger, "final interesting-ness check"):
                _verify_final_interesting(interesting, final_path)
            print("[reduce] final interesting-ness check passed", flush=True)

        return Test(final_path, test.interesting, test.file, test.line)
