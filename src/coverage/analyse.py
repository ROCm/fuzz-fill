"""Post-process ``coverage new-tests`` output directories."""

from __future__ import annotations

import csv
from argparse import Namespace
from pathlib import Path

import pandas as pd

from coverage.runner import display_path_for_log
from coverage.session import LLC_TEST_REPORT_CSV
from coverage.stage_log import stage_line

_NOVEL_LINE_COLS = frozenset({"file", "function", "line"})

# Written under ``output_dir`` when ``coverage analyse`` stacks per-test novel-line CSVs.
STACKED_NOVEL_LINES_DIR = "analyse_stacked_novel_lines"
STACKED_NOVEL_LINES_CSV = "all_novel_source_lines.csv"


def novel_source_lines_csv_data_row_count(path: Path) -> int | None:
    """
    If ``path`` is a novel-source-lines CSV (``file``, ``function``, ``line``), return the number
    of data rows with a non-empty ``file`` and ``line``; else ``None``.
    """
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return None
            by_lower = {
                (n or "").strip().lower(): n for n in reader.fieldnames if n
            }
            if not _NOVEL_LINE_COLS <= by_lower.keys():
                return None
            cf = by_lower["file"]
            cl = by_lower["line"]
            n = 0
            for row in reader:
                file_s = (row.get(cf) or "").strip()
                line_s = (row.get(cl) or "").strip()
                if file_s and line_s:
                    n += 1
            return n
    except OSError:
        return None


def list_csvs_with_new_source_lines(output_dir: Path) -> list[Path]:
    """
    Recursively find ``*.csv`` under ``output_dir`` that use the per-test novel-line schema and
    contain at least one data row. Skips ``llc_test_report.csv``.
    """
    root = output_dir.resolve()
    hits: list[Path] = []
    for path in sorted(root.rglob("*.csv")):
        if not path.is_file():
            continue
        if path.name == LLC_TEST_REPORT_CSV:
            continue
        count = novel_source_lines_csv_data_row_count(path)
        if count is not None and count >= 1:
            hits.append(path)
    return hits


def stacked_novel_source_lines_dataframe(output_dir: Path, paths: list[Path]) -> pd.DataFrame:
    """
    Concatenate novel-line CSVs (columns ``file``, ``function``, ``line``) into one frame.

    Deduplicates rows that share the same ``file``, ``function``, and ``line`` (after stacking);
    which duplicate is kept is unspecified.

    ``per_test_csv`` is the path of the per-test CSV for the retained row (relative to
    ``output_dir``, POSIX).
    """
    root = output_dir.resolve()
    frames: list[pd.DataFrame] = []
    for p in paths:
        df = pd.read_csv(p)
        by_lower = {(c or "").strip().lower(): c for c in df.columns}
        missing = _NOVEL_LINE_COLS - by_lower.keys()
        if missing:
            raise ValueError(
                f"Expected columns {sorted(_NOVEL_LINE_COLS)} in {p}; missing {sorted(missing)}"
            )
        out = pd.DataFrame(
            {
                "file": df[by_lower["file"]].astype("string"),
                "function": df[by_lower["function"]].astype("string"),
                "line": df[by_lower["line"]].astype("string"),
            }
        )
        mask = out["file"].str.strip().ne("") & out["line"].str.strip().ne("")
        out = out.loc[mask].copy()
        out["per_test_csv"] = p.resolve().relative_to(root).as_posix()
        frames.append(out)
    if not frames:
        return pd.DataFrame(
            columns=["per_test_csv", "file", "function", "line"],
            dtype="string",
        )
    stacked = pd.concat(frames, ignore_index=True)
    deduped = stacked.drop_duplicates(
        subset=["file", "function", "line"],
        keep="first",
        ignore_index=True,
    )
    return deduped[["per_test_csv", "file", "function", "line"]]


def analyse_main(args: Namespace) -> int:
    d = Path(args.output_dir).resolve()
    if not d.is_dir():
        stage_line("analyse", f"ERROR: not a directory: {d}")
        return 2

    paths = list_csvs_with_new_source_lines(d)
    stage_line(
        "analyse",
        f"Novel source line CSVs with at least 1 newly covered line: {len(paths)}",
    )
    for p in paths:
        try:
            rel = p.relative_to(Path.cwd())
            shown = rel.as_posix()
        except ValueError:
            shown = display_path_for_log(p)
        stage_line("analyse", f"  {shown}")

    if paths:
        stacked_dir = d / STACKED_NOVEL_LINES_DIR
        stacked_dir.mkdir(parents=True, exist_ok=True)
        out_csv = stacked_dir / STACKED_NOVEL_LINES_CSV
        df = stacked_novel_source_lines_dataframe(d, paths)
        df.to_csv(out_csv, index=False)
        stage_line(
            "analyse",
            f"Stacked {len(df)} unique (file,function,line) row(s) -> "
            f"{display_path_for_log(out_csv)}",
        )
    return 0
