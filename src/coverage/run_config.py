"""Persist and load test-suite run settings (lit filter → symcov path filter)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from coverage.constants import DEFAULT_LIT_FILTER, DEFAULT_RUN_CONFIG_FILE


class RunConfig(TypedDict):
    lit_filter: str
    path_filter: str


def path_filter_from_lit_filter(lit_filter: str) -> str:
    """Map llvm-lit ``--filter=`` prefix to a symcov source-path substring."""
    parts = lit_filter.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "CodeGen":
        return f"llvm/lib/Target/{parts[1]}"
    raise ValueError(
        f"Cannot derive symcov path filter from lit-filter {lit_filter!r}; "
        "expected a CodeGen/<target>/... prefix (e.g. CodeGen/AMDGPU)."
    )


def resolved_lit_filter(lit_filter: str | None) -> str:
    return lit_filter if lit_filter is not None else DEFAULT_LIT_FILTER


def build_run_config(*, lit_filter: str | None) -> RunConfig:
    lit = resolved_lit_filter(lit_filter)
    return RunConfig(lit_filter=lit, path_filter=path_filter_from_lit_filter(lit))


def write_run_config(output_dir: Path, *, lit_filter: str | None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    config = build_run_config(lit_filter=lit_filter)
    path = output_dir / DEFAULT_RUN_CONFIG_FILE
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    return path


def load_run_config(test_suite_output_dir: Path) -> RunConfig:
    path = test_suite_output_dir / DEFAULT_RUN_CONFIG_FILE
    if not path.is_file():
        raise SystemExit(
            f"Missing {path}. Run ``coverage test-suite`` first (same "
            f"--output-dir / --test-suite-output-dir) so run_config.json is written."
        )
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    for key in ("lit_filter", "path_filter"):
        if key not in data or not isinstance(data[key], str) or not data[key]:
            raise SystemExit(f"Invalid {path}: expected non-empty string {key!r}.")
    return RunConfig(lit_filter=data["lit_filter"], path_filter=data["path_filter"])
