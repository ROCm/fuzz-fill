from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from reduce.test import Test


@dataclass(frozen=True)
class ReduceContext:
    llvm_bin: Path
    output_dir: Path


class ReducePass(ABC):
    """One step in the pipeline; returns the test state for the next pass."""

    @abstractmethod
    def run(self, ctx: ReduceContext, test: Test) -> Test:
        raise NotImplementedError


class SnapshotPass(ReducePass):
    """Stage the current IR into the output directory (baseline for later reduction)."""

    def run(self, ctx: ReduceContext, test: Test) -> Test:
        dest = ctx.output_dir / "reduced.ll"
        shutil.copy2(test.test_path, dest)
        return Test(dest, test.interesting, test.file, test.line)


class ExampleTransformPass(ReducePass):
    """
    Template pass: no-op until you add logic.

    Typical pattern: read ``test.test_path``, write a new file under ``ctx.output_dir``,
    then return ``Test(new_path, test.interesting, test.file, test.line)``.
    """

    def run(self, ctx: ReduceContext, test: Test) -> Test:
        _ = ctx  # e.g. subprocess.run([ctx.llvm_bin / "opt", ...], ...)
        return test


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
        ctx = ReduceContext(llvm_bin=self.llvm_bin, output_dir=self.output_dir)
        test = self.test
        for p in self._passes():
            test = p.run(ctx, test)
        return test
