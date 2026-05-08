from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from reduce.pass_registry import known_pass_ids, passes_from_ids
from reduce.test import Test

from reduce.config import PipelineStep


@dataclass(frozen=True)
class ReduceContext:
    """Per-run context. Passes read/write intermediates under ``tmp_dir`` only."""

    llvm_bin: Path
    output_dir: Path
    tmp_dir: Path
    pass_options: Mapping[str, Any]
    """Options for the current pipeline step (from that step's ``parameters``)."""


class Reducer:
    def __init__(
        self,
        llvm_bin: Path,
        output_dir: Path,
        test: Test,
        *,
        pipeline_steps: tuple[PipelineStep, ...],
    ):
        self.llvm_bin: Path = llvm_bin
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
                llvm_bin=self.llvm_bin,
                output_dir=self.output_dir,
                tmp_dir=tmp_dir,
                pass_options=MappingProxyType(dict(self._pipeline_steps[step].options)),
            )
            test = p.run(ctx, test, step=step)

        suffix = test.test_path.suffix if test.test_path.suffix else ".ll"
        final_name = "reduced.ll" if suffix == ".ll" else f"reduced{suffix}"
        final_path = self.output_dir / final_name
        shutil.copy2(test.test_path, final_path)
        print(f"[reduce] wrote {final_path}", flush=True)
        return Test(final_path, test.interesting, test.file, test.line)
