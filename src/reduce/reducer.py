from pathlib import Path

from reduce.test import Test

class Reducer:
    def __init__(self, llvm_bin: Path, output_dir: Path, tests: list[Test]):    
        self.llvm_bin: Path = llvm_bin
        self.output_dir: Path = output_dir
        self.tests: list[Test] = tests

    def reduce(self):
        pass

