from pathlib import Path
import json

class Test:
    def __init__(self, test_path: Path, interesting: Path, line: int, symcov: Path):
        self.test_path: Path = test_path
        self.interesting: Path = interesting
        self.line: int = line
        self.symcov: Path = symcov

    def run(self):
        pass

    def get_coverage(self):
        pass

    def get_interesting_address(self) -> str:
        with open(self.symcov, 'r') as f:
            coverage_data = json.load(f)

        print(coverage_data.keys())

