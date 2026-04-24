import dataclasses
from pathlib import Path

@dataclasses.dataclass
class Filepaths:
    output_dir: Path
    output_test_suite_dir: Path | None   
    output_new_tests_dir: Path | None
    output_diff_dir: Path | None
    llvm_bin: Path | None
    instrumented_bin: Path | None
    new_tests_dir: Path | None

    def __init__(self, output_dir: Path,
     output_test_suite_dir: Path | None = None,
     output_new_tests_dir: Path | None = None,
     output_diff_dir: Path | None = None,
     llvm_bin: Path | None = None,
     instrumented_bin: Path | None = None,
     new_tests_dir: Path | None = None):
        self.output_dir = output_dir
        self.output_test_suite_dir = output_test_suite_dir
        self.output_new_tests_dir = output_new_tests_dir
        self.output_diff_dir = output_diff_dir
        self.llvm_bin = llvm_bin
        self.instrumented_bin = instrumented_bin
        self.new_tests_dir = new_tests_dir