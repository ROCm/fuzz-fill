import csv

import pandas as pd
from pathlib import Path
from typing import Literal

from coverage.filepaths import Filepaths
from coverage.sancov import Sancov

class CoverageAnalyzer:
    def __init__(self, filepaths: Filepaths, mode: Literal["partial", "full"]):
        self.filepaths = filepaths
        self.mode = mode
        self.baseline_coverage_file = filepaths.output_test_suite_dir / filepaths.joint_llc_and_opt_coverage_file
        self.llc_address_line_map_file = filepaths.output_test_suite_dir / filepaths.llc_address_line_map_file
        self.new_coverage_csv = filepaths.output_dir / filepaths.new_coverage_csv

    def get_incremental_coverage(self) -> None:
        if self.mode == "full":
            self.get_full_incremental_coverage()
        elif self.mode == "partial":
            raise NotImplementedError(f"Partial coverage mode is not implemented")
        else:
            raise ValueError(f"Invalid mode: {self.mode}")

    def get_full_incremental_coverage(self) -> None:
        
        baseline_coverage = pd.read_csv(self.baseline_coverage_file)
        llc_address_line_map = pd.read_csv(self.llc_address_line_map_file)
        
        llc_address_line_map["line"] = llc_address_line_map["line"].astype(int)
        llc_address_line_map["point_llc"] = llc_address_line_map["point_llc"].map(lambda x: f"0x{x}" if pd.notna(x) else x)
        llc_address_line_map["file_line"] = llc_address_line_map["file"] + ":" + llc_address_line_map["line"].astype(str)

        baseline_covered_lines = {
            (file, int(line))
            for file, line in zip(baseline_coverage["file"], baseline_coverage["line"])
        }

        self.new_coverage_csv.parent.mkdir(parents=True, exist_ok=True)
        with self.new_coverage_csv.open("w", newline="", encoding="utf-8") as new_coverage_csv_f:
            csv.writer(new_coverage_csv_f).writerow(
                ["test_name", "file", "line", "covered-points"]
            )

        sancov = Sancov(self.filepaths.llvm_bin)

        # Keep track of lines that are newly covered by new tests
        # so that we avoid adding them to the new coverage csv multiple times
        newly_covered_lines = set()

        for new_test_dir in self.filepaths.output_new_tests_dir.iterdir():

            # Check whether any new addresses are covered
            test_name = new_test_dir.name

            sancov_file = get_sancov_file(new_test_dir)

            if sancov_file is None:
                continue

            new_test_covered_addresses: set[str] = sancov.get_covered_addresses(sancov_file)

            # Match newly covered addresses to llc line-address mapping to check
            # whether they are in files that we are interested in
            new_coverage_df = llc_address_line_map[llc_address_line_map['point_llc'].isin(new_test_covered_addresses)].copy()

            if len(new_coverage_df) == 0:
                print(f"New test {test_name} has no covered addresses in files that we are interested in")
                continue
            
            print(f"New test {test_name} has {len(new_coverage_df)} new covered addresses in target files")

            # Rows where every point on the line is hit by this test.
            hit_df = new_coverage_df.copy()
            hit_df["covered"] = 1
            fully_covered = Sancov.full_line_keys(hit_df, covered_column="covered")
            if fully_covered:
                keys_df = pd.DataFrame(list(fully_covered), columns=["file", "line"])
                keys_df["line"] = keys_df["line"].astype(int)
                new_test_covered_lines = new_coverage_df.merge(
                    keys_df, on=["file", "line"], how="inner"
                )
            else:
                new_test_covered_lines = new_coverage_df.iloc[0:0]

            if len(new_test_covered_lines) > 0:

                per_test_csv = test_name
                unique_locations = new_test_covered_lines[["file", "line"]].drop_duplicates()
                
                print(f"New test {test_name} has {len(unique_locations)} covered lines in target files")
                keys = [
                    (file, int(line))
                    for file, line in zip(unique_locations["file"], unique_locations["line"])
                ]
                unique_locations = unique_locations.copy()
                unique_locations["line"] = unique_locations["line"].astype(int)

                # Compare new line coverage to baseline line coverage
                # It is important to do this at the line level rather than the address level
                # when working with full coverage
                is_new_vs_baseline = [key not in baseline_covered_lines for key in keys]

                # Compare to lines already covered by other new tests
                is_new_vs_other_new_tests = [key not in newly_covered_lines for key in keys]

                # Keep only lines that are new vs baseline and new vs other new tests
                mask = [a and b for a, b in zip(is_new_vs_baseline, is_new_vs_other_new_tests)]
                unique_locations = unique_locations.loc[mask]

                print(f"{sum(is_new_vs_baseline)} lines are new vs baseline out of {len(keys)}")
                print(f"{sum(is_new_vs_other_new_tests)} lines are new vs other new tests out of {len(keys)}")

                if unique_locations.empty:
                    continue

                newly_covered_lines.update(
                    zip(unique_locations["file"], unique_locations["line"])
                )

                keys_df = unique_locations[["file", "line"]]
                sub = new_test_covered_lines.merge(keys_df, on=["file", "line"], how="inner")
                addr_by_line = sub.groupby(["file", "line"], sort=False)["point_llc"].agg(
                    lambda s: ";".join(sorted(s.dropna().astype(str).unique()))
                )

                with self.new_coverage_csv.open("a", newline="", encoding="utf-8") as new_coverage_csv_f:
                    writer = csv.writer(new_coverage_csv_f)
                    for _, row in unique_locations.iterrows():
                        addrs = addr_by_line.loc[row["file"], row["line"]]
                        writer.writerow([per_test_csv, row["file"], row["line"], addrs])

def get_sancov_file(new_test_dir: Path) -> Path | None:
    """Get the llc sancov file for a new test. Checks that there is only one sancov file and throws an error if there are multiple."""
    sancov_files = list(new_test_dir.rglob('llc.*.sancov'))
    if len(sancov_files) != 1:
        print(f"Expected 1 sancov file, got {len(sancov_files)}")
        return None
    return list(new_test_dir.rglob('*sancov'))[0]