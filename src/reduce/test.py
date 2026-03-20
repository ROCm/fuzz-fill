from pathlib import Path
import json

class Test:
    def __init__(self, test_path: Path, interesting: Path, file: str, line: int, symcov: Path):
        self.test_path: Path = test_path
        self.interesting: Path = interesting
        self.file: str = file
        self.line: int = line

    def run(self):
        pass

    def get_coverage(self):
        pass


