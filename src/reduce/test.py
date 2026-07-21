from pathlib import Path
import json


class Test:
    def __init__(
        self,
        test_path: Path,
        interesting: Path | None,
        file: str,
        line: int,
    ):
        self.test_path: Path = test_path
        self.interesting: Path = interesting
        self.file: str = file
        self.line: int = line


