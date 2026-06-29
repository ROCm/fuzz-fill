import dataclasses
from pathlib import Path

@dataclasses.dataclass
class Filepaths:
    output_dir: Path
    output_test_suite_dir: Path | None = None
    output_new_tests_dir: Path | None = None
    output_diff_dir: Path | None = None
    llvm_bin: Path | None = None
    instrumented_bin: Path | None = None
    new_tests_dir: Path | None = None
    llc_address_line_map_file: Path | None = None
    joint_llc_and_opt_coverage_file: Path | None = None
    new_coverage_csv: Path | None = None
    target_lines_csv: Path | None = None
    target_lines_report: str | None = None