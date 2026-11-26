import dataclasses
from pathlib import Path

@dataclasses.dataclass
class Filepaths:
    output_dir: Path
    output_candidate_tests_dir: Path | None
    sancov: Path | None
    llvm_lit: Path | None
    llc: Path | None
    opt: Path | None
    candidate_tests_dir: Path | None
    line_coverage_uncovered_csv: Path | None
    address_line_map_csv: Path | None
    line_coverage_summary_file: Path | None
    new_coverage_csv: Path | None

    def __init__(self, output_dir: Path,
     output_candidate_tests_dir: Path | None = None,
     sancov: Path | None = None,
     llvm_lit: Path | None = None,
     llc: Path | None = None,
     opt: Path | None = None,
     candidate_tests_dir: Path | None = None,
     line_coverage_uncovered_csv: Path | None = None,
     address_line_map_csv: Path | None = None,
     # Back-compat for older call sites during rename.
     llc_address_line_map_csv: Path | None = None,
     line_coverage_summary_file: Path | None = None,
     new_coverage_csv: Path | None = None):
        self.output_dir = output_dir
        self.output_candidate_tests_dir = output_candidate_tests_dir
        self.sancov = sancov
        self.llvm_lit = llvm_lit
        self.llc = llc
        self.opt = opt
        self.candidate_tests_dir = candidate_tests_dir
        self.line_coverage_uncovered_csv = line_coverage_uncovered_csv
        self.address_line_map_csv = (
            address_line_map_csv
            if address_line_map_csv is not None
            else llc_address_line_map_csv
        )
        self.line_coverage_summary_file = line_coverage_summary_file
        self.new_coverage_csv = new_coverage_csv

    @property
    def llc_address_line_map_csv(self) -> Path | None:
        return self.address_line_map_csv

    @llc_address_line_map_csv.setter
    def llc_address_line_map_csv(self, value: Path | None) -> None:
        self.address_line_map_csv = value
