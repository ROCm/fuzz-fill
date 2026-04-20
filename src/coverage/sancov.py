"""SanitizerCoverage merge, symbolize, and stats via llvm sancov."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from coverage.constants import MERGED_SANCOV_SUFFIX_ID

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
        """Raw ``<binary>.<digits>.sancov`` only; skips the reserved merged filename."""
        pat = re.compile(rf"^{re.escape(binary_name)}\.\d+\.sancov$")
        merged_name = f"{binary_name}.{self.merged_suffix_id}.sancov"
        return sorted(
            p
            for p in coverage_dir.iterdir()
            if p.is_file() and pat.match(p.name) and p.name != merged_name
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
        """Merge raw ``.sancov`` files with repeated ``sancov -union`` (batched)."""
        if not raw_files:
            raise FileNotFoundError(
                f"No raw <binary>.<digits>.sancov inputs to merge under {merged_out.parent}"
            )
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
