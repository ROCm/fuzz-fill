import dataclasses
from pathlib import Path

@dataclasses.dataclass
class Filepaths:
    output_dir: Path
    output_baseline_dir: Path | None   
    output_new_tests_dir: Path | None
    output_diff_dir: Path | None
    llvm_bin: Path | None
    instrumented_bin: Path | None
    new_tests_dir: Path | None
    llc_address_line_map_file: Path | None
    joint_llc_and_opt_coverage_file: Path | None
    new_coverage_csv: Path | None

    def __init__(self, output_dir: Path,
     output_baseline_dir: Path | None = None,
     output_new_tests_dir: Path | None = None,
     output_diff_dir: Path | None = None,
     llvm_bin: Path | None = None,
     instrumented_bin: Path | None = None,
     new_tests_dir: Path | None = None,
     llc_address_line_map_file: Path | None = None,
     joint_llc_and_opt_coverage_file: Path | None = None,
     new_coverage_csv: Path | None = None):
        self.output_dir = output_dir
        self.output_baseline_dir = output_baseline_dir
        self.output_new_tests_dir = output_new_tests_dir
        self.output_diff_dir = output_diff_dir
        self.llvm_bin = llvm_bin
        self.instrumented_bin = instrumented_bin
        self.new_tests_dir = new_tests_dir
        self.llc_address_line_map_file = llc_address_line_map_file
        self.joint_llc_and_opt_coverage_file = joint_llc_and_opt_coverage_file
        self.new_coverage_csv = new_coverage_csv