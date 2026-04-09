"""Orchestrate test run + per-binary SanCov processing and outline output."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from contextlib import ExitStack
from pathlib import Path

import pandas as pd

from coverage.baseline_csv import (
    addresses_in_test_not_in_baseline,
    load_baseline_llc_addresses_by_source_line,
    load_baseline_llc_addresses_from_csv,
    load_llc_line_address_map_rows,
    norm_address_to_files_from_line_map_rows,
    normalized_addresses_missing_from_line_map,
    novel_source_lines_vs_baseline,
    split_novel_addresses_by_source_prefix,
    split_novel_lines_by_source_prefix,
    test_hit_addresses_normalized_df,
    test_raw_addresses_df,
)
from coverage.config import CoverageConfig
from coverage.runner import TestCommandRunner, display_path_for_log
from coverage.sancov import BinaryCoverageResult, SanCov
from coverage.stage_log import stage_line


LLC_TEST_REPORT_CSV = "llc_test_report.csv"
# One CSV per test input under these directories (columns: file, function, line).
LLC_TEST_NOVEL_SOURCE_LINES_DIR = "llc_test_novel_source_lines"
LLC_TEST_NOVEL_SOURCE_LINES_IN_PREFIX_DIR = "llc_test_novel_source_lines_in_prefix"
LLC_TEST_NOVEL_SOURCE_LINES_OUTSIDE_PREFIX_DIR = (
    "llc_test_novel_source_lines_outside_prefix"
)


def _new_tests_prior_outputs_present(cov: Path) -> bool:
    """Whether canonical new-tests artifacts already exist under ``cov``."""
    if (cov / LLC_TEST_REPORT_CSV).is_file():
        return True
    for base in (
        LLC_TEST_NOVEL_SOURCE_LINES_DIR,
        LLC_TEST_NOVEL_SOURCE_LINES_IN_PREFIX_DIR,
        LLC_TEST_NOVEL_SOURCE_LINES_OUTSIDE_PREFIX_DIR,
    ):
        d = cov / base
        if d.is_dir() and any(d.iterdir()):
            return True
    return False


def _new_tests_version_paths_unused(cov: Path, version_suffix: str) -> bool:
    """True if report ``llc_test_report{suffix}.csv`` and sibling novel dirs do not exist."""
    if (cov / f"llc_test_report{version_suffix}.csv").exists():
        return False
    for base in (
        LLC_TEST_NOVEL_SOURCE_LINES_DIR,
        LLC_TEST_NOVEL_SOURCE_LINES_IN_PREFIX_DIR,
        LLC_TEST_NOVEL_SOURCE_LINES_OUTSIDE_PREFIX_DIR,
    ):
        if (cov / f"{base}{version_suffix}").exists():
            return False
    return True


def _resolve_new_tests_output_paths(
    cov: Path, reuse_dir: Path | None
) -> tuple[Path, Path, Path, Path, str | None]:
    """
    With ``--existing-sancov-dir``, if ``llc_test_report.csv`` or novel-line dirs already exist
    under ``cov``, write to ``llc_test_report_v2.csv`` (then ``_v3``, ...) and matching ``*_vN`` dirs.
    """
    if reuse_dir is None or not _new_tests_prior_outputs_present(cov):
        return (
            cov / LLC_TEST_REPORT_CSV,
            cov / LLC_TEST_NOVEL_SOURCE_LINES_DIR,
            cov / LLC_TEST_NOVEL_SOURCE_LINES_IN_PREFIX_DIR,
            cov / LLC_TEST_NOVEL_SOURCE_LINES_OUTSIDE_PREFIX_DIR,
            None,
        )
    n = 2
    while True:
        suf = f"_v{n}"
        if _new_tests_version_paths_unused(cov, suf):
            return (
                cov / f"llc_test_report{suf}.csv",
                cov / f"{LLC_TEST_NOVEL_SOURCE_LINES_DIR}{suf}",
                cov / f"{LLC_TEST_NOVEL_SOURCE_LINES_IN_PREFIX_DIR}{suf}",
                cov / f"{LLC_TEST_NOVEL_SOURCE_LINES_OUTSIDE_PREFIX_DIR}{suf}",
                suf,
            )
        n += 1


def _safe_novel_lines_csv_filename(test_key: str) -> str:
    """Map a test's relative POSIX path to a single flat ``.csv`` filename."""
    flat = Path(test_key).as_posix().replace("/", "__").replace("\x00", "")
    if not flat or set(flat) <= {"."}:
        flat = "test"
    name = f"{flat}.csv"
    if len(name) > 200:
        digest = hashlib.sha256(test_key.encode("utf-8")).hexdigest()[:20]
        tail = Path(test_key).name.replace("/", "_")[:80] or "test"
        name = f"{digest}__{tail}.csv"
    return name


