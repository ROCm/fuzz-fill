"""Load reduce settings from JSON (see example/config.json)."""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path

_WRAPPER_TOP_LEVEL = frozenset({"tests", "output_dir", "action"})
_TEST_SPEC_KEYS = frozenset({"file", "line", "replacement", "interesting"})


def _warn_unknown_keys(
    *,
    config_file: Path,
    keys: set[str],
    allowed: frozenset[str],
    where: str,
) -> None:
    for key in sorted(keys - allowed):
        warnings.warn(
            f"{config_file}: unknown {where} key {key!r} (ignored)",
            UserWarning,
            stacklevel=3,
        )


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


def load_reduce_config(path: Path, llvm_bin: Path) -> ReduceConfig:
    config_file = path.expanduser()

    with open(config_file, encoding="utf-8") as f:
        raw: dict = json.load(f)

    if "tests" in raw and isinstance(raw["tests"], dict):
        _warn_unknown_keys(
            config_file=config_file,
            keys=set(raw),
            allowed=_WRAPPER_TOP_LEVEL,
            where="top-level",
        )
        test_map = raw["tests"]
        output_dir = raw.get("output_dir")
        action = raw.get("action", "reduce")
    else:
        test_map = raw
        output_dir = None
        action = "reduce"

    entries: list[TestConfig] = []
    for path_str, spec in test_map.items():
        if not isinstance(spec, dict):
            raise SystemExit(f"Invalid test entry for {path_str!r}: expected an object.")
        _warn_unknown_keys(
            config_file=config_file,
            keys=set(spec),
            allowed=_TEST_SPEC_KEYS,
            where=f"test entry {path_str!r}",
        )
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
        llvm_bin=llvm_bin,
        output_dir=Path(output_dir) if output_dir else None,
        action=action,
        test=entries[0],
    )
