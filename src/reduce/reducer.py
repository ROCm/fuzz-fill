from pathlib import Path

class Test:
    def __init__(self, test_path: Path, interesting: Path, line: int):
        self.test_path: Path = test_path
        self.interesting: Path = interesting
        self.line: int = line

    def run(self):
        pass

    def get_coverage(self):
        pass

class Reducer:
    def __init__(self, llvm_bin: Path, output_dir: Path, tests: list[Test]):    
        self.llvm_bin: Path = llvm_bin
        self.output_dir: Path = output_dir
        self.tests: list[Test] = tests

    def reduce(self):
        pass

