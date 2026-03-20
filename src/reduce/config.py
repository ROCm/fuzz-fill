"""Load reduce settings from JSON (see example/config.json)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


def _resolve_relative_to_config(config_file: Path, raw: str) -> Path:
    """Absolute paths unchanged; otherwise resolve relative to the config file's directory."""
    p = Path(raw)
    if p.is_absolute():
        return p
    return (config_file.resolve().parent / p).resolve()


@dataclass(frozen=True)
class TestConfig:
    original_test: Path
    file: str
    line: int
    replacement: str | None = None
    interesting: Path | None = None


@dataclass(frozen=True)
class ReduceConfig:
    llvm_bin: Path
    output_dir: Path | None
    action: str
    test: TestConfig


def load_reduce_config(path: Path, llvm_bin_cli: Path | None = None) -> ReduceConfig:
    config_file = path.expanduser()

    with open(config_file, encoding="utf-8") as f:
        raw: dict = json.load(f)

    if "tests" in raw and isinstance(raw["tests"], dict):
        test_map = raw["tests"]
        output_dir = raw.get("output_dir")
        action = raw.get("action", "reduce")
        llvm_bin = llvm_bin_cli or raw.get("llvm_bin")
    else:
        test_map = raw
        output_dir = None
        action = "reduce"
        llvm_bin = llvm_bin_cli

    if llvm_bin is None:
        raise SystemExit(
            "llvm_bin is required: pass as second argument or set \"llvm_bin\" in config."
        )

    entries: list[TestConfig] = []
    for path_str, spec in test_map.items():
        if not isinstance(spec, dict):
            raise SystemExit(f"Invalid test entry for {path_str!r}: expected an object.")
        try:
            file = spec["file"]
            line = spec["line"]
        except KeyError as e:
            raise SystemExit(f"Test {path_str!r} missing required field: {e.args[0]}") from e
        interesting = spec.get("interesting")
        entries.append(
            TestConfig(
                original_test=_resolve_relative_to_config(config_file, path_str),
                file=file,
                line=line,
                replacement=spec.get("replacement"),
                interesting=(
                    _resolve_relative_to_config(config_file, interesting)
                    if interesting
                    else None
                ),
            )
        )

    n = len(entries)
    if n != 1:
        raise SystemExit(
            f"Config must define exactly one test (found {n}). "
            "Use a single key in the test map."
        )

    return ReduceConfig(
        llvm_bin=Path(llvm_bin),
        output_dir=Path(output_dir) if output_dir else None,
        action=action,
        test=entries[0],
    )
