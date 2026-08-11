"""Read candidate-test ``test.sh`` files produced by gap filling."""

from __future__ import annotations

import re
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestShInfo:
    llvm_bin: Path
    bc_path: Path
    llc_flags: tuple[str, ...]


def parse_test_sh(test_sh: Path) -> TestShInfo:
    """Parse candidate_tests/<test_name>/test.sh for llc binary, flags, and .bc path."""
    if not test_sh.is_file():
        raise FileNotFoundError(f"test.sh not found: {test_sh}")

    llc_line: str | None = None
    for raw in test_sh.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            continue
        if "/llc" in line or line.endswith("llc") or " llc " in f" {line} ":
            llc_line = line
            break

    if llc_line is None:
        raise ValueError(f"No llc invocation found in {test_sh}")

    cmd = re.sub(r"\s*>.*$", "", llc_line).strip()
    parts = shlex.split(cmd)
    if len(parts) < 2:
        raise ValueError(f"Could not parse llc command in {test_sh}: {llc_line!r}")

    llc_exe = Path(parts[0])
    if llc_exe.name != "llc":
        raise ValueError(f"Expected llc executable, got {llc_exe!r} in {test_sh}")

    bc_indices = [i for i, p in enumerate(parts) if p.endswith(".bc")]
    if len(bc_indices) != 1:
        raise ValueError(
            f"Expected exactly one .bc argument in {test_sh}, got {bc_indices!r}"
        )
    bc_idx = bc_indices[0]
    bc_path = Path(parts[bc_idx])
    if not bc_path.is_file():
        raise FileNotFoundError(f"Bitcode file from test.sh does not exist: {bc_path}")

    flags = tuple(parts[1:bc_idx])
    return TestShInfo(llvm_bin=llc_exe.parent, bc_path=bc_path, llc_flags=flags)


def copy_input_bc(test_info: TestShInfo, dest_dir: Path) -> str:
    """Copy the .bc from test.sh into dest_dir; return config input basename."""
    dest_name = test_info.bc_path.name
    shutil.copy2(test_info.bc_path, dest_dir / dest_name)
    return dest_name
