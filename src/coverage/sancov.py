"""SanitizerCoverage merge, symbolize, and stats via llvm sancov."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import json
import pandas as pd
import numpy as np
from pathlib import Path

from coverage.constants import DEFAULT_LIT_FILTER
from coverage.run_config import path_filter_from_lit_filter
from fuzz_fill.log import get_logger, log_timing, run_subprocess
from typing import Literal

logger = get_logger("coverage.sancov")

class Sancov:

    @staticmethod
    def format_hex_address(addr: object) -> str:
        """Normalize a SanitizerCoverage point id to ``0x`` + lowercase hex."""
        s = str(addr).strip()
        if s.lower().startswith("0x"):
            s = s[2:]
        if not s:
            raise ValueError(f"empty sanitizer coverage point id: {addr!r}")
        int(s, 16)
        return f"0x{s.lower()}"

    def __init__(
        self,
        bin_dir: Path,
        instrumented_bin: Path | None = None,
        raw_sancov_dir: Path | None = None,
        suffix: str | None = None,
        coverage_mode: Literal["partial", "full"] = "full",
        union_batch: int = 200,
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

        out = pd.DataFrame({"file": files, "point": addrs, "line": lines}, dtype=object)
        out[["line", "col"]] = (
            out["line"].str.split(":", n=1, expand=True).reindex(columns=[0, 1])
        )
        if not out.empty:
            out["point"] = out["point"].map(Sancov.format_hex_address)

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

        covered_points = {
            Sancov.format_hex_address(p)
            for p in (symcov.get("covered-points") or [])
        }

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
    def jointly_fully_covered_line_keys_from_merged(
        merged: pd.DataFrame,
    ) -> set[tuple[str, int]]:
        """``(file, line)`` where every merged row has ``covered_either`` set."""
        return Sancov.full_line_keys(merged, covered_column="covered_either")

    @staticmethod
    def jointly_all_points_uncovered_line_keys_from_merged(
        merged: pd.DataFrame,
    ) -> set[tuple[str, int]]:
        """``(file, line)`` where no merged row has ``covered_either`` set."""
        agg = (
            merged.groupby(["file", "line"], as_index=False)
            .agg(
                n_covered=("covered_either", "sum"),
                n_points=("covered_either", "count"),
            )
        )
        none_hit = agg[(agg["n_covered"] == 0) & (agg["n_points"] > 0)]
        return set(zip(none_hit["file"], none_hit["line"]))

    @staticmethod
    def jointly_fully_covered_line_keys_from_llc_opt_dfs(
        this_df: pd.DataFrame, other_df: pd.DataFrame
    ) -> set[tuple[str, int]]:
        merged = Sancov.merged_llc_opt_coverage_df(this_df, other_df)
        return Sancov.jointly_fully_covered_line_keys_from_merged(merged)

    @staticmethod
    def jointly_all_points_uncovered_line_keys_from_llc_opt_dfs(
        this_df: pd.DataFrame, other_df: pd.DataFrame
    ) -> set[tuple[str, int]]:
        merged = Sancov.merged_llc_opt_coverage_df(this_df, other_df)
        return Sancov.jointly_all_points_uncovered_line_keys_from_merged(merged)

    @staticmethod
    def all_uncovered_line_point_addresses(
        merged: pd.DataFrame,
        line_keys: set[tuple[str, int]],
    ) -> dict[tuple[str, int], list[str]]:
        """Distinct sanitizer point ids (``point_this`` / ``point_other``) per ``(file, line)``."""
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
    def build_line_coverage_summary(merged: pd.DataFrame) -> pd.DataFrame:
        """Per-(file, line) summary from merged llc/opt coverage.

        Returns columns ``file``, ``line``, ``coverage`` (``full`` | ``partial`` | ``none``),
        and ``point_addresses`` (all ``point_this`` / ``point_other`` ids on the line,
        semicolon-separated).
        """
        m = merged.copy()
        m["line"] = m["line"].astype(int)
        agg = (
            m.groupby(["file", "line"], as_index=False)
            .agg(n_covered=("covered_either", "sum"), n_points=("covered_either", "count"))
        )
        agg["coverage"] = np.where(
            agg["n_covered"] == 0,
            "none",
            np.where(agg["n_covered"] == agg["n_points"], "full", "partial"),
        )
        line_keys = set(zip(agg["file"], agg["line"]))
        addr_map = Sancov.all_uncovered_line_point_addresses(m, line_keys)
        agg["point_addresses"] = [
            ";".join(addr_map.get((f, ln), []))
            for f, ln in zip(agg["file"], agg["line"])
        ]
        return agg[["file", "line", "coverage", "point_addresses"]]

    @staticmethod
    def _load_llc_opt_coverage_dfs(
        this_symcov_path: Path,
        other_symcov_path: Path,
        path_filter: str,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        with this_symcov_path.open(encoding="utf-8") as f:
            this_symcov = json.load(f)
        with other_symcov_path.open(encoding="utf-8") as f:
            other_symcov = json.load(f)
        this_df = Sancov.get_coverage_df(this_symcov, path_filter)
        other_df = Sancov.get_coverage_df(other_symcov, path_filter)
        return this_df, other_df

    def get_merged_sancov_path(self) -> Path:
        return self.output_dir / f"{self.suffix}.0.sancov"

    def get_merged_symcov_path(self) -> Path:
        return self.output_dir / f"{self.suffix}.0.symcov"

    def get_covered_addresses(self, sancov_file: Path) -> set[str]:
        """Get the covered addresses from a sancov file."""
        try:
            proc = run_subprocess(
                logger,
                [str(self.sancov_bin), "--print", str(sancov_file)],
                label="sancov --print",
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or "").strip()
            raise RuntimeError(
                f"sancov --print failed for {sancov_file}: {err or e}"
            ) from e
        return {
            Sancov.format_hex_address(line.strip())
            for line in proc.stdout.splitlines()
            if line.strip()
        }

    def has_raw_files(self) -> bool:
        """True if any raw ``.sancov`` files exist for this suffix."""
        return any(self.raw_sancov_dir.glob(f"{self.suffix}.*.sancov"))

    def write_empty_symcov(self) -> None:
        """Write a symcov with no instrumented or covered points.

        Used when a tool (llc/opt) produced no coverage for the selected tests,
        so downstream joint-coverage treats it as contributing zero points
        instead of crashing on a missing file.
        """
        empty = {"point-symbol-info": {}, "covered-points": []}
        with self.get_merged_symcov_path().open("w", encoding="utf-8") as f:
            json.dump(empty, f)

    def merge(self) -> None:
        """Merge the sancov files for the given suffix."""
        with log_timing(logger, f"sancov merge ({self.suffix})"):
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
                        run_subprocess(
                            logger,
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
        with log_timing(logger, f"sancov symbolize ({self.suffix})"):
            if symcov_path.exists():
                logger.info(
                    "Symcov file already exists at %s, skipping symbolization",
                    symcov_path,
                )
                return

            logger.info("Symbolizing %s with %s", sancov_path, self.instrumented_bin)

            cmd = [str(self.sancov_bin), "-symbolize", str(sancov_path), str(self.instrumented_bin)]

            with symcov_path.open("w") as f:
                run_subprocess(logger, cmd, check=True, stdout=f, stderr=subprocess.STDOUT)

    def get_joint_coverage(
        self,
        other: Sancov,
        path_filter: str | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Build the LLC address map and per-line summary for *this* (llc) vs *other* (opt).

        A fully covered line is one where every instrumentation point on that line is covered
        by llc and/or opt. Points are matched on ``(file, line, col)``; when both tools
        instrument the same site, either tool hitting it counts. Ll-only and opt-only
        points on the line are included as well.

        Returns ``(llc_address_line_map, line_coverage_summary)``.
        The map uses columns ``file``, ``line``, ``point_<suffix>``.
        The summary has ``file``, ``line``, ``coverage``, ``point_addresses``.
        """

        with log_timing(logger, f"joint coverage ({self.suffix})"):
            if path_filter is None:
                path_filter = path_filter_from_lit_filter(DEFAULT_LIT_FILTER)

            this_df, other_df = Sancov._load_llc_opt_coverage_dfs(
                self.get_merged_symcov_path(),
                other.get_merged_symcov_path(),
                path_filter,
            )

            this_address_line_map = this_df[["file", "line", "point"]].copy()
            this_address_line_map["line"] = this_address_line_map["line"].astype(int)
            this_address_line_map.rename(columns={"point": f"point_{self.suffix}"}, inplace=True)

            if self.coverage_mode == "full":
                merged_cov = Sancov.merged_llc_opt_coverage_df(this_df, other_df)
                line_coverage_summary = Sancov.build_line_coverage_summary(merged_cov)
                return (this_address_line_map, line_coverage_summary)

            elif self.coverage_mode == "partial":
                raise NotImplementedError(f"Coverage mode {self.coverage_mode} not implemented")