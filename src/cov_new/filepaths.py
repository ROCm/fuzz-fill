import dataclasses
from pathlib import Path

@dataclasses.dataclass
class Filepaths:
    output_dir: Path
    llvm_project: Path | None
    build_dir: Path | None
    new_tests_dir: Path | None
    baseline_csv: Path | None

    def __post_init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
