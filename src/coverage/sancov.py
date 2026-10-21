"""SanitizerCoverage merge, symbolize, and stats via llvm sancov."""

from __future__ import annotations

import concurrent.futures
import os
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from collections.abc import Sequence
import orjson
import pandas as pd
import numpy as np
from pathlib import Path

from fuzz_fill.log import get_logger, log_timing, run_subprocess

logger = get_logger("coverage.sancov")

_RAW_SANCOV_NAME = re.compile(r"^(?P<tool>.+)\.(?P<pid>\d+)\.sancov$")


def _quote_rsp_path(path: str) -> str:
    """Quote a path for an LLVM GNU-style response file."""
    return '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _load_symcov(path: Path | str) -> dict:
    """Load a merged symcov JSON file."""
    return orjson.loads(Path(path).read_bytes())


def _coverage_df_from_symcov_path(task: tuple[str, str]) -> pd.DataFrame:
    """Load one merged symcov in a worker process."""
    symcov_path, source_code_filter = task
    try:
        symcov = _load_symcov(symcov_path)
        return Sancov.get_coverage_df(symcov, source_code_filter)
    except Exception as exc:
        raise RuntimeError(f"failed to load symcov {symcov_path}") from exc


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

    @staticmethod
    def group_raw_dumps(raw_sancov_dir: Path) -> dict[str, list[str]]:
        """One ``os.scandir`` pass: tool basename to sorted dump path strings.

        Only names matching ``<tool>.<pid>.sancov`` with a numeric process ID
        are kept. Strings avoid building a ``Path`` per file.
        """
        groups: dict[str, list[str]] = defaultdict(list)
        with os.scandir(raw_sancov_dir) as entries:
            for entry in entries:
                match = _RAW_SANCOV_NAME.match(entry.name)
                if match:
                    groups[match.group("tool")].append(entry.path)
        return {tool: sorted(paths) for tool, paths in groups.items()}

    @staticmethod
    def discover_tools(raw_sancov_dir: Path) -> list[str]:
        """Sorted tool basenames that emitted ``<tool>.<pid>.sancov`` dumps."""
        return sorted(Sancov.group_raw_dumps(raw_sancov_dir))

    @staticmethod
    def tool_address_line_map_filename(tool: str) -> str:
        return f"{tool}_address_line_map.csv"

    @staticmethod
    def tool_line_point_summary_filename(tool: str) -> str:
        return f"{tool}_line_point_summary.csv"

    def __init__(
        self,
        sancov: Path,
        symbolize_target: Path | None = None,
        raw_sancov_dir: Path | None = None,
        suffix: str | None = None,
    ) -> None:
        self.sancov_bin = sancov
        self.symbolize_target = symbolize_target
        self.raw_sancov_dir = raw_sancov_dir
        self.suffix = suffix

        if self.raw_sancov_dir is not None:
            self.output_dir = self.raw_sancov_dir.parent / f"processed_sancov"
            self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def flatten_point_symbol_info(point_symbol_info: dict[str, object]) -> pd.DataFrame:
        """Flatten the point-symbol-info dictionary into a dataframe."""
        files, addrs, lines = [], [], []
        for file, functions in point_symbol_info.items():
            for addr_to_line in functions.values():
                for addr, line_col in addr_to_line.items():
                    files.append(file)
                    addrs.append(addr)
                    lines.append(int(line_col.partition(":")[0]))

        out = pd.DataFrame({
            "file": pd.Series(files, dtype=object),
            "point": pd.Series(addrs, dtype=object),
            "line": np.array(lines, dtype=np.int32),
        })
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

        if source_code_filter:
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

        return Sancov.dedupe_coverage_points(df)

    @staticmethod
    def dedupe_coverage_points(df: pd.DataFrame) -> pd.DataFrame:
        """Collapse duplicate ``(file, line, point)`` rows from symcov flattening.

        Header and STL paths can map the same instrumentation point through multiple
        function entries. ``covered`` is a function of ``point`` alone, so duplicate
        rows agree on it; keep the first row per triple.
        """
        if df.empty:
            return df
        return (
            df.drop_duplicates(["file", "line", "point"], ignore_index=True)
            [["file", "line", "point", "covered"]]
        )

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
            dfs.append(
                Sancov.get_coverage_df(_load_symcov(symcov_path), source_code_filter)
            )
        return dfs

    @staticmethod
    def load_coverage_dfs_from_sancovs(
        sancovs: list[Sancov],
        source_code_filter: str | None = None,
        jobs: int | None = None,
    ) -> list[pd.DataFrame]:
        """Load per-tool coverage frames from merged symcov paths on each Sancov.

        One process per tool, capped by ``jobs`` when it is set. Threads do not
        overlap this walk: the pandas steps hold the GIL. Result order matches
        ``sancovs``.
        """
        if source_code_filter is None:
            source_code_filter = ""
        paths = [s.get_merged_symcov_path() for s in sancovs]
        if len(paths) <= 1:
            return Sancov.load_coverage_dfs(paths, source_code_filter)

        workers = len(paths)
        if jobs is not None:
            workers = min(jobs, workers)
        if workers <= 1:
            return Sancov.load_coverage_dfs(paths, source_code_filter)

        tasks = [(str(path), source_code_filter) for path in paths]
        with log_timing(logger, "symcov load"):
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
                return list(pool.map(_coverage_df_from_symcov_path, tasks, chunksize=1))

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
        return Sancov.parse_print_output(proc.stdout)

    @staticmethod
    def parse_print_output(stdout: str) -> set[str]:
        """Parse ``sancov --print`` stdout into normalized point IDs."""
        return {
            Sancov.format_hex_address(line.strip())
            for line in stdout.splitlines()
            if line.strip()
        }

    def has_raw_files(self) -> bool:
        """True if any raw ``.sancov`` files exist for this suffix."""
        with os.scandir(self.raw_sancov_dir) as entries:
            for entry in entries:
                match = _RAW_SANCOV_NAME.match(entry.name)
                if match and match.group("tool") == self.suffix:
                    return True
        return False

    def raw_files(self) -> list[Path]:
        """Sorted raw ``.sancov`` dumps for this suffix."""
        paths: list[Path] = []
        with os.scandir(self.raw_sancov_dir) as entries:
            for entry in entries:
                match = _RAW_SANCOV_NAME.match(entry.name)
                if match and match.group("tool") == self.suffix:
                    paths.append(Path(entry.path))
        return sorted(paths)

    def union_files(
        self, inputs: Sequence[str | Path], output: Path
    ) -> None:
        """Union *inputs* into *output*.

        A single input is copied. Multiple inputs are passed to ``sancov -union``
        via a response file (``@list``), one quoted path per line.
        """
        if not inputs:
            raise ValueError("union_files requires at least one input")
        if len(inputs) == 1:
            shutil.copy(str(inputs[0]), output)
            return

        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix="sancov-union-",
            suffix=".rsp",
            dir=output.parent,
            delete=False,
            mode="w",
            encoding="utf-8",
        ) as list_file:
            list_file.write(
                "".join(_quote_rsp_path(str(path)) + "\n" for path in inputs)
            )
            rsp = Path(list_file.name)
        try:
            run_subprocess(
                logger,
                [
                    str(self.sancov_bin),
                    "-union",
                    f"@{rsp}",
                    "--output",
                    str(output),
                ],
                check=True,
            )
        finally:
            rsp.unlink(missing_ok=True)

    def merge(self) -> None:
        """Merge the sancov files for the given suffix."""
        with log_timing(logger, f"sancov merge ({self.suffix})"):
            raw_files = self.raw_files()
            if not raw_files:
                raise FileNotFoundError(
                    f"No sancov files found for suffix: {self.suffix}"
                )
            self.union_files(raw_files, self.get_merged_sancov_path())
    
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
