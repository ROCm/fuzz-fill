"""SanitizerCoverage merge, symbolize, and stats via llvm sancov."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from coverage.constants import MERGED_SANCOV_SUFFIX_ID
from coverage.merge import collect_sancov_files, union_sancov_batched

_STATS_RE = re.compile(
    r"^(all-edges|cov-edges|all-functions|cov-functions):\s*(\d+)\s*$", re.MULTILINE
)


def _parse_stats_text(stats_stdout: str) -> dict[str, int]:
    """Parse sancov ``-print-coverage-stats`` stdout into a small dict."""
    out: dict[str, int] = {}
    for m in _STATS_RE.finditer(stats_stdout):
        key = m.group(1).replace("-", "_")
        out[key] = int(m.group(2))
    return out


@dataclass(frozen=True)
class BinaryCoverageResult:
    binary_name: str
    merged_sancov: Path
    merged_symcov: Path
    raw_sancov_count: int
    stats_text: str
    stats: dict[str, int]


class SanCov:
    """Drive llvm ``sancov`` for one build tree (``build/.../bin``)."""

    def __init__(
        self,
        build_bin_dir: Path,
        *,
        merged_suffix_id: str = MERGED_SANCOV_SUFFIX_ID,
        union_batch: int = 200,
    ) -> None:
        self.build_bin_dir = Path(build_bin_dir)
        self.merged_suffix_id = merged_suffix_id
        self.union_batch = union_batch

    @property
    def sancov_bin(self) -> Path:
        return self.build_bin_dir / "sancov"

    def tool_binary(self, name: str) -> Path:
        return self.build_bin_dir / name

    def collect_raw(self, coverage_dir: Path, binary_name: str) -> list[Path]:
        return collect_sancov_files(
            coverage_dir, binary_name, self.merged_suffix_id
        )

    def unique_addresses_from_print(self, sancov_file: Path) -> set[str]:
        """
        Run ``sancov --print`` on a ``.sancov`` file and return unique address lines as strings.
        """
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

    def merge_to(
        self,
        raw_files: list[Path],
        merged_out: Path,
    ) -> None:
        union_sancov_batched(
            self.sancov_bin, raw_files, merged_out, self.union_batch
        )

    def symbolize(
        self,
        merged_sancov: Path,
        instrumented_binary: Path,
        symcov_out: Path,
    ) -> None:
        with symcov_out.open("w") as f:
            subprocess.run(
                [
                    str(self.sancov_bin),
                    "-symbolize",
                    str(merged_sancov),
                    str(instrumented_binary),
                ],
                check=True,
                stdout=f,
            )

    def print_stats(
        self,
        merged_sancov: Path,
        instrumented_binary: Path,
    ) -> str:
        proc = subprocess.run(
            [
                str(self.sancov_bin),
                "-print-coverage-stats",
                str(merged_sancov),
                str(instrumented_binary),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return proc.stdout

    def process_binary_from_raw(
        self,
        coverage_dir: Path,
        binary_name: str,
        raw_files: list[Path],
    ) -> BinaryCoverageResult:
        """Merge given raw files, symbolize, and collect stats."""
        tool = self.tool_binary(binary_name)
        merged_sancov = (
            coverage_dir / f"{binary_name}.{self.merged_suffix_id}.sancov"
        )
        self.merge_to(raw_files, merged_sancov)

        symcov_path = (
            coverage_dir / f"{binary_name}.{self.merged_suffix_id}.symcov"
        )
        self.symbolize(merged_sancov, tool, symcov_path)

        stats_text = self.print_stats(merged_sancov, tool)
        return BinaryCoverageResult(
            binary_name=binary_name,
            merged_sancov=merged_sancov,
            merged_symcov=symcov_path,
            raw_sancov_count=len(raw_files),
            stats_text=stats_text,
            stats=_parse_stats_text(stats_text),
        )

    def process_binary(
        self,
        coverage_dir: Path,
        binary_name: str,
    ) -> BinaryCoverageResult | None:
        """
        Merge raw ``binary_name.<digits>.sancov``, symbolize, and collect stats.

        Returns None if there are no raw files for this binary.
        """
        raw = self.collect_raw(coverage_dir, binary_name)
        if not raw:
            return None
        return self.process_binary_from_raw(coverage_dir, binary_name, raw)