def _write_novel_lines_per_test_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["file", "function", "line"]
    out = df[cols] if not df.empty else pd.DataFrame(columns=cols)
    out.to_csv(path, index=False, lineterminator="\n", encoding="utf-8")


def _collect_llc_input_files(test_root: Path) -> list[Path]:
    """Sorted unique paths under ``test_root`` with suffix ``.ll`` or ``.bc``."""
    paths: set[Path] = set()
    for pattern in ("*.ll", "*.bc"):
        paths.update(p for p in test_root.rglob(pattern) if p.is_file())
    return sorted(paths)


_RAW_LLC_SANCOV_RE = re.compile(r"^llc\.(\d+)\.sancov$")


def _sorted_raw_llc_sancov_paths(
    directory: Path, *, merged_suffix_id: str
) -> list[Path]:
    """Raw ``llc.<pid>.sancov`` under ``directory``, sorted by numeric PID (excludes merged file)."""
    merged_name = f"llc.{merged_suffix_id}.sancov"
    found: list[tuple[int, Path]] = []
    for p in directory.iterdir():
        if not p.is_file() or p.name == merged_name:
            continue
        m = _RAW_LLC_SANCOV_RE.match(p.name)
        if m:
            found.append((int(m.group(1)), p))
    return [p for _, p in sorted(found, key=lambda t: t[0])]


def _pair_tests_to_sancov_by_pid_order(
    to_run: list[Path],
    tests_root: Path,
    existing_dir: Path,
    merged_suffix_id: str,
) -> dict[str, list[str]]:
    files = _sorted_raw_llc_sancov_paths(existing_dir, merged_suffix_id=merged_suffix_id)
    n = len(to_run)
    if len(files) != n:
        raise RuntimeError(
            f"--existing-sancov-dir {existing_dir}: found {len(files)} raw llc.<pid>.sancov "
            f"file(s), but {n} test input(s) selected (after --limit). Use --reuse-report with a "
            f"prior llc_test_report.csv to map tests to files, or ensure exactly one raw file per test."
        )
    return {
        to_run[i].relative_to(tests_root).as_posix(): [files[i].name] for i in range(n)
    }


def _load_llc_test_reuse_report(
    report_path: Path,
    to_run: list[Path],
    tests_root: Path,
    existing_dir: Path,
) -> tuple[dict[str, list[str]], dict[str, int]]:
    with report_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"empty or invalid CSV: {report_path}")
        for col in ("test", "raw_sancov_files", "llc_exit_code"):
            if col not in reader.fieldnames:
                raise ValueError(
                    f"reuse report {report_path} missing required column {col!r}"
                )
        by_test = {row["test"]: row for row in reader}

    sancov_by_test: dict[str, list[str]] = {}
    rc_by_test: dict[str, int] = {}
    for test_path in to_run:
        key = test_path.relative_to(tests_root).as_posix()
        row = by_test.get(key)
        if row is None:
            raise RuntimeError(
                f"--reuse-report {report_path} has no row for test {key!r}"
            )
        raw_cell = (row.get("raw_sancov_files") or "").strip()
        basenames: list[str] = json.loads(raw_cell) if raw_cell else []
        for b in basenames:
            p = existing_dir / b
            if not p.is_file():
                raise FileNotFoundError(
                    f"reuse report lists {b!r} for test {key!r} but file is missing under "
                    f"{existing_dir}"
                )
        sancov_by_test[key] = basenames
        rc_cell = row.get("llc_exit_code", "")
        try:
            rc = int(rc_cell) if str(rc_cell).strip() != "" else 0
        except ValueError:
            rc = 0
        rc_by_test[key] = rc
    return sancov_by_test, rc_by_test


