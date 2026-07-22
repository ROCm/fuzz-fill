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
    llc_address_line_map_csv: Path | None
    llc_address_line_map_file: Path | None
    opt_address_line_map_file: Path | None
    llc_line_point_summary_file: Path | None
    opt_line_point_summary_file: Path | None
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
     llc_address_line_map_csv: Path | None = None,
     llc_address_line_map_file: Path | None = None,
     opt_address_line_map_file: Path | None = None,
     llc_line_point_summary_file: Path | None = None,
     opt_line_point_summary_file: Path | None = None,
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
        self.llc_address_line_map_csv = llc_address_line_map_csv
        self.llc_address_line_map_file = llc_address_line_map_file
        self.opt_address_line_map_file = opt_address_line_map_file
        self.llc_line_point_summary_file = llc_line_point_summary_file
        self.opt_line_point_summary_file = opt_line_point_summary_file
        self.line_coverage_summary_file = line_coverage_summary_file
        self.new_coverage_csv = new_coverage_csv
