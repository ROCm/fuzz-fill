"""SanitizerCoverage merge, symbolize, and stats via llvm sancov."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import json
import pandas as pd
import numpy as np
from pathlib import Path

from cov_new.constants import DEFAULT_PATH_FILTER
from typing import Literal

class Sancov:

    def __init__(
        self,
        bin_dir: Path,
        instrumented_bin: Path,
        raw_sancov_dir: Path,
        suffix: str,
        coverage_mode: Literal["partial", "full"] = "full",
        union_batch: int = 200,
    ) -> None:
        self.sancov_bin = Path(bin_dir, "sancov")
        self.instrumented_bin = instrumented_bin
        self.union_batch = union_batch
        self.raw_sancov_dir = raw_sancov_dir
        self.suffix = suffix
        self.coverage_mode = coverage_mode
        self.output_dir = self.raw_sancov_dir.parent / f"processed_sancov"

        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_coverage_df(symcov: dict[str, object], path_filter: str) -> pd.DataFrame:
        """Get the coverage information in a dataframe.
            The symcov file is a dictionary with the following keys:
            - point-symbol-info: a dictionary of point-symbol-info
            - covered-points: a list of covered points
            The point-symbol-info is a dictionary of point-symbol-info with the following structure:
            - keys: filepaths of the source code
            - values: a dictionary of structure:
                - keys: function names
                - values: a dictionary of structure:
                    - keys: point-ids in hex format
                    - values: the line numbers and column numbers of the source code
            The covered-points is a list of covered point-ids in hex format
        """
        point_symbol_info = symcov.get("point-symbol-info")
        point_symbol_info = {k: v for k, v in point_symbol_info.items() if path_filter in k}

        covered_points = symcov.get("covered-points")

        # Flatten point_symbol_info           
        flattened_point_symbol_info = {f"{file}": addr_to_line for file, func_info in point_symbol_info.items() for func, addr_to_line in func_info.items()}
        point_to_line = [(file, line, point) for file, inner in flattened_point_symbol_info.items() for point, line in inner.items()]

        # Create coverage dataframe
        df = pd.DataFrame(point_to_line, columns=["file", "line", "point"])
        df[["line", "col"]] = df["line"].str.split(":", n=1, expand=True)
        df["covered"] = df["point"].isin(covered_points).astype(int)

        return df

    @staticmethod
    def get_coverage_summary_df(df: pd.DataFrame) -> pd.DataFrame:
        """Get the coverage summary dataframe."""
        agg = (
            df.groupby(["file", "line"], as_index=False)
            .agg(n_covered=("covered_either", "sum"), n_points=("covered_either", "count"))
        )

        agg["coverage"] = np.where(
            agg["n_covered"] == 0,
            "none",
            np.where(agg["n_covered"] == agg["n_points"], "full", "partial"),
        )

        agg = agg.drop(columns=["n_covered", "n_points"])
        cov_df = agg.merge(df, on=["file", "line"], how="left")
        return cov_df[["file", "line", "coverage", "point_this"]]
    
    def get_merged_sancov_path(self) -> Path:
        return self.output_dir / f"{self.suffix}.0.sancov"

    def get_merged_symcov_path(self) -> Path:
        return self.output_dir / f"{self.suffix}.0.symcov"

    def merge(self) -> None:
        """Merge the sancov files for the given suffix."""

        merged_out = self.get_merged_sancov_path()

        raw_files = list(self.raw_sancov_dir.glob(f"{self.suffix}.*.sancov"))
        if not raw_files:
            raise FileNotFoundError(f"No sancov files found for suffix: {self.suffix}")

        """Merge raw ``.sancov`` files with repeated ``sancov -union`` (batched)."""
        if len(raw_files) == 1:
            shutil.copy(raw_files[0], merged_out)
            return

        sancov = self.sancov_bin
        batch = self.union_batch
        layer = list(raw_files)
        with tempfile.TemporaryDirectory(dir=merged_out.parent) as tmp:
            tmp_path = Path(tmp)
            round_idx = 0
            while len(layer) > 1:
                nxt: list[Path] = []
                for i in range(0, len(layer), batch):
                    chunk = layer[i : i + batch]
                    if len(chunk) == 1:
                        nxt.append(chunk[0])
                        continue
                    out_f = tmp_path / f"u_{round_idx}_{len(nxt)}.sancov"
                    subprocess.run(
                        [str(sancov), "-union"]
                        + [str(p) for p in chunk]
                        + ["--output", str(out_f)],
                        check=True,
                    )
                    nxt.append(out_f)
                layer = nxt
                round_idx += 1
            shutil.copy(layer[0], merged_out)
    
    def symbolize(
        self,
        sancov_path: Path,
        symcov_path: Path
    ) -> None:

        if symcov_path.exists():
            print(f"Symcov file already exists at {symcov_path}, skipping symbolization")
            return

        print(f"Symbolizing {sancov_path} with {self.instrumented_bin}")
        
        cmd = [str(self.sancov_bin), "-symbolize", str(sancov_path), str(self.instrumented_bin)]

        with symcov_path.open("w") as f:
            subprocess.run(cmd, check=True, stdout=f, stderr=subprocess.STDOUT)

    def get_joint_coverage(self, other: Sancov, path_filter: str = DEFAULT_PATH_FILTER) -> pd.DataFrame:
        """
        Joint coverage: rows from *this* symcov's ``point-symbol-info`` (hex ``address`` per point)
        restricted to ``(file, function, line)`` that also appear in ``other``'s covered locations.

        Returns a long table with columns ``file``, ``function``, ``line``, ``address``.
        """
        with self.get_merged_symcov_path().open(encoding="utf-8") as f:
            this_symcov = json.load(f)

        with other.get_merged_symcov_path().open(encoding="utf-8") as f:
            other_symcov = json.load(f)

        this_df = self.get_coverage_df(this_symcov, path_filter)
        other_df = self.get_coverage_df(other_symcov, path_filter)

        this_address_line_map = this_df[["file", "line", "point"]].copy()
        this_address_line_map["point"].astype(str)
        this_address_line_map.rename(columns={"point": f"point_{self.suffix}"}, inplace=True)

        # Get joint coverage dataframe
        joint_df = this_df.merge(other_df, on=["file", "line", "col"], how="inner", suffixes=("_this", "_other"))

        joint_df["covered_either"] = joint_df["covered_this"] | joint_df["covered_other"]

        if self.coverage_mode == "full":
            joint_df =joint_df.drop(columns=["col", "covered_other", "covered_this", "point_other"])
            cov_summary_df = self.get_coverage_summary_df(joint_df)
            fully_covered_df = cov_summary_df[cov_summary_df["coverage"] == "full"].copy()
            fully_covered_df.rename(columns={"point_this": f"point_{self.suffix}"}, inplace=True)
            return (this_address_line_map, fully_covered_df)
        
        elif self.coverage_mode == "partial":
            raise NotImplementedError(f"Coverage mode {self.coverage_mode} not implemented")  