def _format_duration_hms(seconds: float) -> str:
    """Human-readable duration for logs (minutes + seconds, or seconds only)."""
    if seconds >= 60.0:
        m = int(seconds // 60)
        s = seconds - m * 60
        if m == 1:
            return f"1 minute {s:.1f} seconds" if s >= 0.05 else "1 minute"
        return f"{m} minutes {s:.1f} seconds"
    return f"{seconds:.1f} seconds"


class CoverageSession:
    """One llvm-lit (or custom) run plus merge/symbolize for configured binaries."""

    def __init__(self, config: CoverageConfig) -> None:
        self.config = config
        self.san_cov = SanCov(
            config.build_bin_dir,
            merged_suffix_id=config.merged_suffix_id,
            union_batch=config.union_batch,
        )
        self._runner = TestCommandRunner()

    def run_tests(self) -> int | None:
        if self.config.skip_run:
            stage_line("skip-run", "(--skip-run: not executing tests)")
            return None
        if self.config.new_tests_dir is not None:
            return self._run_new_tests()
        assert self.config.command is not None
        return self._runner.run(
            self.config.command,
            self.config.cwd,
            self.config.coverage_dir,
        )

    def _run_new_tests(self) -> int:
        """Run ``llc -o /dev/null`` on each ``*.ll`` / ``*.bc`` under ``new_tests_dir``; per-test addresses via ``sancov --print`` only (no merge/symbolize)."""
        d = self.config.new_tests_dir
        assert d is not None
        reuse_dir = self.config.new_tests_existing_sancov_dir
        llc_path: Path | None = None
        if reuse_dir is None:
            llc_path = self.san_cov.tool_binary("llc")
            if not llc_path.exists():
                raise FileNotFoundError(f"llc not found at {llc_path}")
        if not self.san_cov.sancov_bin.exists():
            raise FileNotFoundError(f"sancov not found at {self.san_cov.sancov_bin}")

        tests = _collect_llc_input_files(d)
        if not tests:
            raise RuntimeError(f"no .ll or .bc files under {d}")

        t0 = time.perf_counter()

        limit = self.config.new_tests_limit
        assert limit is not None
        src_prefix = self.config.new_tests_source_path_prefix
        sense = self.config.new_tests_sense_check
        load_prefix: str | None = None if sense else src_prefix

        z = len(tests)
        y = min(limit, z)
        to_run = tests[:y]

        cov = self.config.coverage_dir
        sancov_by_test: dict[str, list[str]] | None = None
        rc_by_test: dict[str, int] = {}
        if reuse_dir is not None:
            if self.config.new_tests_reuse_report is not None:
                sancov_by_test, rc_by_test = _load_llc_test_reuse_report(
                    self.config.new_tests_reuse_report, to_run, d, reuse_dir
                )
                stage_line(
                    "new-tests",
                    "Mapped tests to raw .sancov via "
                    f"{display_path_for_log(self.config.new_tests_reuse_report)}",
                )
            else:
                sancov_by_test = _pair_tests_to_sancov_by_pid_order(
                    to_run, d, reuse_dir, self.config.merged_suffix_id
                )
                stage_line(
                    "new-tests",
                    "Mapped tests to .sancov by pairing sorted test paths with raw files sorted by "
                    f"numeric PID under {display_path_for_log(reuse_dir)}; use --reuse-report if "
                    "that order does not match your capture.",
                )

        baseline_path = self.config.new_tests_baseline_csv
        baseline_norm_df: pd.DataFrame | None = None
        if baseline_path is not None:
            baseline_norm_df = load_baseline_llc_addresses_from_csv(
                baseline_path,
                source_path_prefix=load_prefix,
            )
            stage_line(
                "new-tests",
                "Loaded "
                + f"{len(baseline_norm_df)} unique llc address(es) from baseline CSV"
                + (
                    " (--sense-check: full CSV, split by prefix when reporting)"
                    if sense
                    else (
                        f" (source path prefix {src_prefix!r})"
                        if src_prefix is not None
                        else ""
                    )
                ),
            )

        line_map_path = self.config.new_tests_line_address_map
        line_map_df: pd.DataFrame | None = None
        baseline_long_df: pd.DataFrame | None = None
        if line_map_path is not None:
            line_map_df = load_llc_line_address_map_rows(
                line_map_path,
                source_path_prefix=load_prefix,
            )
            stage_line(
                "new-tests",
                "Loaded source lines from --line-address-map "
                f"{display_path_for_log(line_map_path)}"
                + (
                    " (--sense-check: full map, split by prefix when reporting)"
                    if sense
                    else (f" (prefix {src_prefix!r})" if src_prefix is not None else "")
                ),
            )
            assert baseline_path is not None
            baseline_long_df = load_baseline_llc_addresses_by_source_line(
                baseline_path,
                source_path_prefix=load_prefix,
            )
            n_loc = (
                len(baseline_long_df[["file", "function", "line"]].drop_duplicates())
                if not baseline_long_df.empty
                else 0
            )
            stage_line(
                "new-tests",
                f"Loaded {n_loc} baseline (file,function,line) location(s) "
                "for per-line comparison"
                + (" (--sense-check: full baseline rows)" if sense else ""),
            )

        # Full line map (no path filtering on load): every test hit address must appear in the map.
        norm_addr_files_df: pd.DataFrame | None = None
        if line_map_df is not None and load_prefix is None:
            norm_addr_files_df = norm_address_to_files_from_line_map_rows(line_map_df)

        def raw_llc_sancov_names() -> set[str]:
            return {p.name for p in self.san_cov.collect_raw(cov, "llc")}

        report_path, novel_dir, novel_dir_in, novel_dir_out, out_suffix = (
            _resolve_new_tests_output_paths(cov, reuse_dir)
        )
        if out_suffix is not None:
            stage_line(
                "new-tests",
                f"Prior outputs under {display_path_for_log(cov)}; writing "
                f"llc_test_report{out_suffix}.csv and novel-line dirs with suffix {out_suffix} "
                "to avoid overwriting.",
            )

        report_fields = [
            "test",
            "llc_exit_code",
            "raw_sancov_files",
            "baseline_unique_address_count",
            "test_unique_address_count",
            "test_only_address_count",
            "baseline_only_address_count",
            "both_address_count",
            "novel_source_line_count",
            "novel_vs_baseline_addresses",
        ]
        if sense:
            report_fields.extend(
                [
                    "novel_vs_baseline_addresses_in_prefix",
                    "novel_vs_baseline_addresses_outside_prefix",
                    "novel_source_line_count_in_prefix",
                    "novel_source_line_count_outside_prefix",
                ]
            )

        any_failed = False
        sum_llc_s = 0.0
        sum_novel_line_s = 0.0
        with ExitStack() as stack:
            report_f = stack.enter_context(
                report_path.open("w", newline="", encoding="utf-8")
            )
            writer = csv.DictWriter(report_f, fieldnames=report_fields)
            writer.writeheader()
            report_f.flush()

            tests_with_novel_line = 0
            for i, test_path in enumerate(to_run, start=1):
                rel = test_path.relative_to(d)
                test_key = rel.as_posix()
                if sancov_by_test is not None:
                    assert reuse_dir is not None
                    new_names = list(sancov_by_test[test_key])
                    rc = rc_by_test.get(test_key, 0)
                    llc_s = 0.0
                    sancov_root = reuse_dir
                    stage_line(
                        "new-tests",
                        f"processing [{i}/{y}] of {z} in {display_path_for_log(d)}\n"
                        f"Test name: {test_key}",
                    )
                    stage_line(
                        "new-tests",
                        f"reusing {len(new_names)} raw .sancov file(s) from "
                        f"{display_path_for_log(sancov_root)}",
                    )
                else:
                    stage_line(
                        "new-tests",
                        f"running [{i}/{y}] of {z} in {display_path_for_log(d)}\n"
                        f"Test name: {test_key}",
                    )
                    assert llc_path is not None
                    before = raw_llc_sancov_names()
                    argv = [str(llc_path), "-o", "/dev/null", str(rel)]
                    t_llc = time.perf_counter()
                    rc = self._runner.run_argv(argv, d, cov, log_per_test=True)
                    llc_s = time.perf_counter() - t_llc
                    sum_llc_s += llc_s
                    after = raw_llc_sancov_names()
                    new_names = sorted(after - before)
                    sancov_root = cov

                addr_strings: set[str] = set()
                for basename in new_names:
                    sp = sancov_root / basename
                    if sp.is_file():
                        addr_strings |= self.san_cov.unique_addresses_from_print(sp)
                test_raw_df = test_raw_addresses_df(addr_strings)
                test_norm_df = test_hit_addresses_normalized_df(addr_strings)
                stage_line(
                    "new-tests",
                    f"{len(test_norm_df)} addresses covered by test",
                )

                if norm_addr_files_df is not None and line_map_df is not None:
                    missing_df = normalized_addresses_missing_from_line_map(
                        test_norm_df, line_map_df
                    )
                    if not missing_df.empty:
                        n = len(missing_df)
                        cap = 20
                        shown = ", ".join(missing_df["addr"].head(cap).astype(str))
                        more = f" ... and {n - cap} more" if n > cap else ""
                        raise RuntimeError(
                            f"Test {test_key!r}: {n} llc address(es) from this run are not "
                            f"present in --line-address-map (normalized hex, examples): "
                            f"{shown}{more}"
                        )

                if baseline_norm_df is not None:
                    novel_df = addresses_in_test_not_in_baseline(
                        test_raw_df, baseline_norm_df
                    )
                    novel = novel_df["raw"].tolist()
                    stage_line(
                        "new-tests",
                        f"{len(novel)} address(es) from test not in baseline CSV",
                    )
                    bl = baseline_norm_df["addr"]
                    tt = test_norm_df["addr"]
                    row_counts = {
                        "baseline_unique_address_count": int(bl.nunique()),
                        "test_unique_address_count": int(tt.nunique()),
                        "test_only_address_count": int(tt.loc[~tt.isin(bl)].nunique()),
                        "baseline_only_address_count": int(bl.loc[~bl.isin(tt)].nunique()),
                        "both_address_count": int(tt.loc[tt.isin(bl)].nunique()),
                    }
                else:
                    novel_df = pd.DataFrame(columns=["raw", "norm"])
                    novel = []
                    row_counts = {
                        "baseline_unique_address_count": "",
                        "test_unique_address_count": int(test_norm_df["addr"].nunique()),
                        "test_only_address_count": "",
                        "baseline_only_address_count": "",
                        "both_address_count": "",
                    }

                novel_line_count: str | int = ""
                sense_row: dict[str, object] = {}
                novel_line_s = 0.0
                if (
                    line_map_df is not None
                    and baseline_long_df is not None
                ):
                    t_novel_lines = time.perf_counter()
                    novel_src_df = novel_source_lines_vs_baseline(
                        line_map_df,
                        baseline_long_df,
                        test_norm_df,
                        coverage_level=self.config.new_tests_novel_line_coverage_level,
                    )
                    if sense:
                        assert norm_addr_files_df is not None and src_prefix is not None
                        in_addrs_df, out_addrs_df = split_novel_addresses_by_source_prefix(
                            novel_df, norm_addr_files_df, src_prefix
                        )
                        in_lines_df, out_lines_df = split_novel_lines_by_source_prefix(
                            novel_src_df, src_prefix
                        )
                        novel_line_count = len(in_lines_df) + len(out_lines_df)
                        sense_row = {
                            "novel_vs_baseline_addresses_in_prefix": json.dumps(
                                in_addrs_df["raw"].tolist()
                            ),
                            "novel_vs_baseline_addresses_outside_prefix": json.dumps(
                                out_addrs_df["raw"].tolist()
                            ),
                            "novel_source_line_count_in_prefix": len(in_lines_df),
                            "novel_source_line_count_outside_prefix": len(out_lines_df),
                        }
                        stage_line(
                            "new-tests",
                            f"{novel_line_count} novel source line(s) total "
                            f"({len(in_lines_df)} under prefix, {len(out_lines_df)} outside); "
                            f"{len(in_addrs_df)} / {len(out_addrs_df)} novel address(es) "
                            "under prefix / outside",
                        )
                        stem = _safe_novel_lines_csv_filename(test_key)
                        _write_novel_lines_per_test_csv(
                            novel_dir_in / stem, in_lines_df
                        )
                        _write_novel_lines_per_test_csv(
                            novel_dir_out / stem, out_lines_df
                        )
                    else:
                        novel_line_count = len(novel_src_df)
                        stage_line(
                            "new-tests",
                            f"{novel_line_count} source line(s) for test hit by new "
                            "coverage but no line id in baseline",
                        )
                        _write_novel_lines_per_test_csv(
                            novel_dir / _safe_novel_lines_csv_filename(test_key),
                            novel_src_df,
                        )
                    novel_line_s = time.perf_counter() - t_novel_lines
                    sum_novel_line_s += novel_line_s

                writer.writerow(
                    {
                        "test": test_key,
                        "llc_exit_code": rc,
                        "raw_sancov_files": json.dumps(new_names),
                        "novel_vs_baseline_addresses": json.dumps(novel),
                        "novel_source_line_count": novel_line_count,
                        **sense_row,
                        **row_counts,
                    }
                )
                report_f.flush()

                if rc != 0:
                    any_failed = True
                    stage_line("new-tests", f"FAILED: test (exit {rc})")

                if (
                    line_map_df is not None
                    and isinstance(novel_line_count, int)
                    and novel_line_count > 0
                ):
                    tests_with_novel_line += 1
                if line_map_df is not None:
                    stage_line(
                        "new-tests",
                        f"{i} out of {y} tests processed, "
                        f"{tests_with_novel_line} cover at least 1 new line",
                    )
                else:
                    stage_line(
                        "new-tests",
                        f"{i} out of {y} tests processed",
                    )
                stage_line(
                    "new-tests",
                    f"timing: llc {llc_s:.2f}s; novel-line work {novel_line_s:.2f}s",
                )
                print(flush=True)

        stage_line(
            "new-tests",
            f"LLC test report CSV -> {display_path_for_log(report_path)}",
        )
        if line_map_df is not None:
            if sense:
                stage_line(
                    "new-tests",
                    "Novel source lines under prefix (one CSV per test) -> "
                    f"{display_path_for_log(novel_dir_in)}/",
                )
                stage_line(
                    "new-tests",
                    "Novel source lines outside prefix (one CSV per test) -> "
                    f"{display_path_for_log(novel_dir_out)}/",
                )
            else:
                stage_line(
                    "new-tests",
                    "Novel source lines (one CSV per test) -> "
                    f"{display_path_for_log(novel_dir)}/",
                )

        elapsed = time.perf_counter() - t0
        per_test = elapsed / y if y else 0.0
        stage_line(
            "new-tests",
            f"{y} tests processed in {_format_duration_hms(elapsed)} "
            f"-> {per_test:.2f} seconds per test",
        )
        if y:
            avg_llc = sum_llc_s / y
            avg_nl = sum_novel_line_s / y
            stage_line(
                "new-tests",
                f"Average timing per test: llc {avg_llc:.2f}s, "
                f"novel-line work {avg_nl:.2f}s",
            )

        return 1 if any_failed else 0

    def process_binaries(self) -> list[BinaryCoverageResult]:
        if not self.san_cov.sancov_bin.exists():
            raise FileNotFoundError(
                f"sancov not found at {self.san_cov.sancov_bin}"
            )

        results: list[BinaryCoverageResult] = []
        for binary_name in self.config.binaries:
            tool = self.san_cov.tool_binary(binary_name)
            if not tool.exists():
                raise FileNotFoundError(f"binary not found at {tool}")

            raw = self.san_cov.collect_raw(self.config.coverage_dir, binary_name)
            stage_line(
                "merge",
                f"Found {len(raw)} raw .sancov file(s) for {binary_name}",
            )
            if not raw:
                stage_line(
                    "merge",
                    f"WARNING: skipping {binary_name}: no raw "
                    f"<{binary_name}>.<digits>.sancov in "
                    f"{display_path_for_log(self.config.coverage_dir)}",
                )
                continue

            result = self.san_cov.process_binary_from_raw(
                self.config.coverage_dir, binary_name, raw
            )

            stage_line(
                "merge",
                f"Merged raw coverage -> {display_path_for_log(result.merged_sancov)}",
            )
            stage_line(
                "merge",
                f"Symbolized -> {display_path_for_log(result.merged_symcov)}",
            )
            stage_line("merge", "")
            stage_line("merge", result.stats_text)
            results.append(result)

        if not results:
            raise RuntimeError(
                "no binaries produced coverage (no raw .sancov inputs)"
            )
        return results

    def write_outlines(
        self,
        results: list[BinaryCoverageResult],
        run_returncode: int | None,
    ) -> None:
        sections: list[str] = []
        per_binary: dict[str, dict[str, object]] = {}
        for r in results:
            sections.append(
                f"=== {r.binary_name} ===\n"
                + r.stats_text.rstrip()
                + "\n---\n"
                + f"merged_sancov: {r.merged_sancov}\n"
                + f"merged_symcov: {r.merged_symcov}\n"
                + f"raw_sancov_count: {r.raw_sancov_count}\n"
            )
            per_binary[r.binary_name] = {
                "merged_sancov": str(r.merged_sancov),
                "merged_symcov": str(r.merged_symcov),
                "raw_sancov_count": r.raw_sancov_count,
                "stats": r.stats,
                "stats_raw": r.stats_text.strip(),
            }

        outline_txt = self.config.coverage_dir / "coverage_outline.txt"
        outline_txt.write_text("\n".join(sections).rstrip() + "\n")
        stage_line("outline", f"Outline -> {display_path_for_log(outline_txt)}")

        if self.config.outline_json is not None:
            payload = {
                "binaries": per_binary,
                "run_summary": {
                    "command": self.config.command,
                    "returncode": run_returncode,
                },
            }
            self.config.outline_json.write_text(json.dumps(payload, indent=2))
            stage_line(
                "outline",
                f"JSON outline -> {display_path_for_log(self.config.outline_json)}",
            )

    def run(self) -> int:
        """Run tests (unless skipped), then merge/symbolize and write outlines (LIT path only)."""
        self.config.coverage_dir.mkdir(parents=True, exist_ok=True)
        run_returncode = self.run_tests()
        if self.config.new_tests_dir is not None:
            return run_returncode if run_returncode is not None else 1

        results = self.process_binaries()
        self.write_outlines(results, run_returncode)
        return 0
