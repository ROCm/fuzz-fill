"""SanitizerCoverage merge, symbolize, and stats via llvm sancov."""

from __future__ import annotations

from calendar import c
import shutil
import subprocess
import tempfile
import pandas as pd
from pathlib import Path

class Sancov:
    """Drive llvm ``sancov`` for one build tree (``build/.../bin``)."""

    def __init__(
        self,
        bin_dir: Path,
        instrumented_bin: Path,
        raw_sancov_dir: Path,
        suffix: str,
        union_batch: int = 200,
    ) -> None:
        self.sancov_bin = Path(bin_dir, "sancov")
        self.instrumented_bin = instrumented_bin
        self.union_batch = union_batch
        self.raw_sancov_dir = raw_sancov_dir
        self.suffix = suffix

        self.output_dir = self.raw_sancov_dir.parent / f"processed_sancov"

        self.output_dir.mkdir(parents=True, exist_ok=True)

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

        print(f"Symbolizing {sancov_path} with {self.instrumented_bin}")
        
        cmd = [str(self.sancov_bin), "-symbolize", str(sancov_path), str(self.instrumented_bin)]

        with symcov_path.open("w") as f:
            subprocess.run(cmd, check=True, stdout=f, stderr=subprocess.STDOUT)

    def get_joint_coverage(self, other: Sancov, path_filter: str | None = None) -> pd.DataFrame:
        """
            Get the joint coverage for this Sancov instance and the other Sancov instance.
            The joint coverage is based on *this* instance's mapping from addresses to source locations.
        """

        # Load symcov data, filtered for the source code paths of interest.
        this_df = pd.read_csv(self.get_merged_symcov_path())

        if path_filter is not None:
            this_df = this_df[this_df["file"].str.contains(path_filter)]

        other_df = pd.read_csv(other.get_merged_symcov_path())
        if path_filter is not None:
            other_df = other_df[other_df["file"].str.contains(path_filter)]

        # Map other instance's covered source locations to this instance's addresses.


        print(this_df.head())
        print(other_df.head())
        exit()
        address_map = self.get_address_map()
        other_df["address"] = other_df["point_id"].map(address_map)
        other_df["address"] = other_df["address"].astype(int)
        other_df["address"] = other_df["address"].apply(lambda x: f"{x:x}")
        other_df["address"] = other_df["address"].apply(lambda x: f"0x{x}")
        other_df["address"] = other_df["address"].apply(lambda x: f"0x{x}")

        # Merge the two dataframes on the address column.
        joint_df = this_df.merge(other_df, on="address", how="left")
        return joint_df

    def get_address_map(self) -> dict[str, int]:
        """
            Get the address map for this Sancov instance.
            The address map is a dictionary of addresses to source locations.
        """
        df = pd.read_csv(self.get_merged_symcov_path())
        address_map = df["point_id"].to_dict()
        return address_map
