import csv

import pandas as pd
from pathlib import Path
from typing import Literal

from coverage.filepaths import Filepaths
from coverage.line_rules import (
    LineCoverageIndex,
    fully_covered_line_keys_from_address_map,
    normalize_llc_address_line_map,
)
from coverage.sancov import Sancov
from fuzz_fill.log import get_logger, log_timing

logger = get_logger("coverage.analyser")

class CoverageAnalyzer:
    def __init__(self, filepaths: Filepaths, mode: Literal["partial", "full"]):
        self.filepaths = filepaths
        self.mode = mode
        self.line_coverage_summary_file = (
            filepaths.output_baseline_dir / filepaths.line_coverage_summary_file
        )
        self.llc_address_line_map_file = filepaths.output_baseline_dir / filepaths.llc_address_line_map_file
        self.new_coverage_csv = filepaths.output_dir / filepaths.new_coverage_csv

    def get_incremental_coverage(self) -> None:
        if self.mode == "full":
            self.get_full_incremental_coverage()
        elif self.mode == "partial":
            raise NotImplementedError(f"Partial coverage mode is not implemented")
        else:
            raise ValueError(f"Invalid mode: {self.mode}")

    def get_full_incremental_coverage(self) -> None:
        with log_timing(logger, "incremental coverage analysis"):
            line_coverage_summary = pd.read_csv(self.line_coverage_summary_file)
            baseline_index = LineCoverageIndex.from_summary_df(line_coverage_summary)
            llc_address_line_map = normalize_llc_address_line_map(
                pd.read_csv(self.llc_address_line_map_file)
            )

            self.new_coverage_csv.parent.mkdir(parents=True, exist_ok=True)
            with self.new_coverage_csv.open("w", newline="", encoding="utf-8") as new_coverage_csv_f:
                csv.writer(new_coverage_csv_f).writerow(
                    ["test_name", "file", "line", "covered-points"]
                )

            sancov = Sancov(self.filepaths.sancov)

            # Keep track of lines that are newly covered by candidate tests
            # so that we avoid adding them to the new coverage csv multiple times
            newly_covered_lines = set()

            for candidate_test_dir in self.filepaths.output_candidate_tests_dir.iterdir():
                with log_timing(logger, f"candidate test {candidate_test_dir.name}"):
                    test_name = candidate_test_dir.name

                    sancov_file = get_sancov_file(candidate_test_dir)

                    if sancov_file is None:
                        continue

                    new_test_covered_addresses: set[str] = sancov.get_covered_addresses(sancov_file)

                    matched_addresses = llc_address_line_map[
                        llc_address_line_map["point_llc"].isin(new_test_covered_addresses)
                    ]

                    if len(matched_addresses) == 0:
                        logger.info(
                            "candidate test %s has no covered addresses "
                            "in files that we are interested in",
                            test_name,
                        )
                        continue

                    logger.info(
                        "candidate test %s has %d new covered addresses in target files",
                        test_name,
                        len(matched_addresses),
                    )

                    fully_covered_keys = fully_covered_line_keys_from_address_map(
                        llc_address_line_map, new_test_covered_addresses
                    )

                    if fully_covered_keys:
                        per_test_csv = test_name
                        keys = sorted(fully_covered_keys)

                        logger.info(
                            "candidate test %s has %d covered lines in target files",
                            test_name,
                            len(keys),
                        )

                        # Only lines the suite left completely uncovered count as new;
                        # partially covered baseline lines are excluded.
                        is_new_vs_baseline = [
                            baseline_index.is_baseline_gap(file, line) for file, line in keys
                        ]

                        is_new_vs_other_candidate_tests = [
                            (file, line) not in newly_covered_lines for file, line in keys
                        ]

                        mask = [
                            a and b
                            for a, b in zip(is_new_vs_baseline, is_new_vs_other_candidate_tests)
                        ]
                        accepted_keys = [key for key, keep in zip(keys, mask) if keep]

                        logger.info(
                            "%d lines are uncovered in baseline out of %d",
                            sum(is_new_vs_baseline),
                            len(keys),
                        )
                        logger.info(
                            "%d lines are new vs other candidate tests out of %d",
                            sum(is_new_vs_other_candidate_tests),
                            len(keys),
                        )

                        if not accepted_keys:
                            continue

                        newly_covered_lines.update(accepted_keys)
                        unique_locations = pd.DataFrame(accepted_keys, columns=["file", "line"])

                        keys_df = unique_locations[["file", "line"]]
                        sub = matched_addresses.merge(keys_df, on=["file", "line"], how="inner")
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
        logger.warning("expected 1 sancov file, got %d", len(sancov_files))
        return None
    return list(new_test_dir.rglob('*sancov'))[0]
