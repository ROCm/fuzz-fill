"""SanitizerCoverage merge, symbolize, and stats via llvm sancov."""

from __future__ import annotations

import dataclasses
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from coverage.constants import DEFAULT_LIT_FILTER, UNION_BATCH_SIZE
from coverage.run_config import path_filter_from_lit_filter


@dataclasses.dataclass(frozen=True)
class JointCoverageView:
    """Joint llc/opt symcov analysis for a filtered test-suite run."""

    merged_cov: pd.DataFrame
    this_df: pd.DataFrame
    other_df: pd.DataFrame
    line_status: dict[tuple[str, int], Literal["full", "partial", "none"]]
    instrumented_lines: set[tuple[str, int]]
    symcov_files: set[str]
    point_addresses_by_line: dict[tuple[str, int], list[str]]

    @property
    def fully_covered_lines(self) -> set[tuple[str, int]]:
        return {k for k, v in self.line_status.items() if v == "full"}

    @property
    def all_uncovered_lines(self) -> set[tuple[str, int]]:
        return {k for k, v in self.line_status.items() if v == "none"}


class Sancov:

    def __init__(
        self,
        bin_dir: Path,
        instrumented_bin: Path | None = None,
        raw_sancov_dir: Path | None = None,
        suffix: str | None = None,
        coverage_mode: Literal["partial", "full"] = "full",
        union_batch: int = UNION_BATCH_SIZE,
    ) -> None:
        self.sancov_bin = Path(bin_dir, "sancov")
        self.instrumented_bin = instrumented_bin
        self.union_batch = union_batch
        self.raw_sancov_dir = raw_sancov_dir
        self.suffix = suffix
        self.coverage_mode = coverage_mode

        if self.raw_sancov_dir is not None:
            self.output_dir = self.raw_sancov_dir.parent / f"processed_sancov"
            self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def flatten_point_symbol_info(point_symbol_info: dict[str, object]) -> pd.DataFrame:
        """Flatten the point-symbol-info dictionary into a dataframe."""
        rows = ((file, addr_to_line) for file, d1 in point_symbol_info.items() for fun, addr_to_line in d1.items())
        df = pd.DataFrame.from_records(rows, columns=["file", "addr_to_line"])

        files, addrs, lines = [], [], []
        for t in df.itertuples(index=False):
            f = t.file
            for a, ln in t.addr_to_line.items():
                files.append(f)
                addrs.append(a)
                lines.append(ln)

        out = pd.DataFrame({"file": files, "point": addrs, "line": lines})
        out[["line", "col"]] = out["line"].str.split(":", n=1, expand=True)

        return out

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

        df = Sancov.flatten_point_symbol_info(point_symbol_info)

        covered_points = symcov.get("covered-points")

        # Create coverage dataframe
        df["covered"] = df["point"].isin(covered_points).astype(int)

        return df

    @staticmethod
    def full_line_keys(
        df: pd.DataFrame, *, covered_column: str = "covered"
    ) -> set[tuple[str, int]]:
        """``(file, line)`` pairs where every instrumentation point row in *df* is covered."""
        line_df = df.copy()
        line_df["line"] = line_df["line"].astype(int)
        agg = (
            line_df.groupby(["file", "line"], as_index=False)
            .agg(
                n_covered=(covered_column, "sum"),
                n_points=(covered_column, "count"),
            )
        )
        full = agg[agg["n_covered"] == agg["n_points"]]
        return set(zip(full["file"], full["line"]))

    @staticmethod
    def merged_llc_opt_coverage_df(
        this_df: pd.DataFrame, other_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Outer-merge llc and opt coverage rows on ``(file, line, col)`` with ``covered_either``."""
        this_df = this_df.copy()
        this_df["line"] = this_df["line"].astype(int)
        other_df = other_df.copy()
        other_df["line"] = other_df["line"].astype(int)
        merged = this_df.merge(
            other_df,
            on=["file", "line", "col"],
            how="outer",
            suffixes=("_this", "_other"),
        )
        merged["covered_either"] = (
            merged["covered_this"].fillna(0).astype(int)
            | merged["covered_other"].fillna(0).astype(int)
        )
        return merged

    @staticmethod
    def line_status_from_merged(
        merged: pd.DataFrame,
    ) -> dict[tuple[str, int], Literal["full", "partial", "none"]]:
        """Per ``(file, line)`` coverage status from a llc/opt merged DataFrame."""
        m = merged.copy()
        m["line"] = m["line"].astype(int)
        agg = (
            m.groupby(["file", "line"], as_index=False)
            .agg(
                n_covered=("covered_either", "sum"),
                n_points=("covered_either", "count"),
            )
        )
        status: dict[tuple[str, int], Literal["full", "partial", "none"]] = {}
        for row in agg.itertuples(index=False):
            if row.n_covered == 0:
                cov: Literal["full", "partial", "none"] = "none"
            elif row.n_covered == row.n_points:
                cov = "full"
            else:
                cov = "partial"
            status[(row.file, int(row.line))] = cov
        return status

    @staticmethod
    def point_addresses_by_line_from_merged(
        merged: pd.DataFrame,
        line_keys: set[tuple[str, int]] | None = None,
    ) -> dict[tuple[str, int], list[str]]:
        """Distinct sanitizer point ids (``point_this`` / ``point_other``) per line."""
        if line_keys is None:
            m = merged.copy()
            m["line"] = m["line"].astype(int)
            line_keys = set(zip(m["file"], m["line"]))
        return Sancov._point_addresses_for_lines(merged, line_keys)

    @staticmethod
    def _point_addresses_for_lines(
        merged: pd.DataFrame,
        line_keys: set[tuple[str, int]],
    ) -> dict[tuple[str, int], list[str]]:
        if not line_keys:
            return {}
        m = merged.copy()
        m["line"] = m["line"].astype(int)
        out: dict[tuple[str, int], list[str]] = {}
        for f, ln in line_keys:
            sub = m[(m["file"] == f) & (m["line"] == ln)]
            ordered: list[str] = []
            seen: set[str] = set()
            for _, row in sub.iterrows():
                for col in ("point_this", "point_other"):
                    if col not in row.index:
                        continue
                    v = row[col]
                    if pd.isna(v):
                        continue
                    s = str(v).strip()
                    if not s or s in seen:
                        continue
                    seen.add(s)
                    ordered.append(s)
            out[(f, ln)] = ordered
        return out

    @staticmethod
    def all_uncovered_line_point_addresses(
        merged: pd.DataFrame,
        line_keys: set[tuple[str, int]],
    ) -> dict[tuple[str, int], list[str]]:
        """Distinct sanitizer point ids for *line_keys* (typically all-uncovered lines)."""
        return Sancov._point_addresses_for_lines(merged, line_keys)

    @staticmethod
    def symcov_paths(test_suite_output_dir: Path) -> tuple[Path, Path]:
        base = test_suite_output_dir / "processed_sancov"
        return base / "llc.0.symcov", base / "opt.0.symcov"

    @classmethod
    def load_joint_coverage(
        cls,
        llc_symcov_path: Path,
        opt_symcov_path: Path,
        path_filter: str,
    ) -> JointCoverageView:
        with llc_symcov_path.open(encoding="utf-8") as f:
            llc_symcov = json.load(f)
        with opt_symcov_path.open(encoding="utf-8") as f:
            opt_symcov = json.load(f)

        this_df = cls.get_coverage_df(llc_symcov, path_filter)
        other_df = cls.get_coverage_df(opt_symcov, path_filter)
        merged_cov = cls.merged_llc_opt_coverage_df(this_df, other_df)
        line_status = cls.line_status_from_merged(merged_cov)
        instrumented_lines = set(line_status.keys())
        symcov_files = set(this_df["file"].unique()) | set(other_df["file"].unique())
        uncovered = {k for k, v in line_status.items() if v == "none"}
        point_addresses = cls._point_addresses_for_lines(merged_cov, uncovered)

        return JointCoverageView(
            merged_cov=merged_cov,
            this_df=this_df,
            other_df=other_df,
            line_status=line_status,
            instrumented_lines=instrumented_lines,
            symcov_files=symcov_files,
            point_addresses_by_line=point_addresses,
        )

    @classmethod
    def load_joint_coverage_from_suite_dir(
        cls,
        test_suite_output_dir: Path,
        path_filter: str,
    ) -> JointCoverageView:
        llc_path, opt_path = cls.symcov_paths(test_suite_output_dir)
        if not llc_path.is_file():
            raise SystemExit(
                f"Missing {llc_path}. Run ``coverage test-suite`` first (or pass the same "
                f"--output-dir you used for that run as --test-suite-output-dir)."
            )
        if not opt_path.is_file():
            raise SystemExit(
                f"Missing {opt_path}. Run ``coverage test-suite`` first so llc and opt symcov exist."
            )
        return cls.load_joint_coverage(llc_path, opt_path, path_filter)

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

    def get_covered_addresses(self, sancov_file: Path) -> set[str]:
        """Get the covered addresses from a sancov file."""
        try:
            proc = subprocess.run(
                [str(self.sancov_bin), "--print", str(sancov_file)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or "").strip()
            raise RuntimeError(
                f"sancov --print failed for {sancov_file}: {err or e}"
            ) from e
        return {line.strip() for line in proc.stdout.splitlines() if line.strip()}

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

    def get_joint_coverage(
        self,
        other: Sancov,
        path_filter: str | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Build the LLC address map and baseline covered lines for *this* (llc) vs *other* (opt).

        A baseline line is one where every instrumentation point on that line is covered
        by llc and/or opt. Points are matched on ``(file, line, col)``; when both tools
        instrument the same site, either tool hitting it counts. Ll-only and opt-only
        points on the line are included as well.

        Returns ``(llc_address_line_map, baseline_coverage)`` with columns
        ``file``, ``line``, ``point_<suffix>`` on the map and ``file``, ``line``,
        ``point_<suffix>`` on baseline rows (one row per instrumented point).
        """
        if path_filter is None:
            path_filter = path_filter_from_lit_filter(DEFAULT_LIT_FILTER)

        view = Sancov.load_joint_coverage(
            self.get_merged_symcov_path(),
            other.get_merged_symcov_path(),
            path_filter,
        )
        this_df = view.this_df
        other_df = view.other_df

        this_address_line_map = this_df[["file", "line", "point"]].copy()
        this_address_line_map["line"] = this_address_line_map["line"].astype(int)
        this_address_line_map.rename(columns={"point": f"point_{self.suffix}"}, inplace=True)

        if self.coverage_mode == "full":
            baseline_lines = view.fully_covered_lines
            baseline_lines_df = pd.DataFrame(
                list(baseline_lines), columns=["file", "line"]
            )

            this_df_merge = this_df.copy()
            this_df_merge["line"] = this_df_merge["line"].astype(int)
            other_df_merge = other_df.copy()
            other_df_merge["line"] = other_df_merge["line"].astype(int)

            llc_baseline = this_df_merge.merge(
                baseline_lines_df, on=["file", "line"], how="inner"
            )
            llc_instrumented_lines = set(zip(this_df_merge["file"], this_df_merge["line"]))
            opt_only_lines = baseline_lines - llc_instrumented_lines
            opt_only_df = pd.DataFrame(list(opt_only_lines), columns=["file", "line"])
            opt_baseline = other_df_merge.merge(
                opt_only_df, on=["file", "line"], how="inner"
            )

            point_col = f"point_{self.suffix}"
            baseline_coverage = pd.concat(
                [
                    llc_baseline[["file", "line", "point"]].rename(
                        columns={"point": point_col}
                    ),
                    opt_baseline[["file", "line", "point"]].rename(
                        columns={"point": point_col}
                    ),
                ],
                ignore_index=True,
            )
            return (this_address_line_map, baseline_coverage)

        elif self.coverage_mode == "partial":
            raise NotImplementedError(f"Coverage mode {self.coverage_mode} not implemented")