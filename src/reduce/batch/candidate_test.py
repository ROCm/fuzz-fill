"""Read candidate-test ``test.sh`` files produced by gap filling."""

from __future__ import annotations

import re
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path

_LLC_INPUT_SUFFIXES = (".bc", ".ll")
_TEST_NAME_RE = re.compile(r"test_\d+_(.+)")


@dataclass(frozen=True)
class TestShInfo:
    llvm_bin: Path
    bc_path: Path
    llc_flags: tuple[str, ...]


def _llc_command_index(parts: list[str]) -> int:
    for i, part in enumerate(parts):
        if Path(part).name == "llc":
            return i
    raise ValueError(f"No llc executable in command: {parts!r}")


def _llc_input_indices(parts: list[str], llc_idx: int) -> list[int]:
    """Indices of llc input (.ll/.bc) arguments, ignoring ``-o`` outputs."""
    indices: list[int] = []
    i = llc_idx + 1
    while i < len(parts):
        if parts[i] == "-o":
            i += 2
            continue
        if parts[i].startswith("-"):
            i += 1
            continue
        if any(parts[i].endswith(suffix) for suffix in _LLC_INPUT_SUFFIXES):
            indices.append(i)
        i += 1
    return indices


def _basename_from_test_name(test_name: str) -> str | None:
    match = _TEST_NAME_RE.match(test_name)
    return match.group(1) if match else None


def resolve_llc_input_path(
    raw: Path,
    *,
    test_sh: Path,
    test_name: str | None = None,
    corpus_dir: Path | None = None,
) -> Path:
    """Resolve the llc input path from test.sh, including Docker mount paths."""
    if raw.is_file():
        return raw.resolve()

    basenames = {raw.name}
    if test_name:
        from_test = _basename_from_test_name(test_name)
        if from_test:
            basenames.add(from_test)

    tried: list[Path] = [raw]
    for basename in basenames:
        local = test_sh.parent / basename
        tried.append(local)
        if local.is_file():
            return local.resolve()

    if corpus_dir is not None:
        for basename in basenames:
            corp = corpus_dir / basename
            tried.append(corp)
            if corp.is_file():
                return corp.resolve()

    tried_str = ", ".join(str(p) for p in tried)
    raise FileNotFoundError(
        f"LLC input file from test.sh does not exist: {raw} (tried: {tried_str})"
    )


def parse_test_sh(
    test_sh: Path,
    *,
    test_name: str | None = None,
    corpus_dir: Path | None = None,
) -> TestShInfo:
    """Parse candidate_tests/<test_name>/test.sh for llc binary, flags, and input path."""
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

    llc_idx = _llc_command_index(parts)
    llc_exe = Path(parts[llc_idx])

    input_indices = _llc_input_indices(parts, llc_idx)
    if len(input_indices) != 1:
        raise ValueError(
            f"Expected exactly one .ll/.bc input in {test_sh}, got {input_indices!r}"
        )
    input_idx = input_indices[0]
    input_path = resolve_llc_input_path(
        Path(parts[input_idx]),
        test_sh=test_sh,
        test_name=test_name,
        corpus_dir=corpus_dir,
    )

    flags = tuple(parts[llc_idx + 1 : input_idx])
    return TestShInfo(llvm_bin=llc_exe.parent, bc_path=input_path, llc_flags=flags)


def copy_input_bc(test_info: TestShInfo, dest_dir: Path) -> str:
    """Copy the llc input from test.sh into dest_dir; return config input basename."""
    dest_name = test_info.bc_path.name
    shutil.copy2(test_info.bc_path, dest_dir / dest_name)
    return dest_name
