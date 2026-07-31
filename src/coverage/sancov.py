"""SanitizerCoverage merge, symbolize, and stats via llvm sancov."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import json
import pandas as pd
import numpy as np
from pathlib import Path

from coverage.constants import DEFAULT_SOURCE_CODE_FILTER
from fuzz_fill.log import get_logger, log_timing, run_subprocess

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
        sancov: Path,
        symbolize_target: Path | None = None,
        raw_sancov_dir: Path | None = None,
        suffix: str | None = None,
        union_batch: int = 200,
    ) -> None:
        self.sancov_bin = sancov
        self.symbolize_target = symbolize_target
        self.union_batch = union_batch
        self.raw_sancov_dir = raw_sancov_dir
        self.suffix = suffix

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
    def get_coverage_df(symcov: dict[str, object], source_code_filter: str) -> pd.DataFrame:
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

        point_symbol_info = {
            k: v for k, v in point_symbol_info.items() if source_code_filter in k
        }

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
    def coverage_df_from_hits(
        address_line_map: pd.DataFrame,
        covered_addresses: set[str],
        *,
        point_column: str = "point",
    ) -> pd.DataFrame:
        """Build a ``(file, line, point, covered)`` frame from a static address map and runtime hits."""
        m = address_line_map[["file", "line", point_column]].copy()
        m["line"] = m["line"].astype(int)
        m["point"] = m[point_column].map(
            lambda x: Sancov.format_hex_address(x) if pd.notna(x) else x
        )
        m["covered"] = m["point"].isin(covered_addresses).astype(int)
        return m[["file", "line", "point", "covered"]]

    @staticmethod
    def covered_line_keys(coverage_dfs: list[pd.DataFrame]) -> set[tuple[str, int]]:
        """``(file, line)`` pairs classified as ``covered`` by ``build_coverage_summary``."""
        summary = Sancov.build_coverage_summary(coverage_dfs)
        rows = summary.loc[summary["coverage"] == "covered"]
        return set(zip(rows["file"], rows["line"].astype(int)))

    @staticmethod
    def build_address_line_map(df: pd.DataFrame) -> pd.DataFrame:
        """Static ``(file, line, point, covered)`` map for a per-tool coverage frame.

        A line with multiple instrumentation points yields multiple rows. This reflects
        the coverage information available in the tool regardless of coverage achieved.
        """
        required_cols = ("file", "line", "point", "covered")
        missing = set(required_cols) - set(df.columns)
        assert not missing, f"address line map input missing columns: {sorted(missing)}"
        address_line_map = df[list(required_cols)].copy()
        address_line_map["line"] = address_line_map["line"].astype(int)
        return address_line_map

    @staticmethod
    def build_line_point_summary(
        address_line_map: pd.DataFrame, *, point_column: str = "point"
    ) -> pd.DataFrame:
        """Per-(file, line) semicolon-separated point lists for one tool address-line map.

        Input is the output of ``build_address_line_map`` with columns ``file``, ``line``,
        ``covered``, and ``point``.

        Returns columns ``file``, ``line``, ``covered_points``, ``all_points``.
        """
        required_cols = ("file", "line", "covered", point_column)
        missing = set(required_cols) - set(address_line_map.columns)
        assert not missing, f"address line map missing columns: {sorted(missing)}"
        if address_line_map.empty:
            return pd.DataFrame(columns=["file", "line", "covered_points", "all_points"])

        covered_col = address_line_map["covered"]
        assert (
            pd.api.types.is_numeric_dtype(covered_col)
            and covered_col.isin([0, 1]).all()
        ), "covered must be numeric 0/1 flags"

        keys_order: list[tuple[str, int]] = []
        all_points_by_key: dict[tuple[str, int], set[str]] = {}
        covered_points_by_key: dict[tuple[str, int], set[str]] = {}

        for file, line, point, covered in zip(
            address_line_map["file"].to_numpy(),
            address_line_map["line"].astype(int).to_numpy(),
            address_line_map[point_column].to_numpy(),
            covered_col.to_numpy(),
        ):
            if pd.isna(point):
                continue
            key = (file, line)
            if key not in all_points_by_key:
                keys_order.append(key)
                all_points_by_key[key] = set()
            point_str = str(point)
            all_points_by_key[key].add(point_str)
            if covered == 1:
                covered_points_by_key.setdefault(key, set()).add(point_str)

        rows = []
        for file, line in keys_order:
            key = (file, line)
            covered_set = covered_points_by_key.get(key)
            rows.append(
                {
                    "file": file,
                    "line": line,
                    "covered_points": ";".join(sorted(covered_set)) if covered_set else "",
                    "all_points": ";".join(sorted(all_points_by_key[key])),
                }
            )
        return pd.DataFrame(
            rows, columns=["file", "line", "covered_points", "all_points"]
        )

    @staticmethod
    def build_coverage_summary(coverage_dfs: list[pd.DataFrame]) -> pd.DataFrame:
        """Per-(file, line) coverage classification across one or more tool frames.

        Each input frame must have columns ``file``, ``line``, ``point``, and ``covered``.
        A ``(file, line)`` present in only one tool is judged solely on that tool's
        points.

        Returns columns ``file``, ``line``, ``coverage`` with values:
        - ``uncovered``: every instrumentation point across all tools has ``covered == 0``
        - ``covered``: at least one tool has all instrumentation points on the line covered
        - ``partially``: some points are covered, but no tool fully covers the line
        """
        required_cols = ("file", "line", "point", "covered")
        for i, df in enumerate(coverage_dfs):
            missing = set(required_cols) - set(df.columns)
            assert not missing, f"coverage_dfs[{i}] missing columns: {sorted(missing)}"
        if not coverage_dfs:
            return pd.DataFrame(columns=["file", "line", "coverage"])

        per_tool: list[pd.DataFrame] = []
        for df in coverage_dfs:
            tool_df = df[list(required_cols)].copy()
            tool_df["line"] = tool_df["line"].astype(int)
            assert (
                pd.api.types.is_numeric_dtype(tool_df["covered"])
                and tool_df["covered"].isin([0, 1]).all()
            ), "covered must be numeric 0/1 flags"
            dupes = tool_df.duplicated(subset=["file", "line", "point"], keep=False)
            assert not dupes.any(), (
                "duplicate instrumentation points for the same (file, line) in one tool: "
                f"{tool_df.loc[dupes, ['file', 'line', 'point']].drop_duplicates().to_dict('records')}"
            )
            # One row per (file, line) for this tool: how many points exist vs how many were hit.
            # e.g. two points on line 42 with covered=[1, 0] -> tool_points=2, tool_covered=1.
            grouped = (
                tool_df.groupby(["file", "line"], as_index=False)
                .agg(tool_points=("covered", "count"), tool_covered=("covered", "sum"))
            )
            grouped["tool_full"] = grouped["tool_covered"] == grouped["tool_points"]
            per_tool.append(grouped)

        combined = pd.concat(per_tool, ignore_index=True)
        # Merge per-tool stats: total hits across tools, and whether any one tool fully covered the line.
        # e.g. llc tool_covered=1, opt tool_covered=2 -> total_covered=3; llc tool_full=True -> any_tool_full=True.
        agg = (
            combined.groupby(["file", "line"], as_index=False)
            .agg(total_covered=("tool_covered", "sum"), any_tool_full=("tool_full", "any"))
        )
        # A (file, line) is
        #   a) uncovered if none of its points were covered by any tool.
        #   b) covered if at least one tool fully covered all of its points in that tool.
        #   c) partially if some points are covered, but no tool fully covered the line.
        agg["coverage"] = np.select(
            [agg["total_covered"] == 0, agg["any_tool_full"]],
            ["uncovered", "covered"],
            default="partially",
        )
        return agg[["file", "line", "coverage"]].sort_values(
            ["file", "line"]
        ).reset_index(drop=True)

    @staticmethod
    def load_coverage_dfs(
        symcov_paths: list[Path],
        source_code_filter: str,
    ) -> list[pd.DataFrame]:
        """Load per-tool coverage frames from symcov JSON files."""
        dfs: list[pd.DataFrame] = []
        for symcov_path in symcov_paths:
            with symcov_path.open(encoding="utf-8") as f:
                symcov = json.load(f)
            dfs.append(Sancov.get_coverage_df(symcov, source_code_filter))
        return dfs

    @staticmethod
    def load_coverage_dfs_from_sancovs(
        sancovs: list[Sancov],
        source_code_filter: str | None = None,
    ) -> list[pd.DataFrame]:
        """Load per-tool coverage frames from merged symcov paths on each Sancov."""
        if source_code_filter is None:
            source_code_filter = DEFAULT_SOURCE_CODE_FILTER
        return Sancov.load_coverage_dfs(
            [s.get_merged_symcov_path() for s in sancovs],
            source_code_filter,
        )

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

            raw_files = sorted(self.raw_sancov_dir.glob(f"{self.suffix}.*.sancov"))
            if not raw_files:
                raise FileNotFoundError(f"No sancov files found for suffix: {self.suffix}")

            if len(raw_files) == 1:
                shutil.copy(raw_files[0], merged_out)
                return

            logger.info("Merging %d raw sancov file(s) via sancov -union", len(raw_files))

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
                        self._union_raw_sancov_chunk(chunk, out_f)
                        nxt.append(out_f)
                    layer = nxt
                    round_idx += 1
                shutil.copy(layer[0], merged_out)

    def _union_raw_sancov_chunk(self, inputs: list[Path], output: Path) -> None:
        result = run_subprocess(
            logger,
            [str(self.sancov_bin), "-union", *[str(path) for path in inputs], "--output", str(output)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            stderr = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                f"sancov -union failed for {len(inputs)} file(s): {stderr or result.returncode}"
            )
    
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

            logger.info("Symbolizing %s with %s", sancov_path, self.symbolize_target)

            cmd = [
                str(self.sancov_bin),
                "-symbolize",
                str(sancov_path),
                str(self.symbolize_target),
            ]

            with symcov_path.open("w") as f:
                run_subprocess(logger, cmd, check=True, stdout=f, stderr=subprocess.STDOUT)

    @staticmethod
    def get_joint_coverage(
        coverage_dfs: list[pd.DataFrame],
    ) -> tuple[list[pd.DataFrame], list[pd.DataFrame], pd.DataFrame]:
        """
        Build per-tool address maps, line point summaries, and a joint coverage summary.

        Each input frame must have columns ``file``, ``line``, ``point``, and ``covered``.

        Each address map is a static, per-tool table: one row per instrumentation point
        (a line with multiple points yields multiple rows), with a ``covered`` flag marking
        which points were hit.

        Each line point summary is one row per ``(file, line)`` for that tool with
        semicolon-separated ``covered_points`` and ``all_points``.

        The coverage summary classifies every instrumented ``(file, line)`` as
        ``uncovered``, ``covered``, or ``partially``.

        Returns ``(address_line_maps, line_point_summaries, coverage)``.
        Each map uses columns ``file``, ``line``, ``point``, ``covered``.
        Each line point summary uses columns ``file``, ``line``, ``covered_points``, ``all_points``.
        The coverage summary has columns ``file``, ``line``, ``coverage``.
        """
        with log_timing(logger, "joint coverage"):
            # Per-tool table (file, point, line, covered) based on the sancov traces and symcov.
            # Each address_line_map has rows of (file, line, point_id, covered) using the static
            # coverage information provided in the symcov of the respective tool.
            # A line with multiple points will have multiple rows in the map.
            # This is the coverage information available in the tool regardless of the coverage achieved.
            # Those points that were covered are reported as such in the "covered" col.
            address_line_maps = [
                Sancov.build_address_line_map(df) for df in coverage_dfs
            ]
            # Each line_point_summary has one row per (file, line) for that tool with
            # semicolon-separated covered_points and all_points derived from the address-line map.
            line_point_summaries = [
                Sancov.build_line_point_summary(m) for m in address_line_maps
            ]
            coverage = Sancov.build_coverage_summary(coverage_dfs)
            return address_line_maps, line_point_summaries, coverage
