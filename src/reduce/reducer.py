from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from reduce.pass_registry import known_pass_ids, passes_from_ids
from reduce.test import Test


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
    extract_ir_before_output: str | None
    interesting_mir: Path | None


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
        extract_ir_before_output: str | None = None,
        interesting_mir: Path | None = None,
    ):
        self.llvm_bin: Path = llvm_bin
        self.output_dir: Path = output_dir
        self.test: Test = test
        self._pass_under_test: str | None = pass_under_test
        self._mtriple: str | None = mtriple
        self._llc_O: str | None = llc_O
        self._extract_mir_output: str | None = extract_mir_output
        self._extract_ir_before_output: str | None = extract_ir_before_output
        self._interesting_mir: Path | None = interesting_mir
        self._pass_ids: list[str] = list(pass_ids)
        self._passes_list = passes_from_ids(pass_ids)

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
            extract_ir_before_output=self._extract_ir_before_output,
            interesting_mir=self._interesting_mir,
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
