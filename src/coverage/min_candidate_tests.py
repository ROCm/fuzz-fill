# Greedy minimal selection of candidate-test runs by instrumentation point coverage.

from __future__ import annotations

import asyncio
import csv
import os
from dataclasses import dataclass
from pathlib import Path

from coverage.analyser import get_sancov_file
from coverage.candidate_test_settings import (
    LLC_FLAGS_COLUMN,
    MANIFEST_COLUMNS,
)
from coverage.constants import (
    DEFAULT_CANDIDATE_TEST_MANIFEST_FILE,
    DEFAULT_CANDIDATE_TEST_SETTINGS_FILE,
    DEFAULT_MIN_CANDIDATE_TESTS_BATCH_SIZE,
    DEFAULT_MIN_CANDIDATE_TESTS_CSV,
    DEFAULT_MIN_CANDIDATE_TESTS_POINTS_CSV,
    DEFAULT_MIN_CANDIDATE_TESTS_SOURCE_FILES_CSV,
)
from coverage.sancov import Sancov
from fuzz_fill.log import get_logger, log_timing

logger = get_logger("coverage.min_candidate_tests")


@dataclass(frozen=True)
class ManifestRow:
    test_id: str
    source_file: Path
    llc_flags: str
    test_dir: str


@dataclass(frozen=True)
class RunRecord:
    row: ManifestRow
    sancov_file: Path


@dataclass
class RunWithAddresses:
    run: RunRecord
    addresses: set[str]


@dataclass
class KeptRun:
    row: ManifestRow
    sancov_file: Path


@dataclass
class SelectionResult:
    selected: list[KeptRun]
    accumulated: set[str]


def load_manifest(output_dir: Path) -> list[ManifestRow]:
    path = output_dir / DEFAULT_CANDIDATE_TEST_MANIFEST_FILE
    if not path.is_file():
        raise FileNotFoundError(
            f"candidate test manifest not found: {path} "
            f"(expected output of `coverage candidate-test`)"
        )

    rows: list[ManifestRow] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"empty manifest CSV: {path}")
        missing = set(MANIFEST_COLUMNS) - set(reader.fieldnames)
        if missing:
            raise ValueError(f"{path}: missing manifest columns: {sorted(missing)}")

        for line_no, raw in enumerate(reader, start=2):
            rows.append(
                ManifestRow(
                    test_id=raw["test_id"],
                    source_file=Path(raw["source_file"]),
                    llc_flags=raw["llc_flags"],
                    test_dir=raw["test_dir"],
                )
            )
            if not raw["test_dir"]:
                raise ValueError(f"{path}: blank test_dir on line {line_no}")

    return rows


def require_settings_csv(output_dir: Path) -> None:
    path = output_dir / DEFAULT_CANDIDATE_TEST_SETTINGS_FILE
    if not path.is_file():
        raise FileNotFoundError(
            f"candidate test settings not found: {path} "
            f"(expected output of `coverage candidate-test`)"
        )
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or LLC_FLAGS_COLUMN not in reader.fieldnames:
            raise ValueError(f"{path}: expected column {LLC_FLAGS_COLUMN!r}")


def discover_runs(
    candidate_tests_output_dir: Path,
    manifest: list[ManifestRow],
) -> list[RunRecord]:
    runs: list[RunRecord] = []
    for row in manifest:
        test_dir = candidate_tests_output_dir / row.test_dir
        if not test_dir.is_dir():
            logger.warning("manifest test_dir missing, skipping: %s", row.test_dir)
            continue
        sancov_file = get_sancov_file(test_dir)
        if sancov_file is None:
            continue
        runs.append(RunRecord(row=row, sancov_file=sancov_file))
    return runs


