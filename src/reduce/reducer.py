from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from reduce.test import Test


FINAL_REDUCED_NAME = "reduced.ll"


def tmp_pass_path(tmp_dir: Path, step: int, slug: str) -> Path:
    """``tmp_dir / "00_snapshot.ll"``-style names, ordered by pipeline index."""
    return tmp_dir / f"{step:02d}_{slug}.ll"


@dataclass(frozen=True)
class ReduceContext:
    """Per-run context. Passes read/write intermediates under ``tmp_dir`` only."""

    llvm_bin: Path
    output_dir: Path
    tmp_dir: Path


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


class ExampleTransformPass(ReducePass):
    """
    Template pass: replace the copy with your transform.

    Read ``test.test_path``, write via ``tmp_pass_path(ctx.tmp_dir, step, "yourslug")``,
    then return ``Test(new_path, test.interesting, test.file, test.line)``.
    """

    def run(self, ctx: ReduceContext, test: Test, *, step: int) -> Test:
        dest = tmp_pass_path(ctx.tmp_dir, step, "example")
        shutil.copy2(test.test_path, dest)
        return Test(dest, test.interesting, test.file, test.line)


class Reducer:
    def __init__(
        self,
        llvm_bin: Path,
        output_dir: Path,
        test: Test,
        *,
        engine: str = "llvmreduce-ir",
    ):
        self.llvm_bin: Path = llvm_bin
        self.output_dir: Path = output_dir
        self.test: Test = test
        self.engine: str = engine

    def _passes(self) -> list[ReducePass]:
        # Later: branch on self.engine for different pipelines.
        return [
            SnapshotPass(),
            ExampleTransformPass(),
        ]

    def reduce(self) -> Test:
        tmp_dir = self.output_dir / "tmp"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        ctx = ReduceContext(
            llvm_bin=self.llvm_bin,
            output_dir=self.output_dir,
            tmp_dir=tmp_dir,
        )
        test = self.test
        for step, p in enumerate(self._passes()):
            test = p.run(ctx, test, step=step)

        final_path = self.output_dir / FINAL_REDUCED_NAME
        shutil.copy2(test.test_path, final_path)
        return Test(final_path, test.interesting, test.file, test.line)
