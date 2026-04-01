"""Collect raw .sancov files and batched sancov -union."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from coverage.constants import MERGED_SANCOV_SUFFIX_ID


def collect_sancov_files(
    coverage_dir: Path,
    binary_name: str,
    merged_suffix_id: str = MERGED_SANCOV_SUFFIX_ID,
) -> list[Path]:
    """Raw <binary_name>.<digits>.sancov only; skips reserved merged name."""
    pat = re.compile(rf"^{re.escape(binary_name)}\.\d+\.sancov$")
    merged_name = f"{binary_name}.{merged_suffix_id}.sancov"
    return sorted(
        p
        for p in coverage_dir.iterdir()
        if p.is_file() and pat.match(p.name) and p.name != merged_name
    )


def union_sancov_batched(
    sancov_bin: Path,
    files: list[Path],
    output: Path,
    batch_size: int,
) -> None:
    """Merge many raw .sancov files using repeated sancov -union (batched)."""
    if not files:
        raise FileNotFoundError(
            f"No raw <binary>.<digits>.sancov inputs to merge under {output.parent}"
        )
    if len(files) == 1:
        shutil.copy(files[0], output)
        return

    layer = list(files)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        tmp_path = Path(tmp)
        round_idx = 0
        while len(layer) > 1:
            nxt: list[Path] = []
            for i in range(0, len(layer), batch_size):
                batch = layer[i : i + batch_size]
                if len(batch) == 1:
                    nxt.append(batch[0])
                    continue
                out_f = tmp_path / f"u_{round_idx}_{len(nxt)}.sancov"
                cmd = [str(sancov_bin), "-union"] + [str(p) for p in batch] + [
                    "--output",
                    str(out_f),
                ]
                subprocess.run(cmd, check=True)
                nxt.append(out_f)
            layer = nxt
            round_idx += 1
        shutil.copy(layer[0], output)