async def _print_addresses(
    run: RunRecord,
    sancov_bin: Path,
    sem: asyncio.Semaphore,
) -> RunWithAddresses:
    async with sem:
        proc = await asyncio.create_subprocess_exec(
            str(sancov_bin),
            "--print",
            str(run.sancov_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err = (stderr or stdout or b"").decode(errors="replace").strip()
            raise RuntimeError(
                f"sancov --print failed for {run.sancov_file}: {err or proc.returncode}"
            )
        text = stdout.decode(errors="replace")
        return RunWithAddresses(
            run=run,
            addresses=Sancov.parse_print_output(text),
        )


async def load_batch_addresses(
    runs: list[RunRecord],
    sancov_bin: Path,
    jobs: int,
) -> list[RunWithAddresses]:
    sem = asyncio.Semaphore(jobs)
    tasks = [
        asyncio.create_task(_print_addresses(run, sancov_bin, sem)) for run in runs
    ]
    results: list[RunWithAddresses] = []
    for idx, task in enumerate(asyncio.as_completed(tasks), start=1):
        results.append(await task)
        if idx % 100 == 0 or idx == len(runs):
            logger.info("sancov --print batch progress: %d / %d", idx, len(runs))
    return results


async def run_batched_selection(
    runs: list[RunRecord],
    sancov_bin: Path,
    *,
    jobs: int,
    batch_size: int,
) -> SelectionResult:
    ordered = sorted(runs, key=lambda r: str(r.sancov_file))
    accumulated: set[str] = set()
    selected: list[KeptRun] = []
    total_batches = (len(ordered) + batch_size - 1) // batch_size

    for batch_idx, start in enumerate(range(0, len(ordered), batch_size), start=1):
        batch = ordered[start : start + batch_size]
        batch_addrs = await load_batch_addresses(batch, sancov_bin, jobs)
        batch_addrs.sort(key=lambda item: str(item.run.sancov_file))

        for item in batch_addrs:
            new_addrs = item.addresses - accumulated
            if not new_addrs:
                continue
            accumulated |= item.addresses
            selected.append(
                KeptRun(
                    row=item.run.row,
                    sancov_file=item.run.sancov_file,
                )
            )

        end = start + len(batch)
        logger.info(
            "batch %d/%d: %d/%d runs processed, %d kept so far, %d points",
            batch_idx,
            total_batches,
            end,
            len(ordered),
            len(selected),
            len(accumulated),
        )

    return SelectionResult(selected=selected, accumulated=accumulated)


def write_kept_runs_csv(path: Path, selected: list[KeptRun]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_file",
        "llc_flags",
        "test_dir",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for kept in selected:
            writer.writerow(
                {
                    "source_file": str(kept.row.source_file),
                    "llc_flags": kept.row.llc_flags,
                    "test_dir": kept.row.test_dir,
                }
            )


def write_points_csv(path: Path, accumulated: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["point"])
        for point in sorted(accumulated):
            writer.writerow([point])


def write_unique_source_files_csv(path: Path, selected: list[KeptRun]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    unique = sorted({str(kept.row.source_file) for kept in selected})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source_file"])
        for source_file in unique:
            writer.writerow([source_file])


class MinCandidateTestsSelector:
    def __init__(
        self,
        *,
        candidate_tests_output_dir: Path,
        output_dir: Path,
        sancov_bin: Path,
        jobs: int | None = None,
        batch_size: int = DEFAULT_MIN_CANDIDATE_TESTS_BATCH_SIZE,
        kept_csv_name: str = DEFAULT_MIN_CANDIDATE_TESTS_CSV,
        points_csv_name: str = DEFAULT_MIN_CANDIDATE_TESTS_POINTS_CSV,
        source_files_csv_name: str = DEFAULT_MIN_CANDIDATE_TESTS_SOURCE_FILES_CSV,
    ) -> None:
        self.candidate_tests_output_dir = candidate_tests_output_dir.resolve()
        self.output_dir = output_dir.resolve()
        self.sancov_bin = sancov_bin
        self.jobs = max(1, jobs if jobs is not None else (os.cpu_count() or 1))
        self.batch_size = max(1, batch_size)
        self.kept_csv_path = self.output_dir / kept_csv_name
        self.points_csv_path = self.output_dir / points_csv_name
        self.source_files_csv_path = self.output_dir / source_files_csv_name

    def run(self) -> SelectionResult:
        with log_timing(logger, "min-candidate-tests"):
            manifest = load_manifest(self.candidate_tests_output_dir)
            require_settings_csv(self.candidate_tests_output_dir)
            runs = discover_runs(self.candidate_tests_output_dir, manifest)

            logger.info(
                "discovered %d runs with sancov (from %d manifest rows)",
                len(runs),
                len(manifest),
            )

            if not runs:
                logger.warning("no runs with sancov; writing empty output CSVs")
                write_kept_runs_csv(self.kept_csv_path, [])
                write_points_csv(self.points_csv_path, set())
                write_unique_source_files_csv(self.source_files_csv_path, [])
                return SelectionResult(selected=[], accumulated=set())

            logger.info(
                "batched selection for %d runs (batch_size=%d, -j=%d)",
                len(runs),
                self.batch_size,
                self.jobs,
            )

            with log_timing(logger, "batched sancov --print + greedy"):
                result = asyncio.run(
                    run_batched_selection(
                        runs,
                        self.sancov_bin,
                        jobs=self.jobs,
                        batch_size=self.batch_size,
                    )
                )

            logger.info(
                "kept %d of %d runs (%d instrumentation points)",
                len(result.selected),
                len(runs),
                len(result.accumulated),
            )

            self.output_dir.mkdir(parents=True, exist_ok=True)
            write_kept_runs_csv(self.kept_csv_path, result.selected)
            write_points_csv(self.points_csv_path, result.accumulated)
            write_unique_source_files_csv(self.source_files_csv_path, result.selected)
            logger.info("wrote %s", self.kept_csv_path)
            logger.info("wrote %s", self.points_csv_path)
            logger.info("wrote %s", self.source_files_csv_path)

            return result
