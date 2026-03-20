import shutil
from pathlib import Path

from reduce.test import Test

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

    def reduce(self):
        dest = self.output_dir / "reduced.ll"
        shutil.copy2(self.test.test_path, dest)

