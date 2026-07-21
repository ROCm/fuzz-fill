"""Persist baseline run settings (lit filter and symcov source code scope)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from coverage.constants import (
    DEFAULT_LIT_FILTER,
    DEFAULT_SOURCE_CODE_FILTER,
    DEFAULT_RUN_CONFIG_FILE,
)


class RunConfig(TypedDict):
    lit_filter: str
    source_code_filter: str


def source_code_filter_from_lit_filter(lit_filter: str) -> str:
    """Map llvm-lit ``--filter=`` prefix to a symcov source-path substring."""
    parts = lit_filter.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "CodeGen":
        return f"llvm/lib/Target/{parts[1]}"
    raise ValueError(
        f"Cannot derive symcov source code filter from lit-filter {lit_filter!r}; "
        "expected a CodeGen/<target>/... prefix (e.g. CodeGen/AMDGPU)."
    )


def _is_simple_codegen_lit_filter(lit_filter: str) -> bool:
    """True when *lit_filter* is a plain CodeGen/<target>/ prefix, not a regex."""
    if any(char in lit_filter for char in "|()[]?*+^$"):
        return False
    parts = lit_filter.strip("/").split("/")
    return len(parts) >= 2 and parts[0] == "CodeGen"


def resolved_lit_filter(lit_filter: str | None) -> str:
    return lit_filter if lit_filter is not None else DEFAULT_LIT_FILTER


def resolved_source_code_filter(
    *, lit_filter: str, source_code_filter: str | None
) -> str:
    if source_code_filter is not None:
        return source_code_filter
    if _is_simple_codegen_lit_filter(lit_filter):
        return source_code_filter_from_lit_filter(lit_filter)
    return DEFAULT_SOURCE_CODE_FILTER


def build_run_config(
    *,
    lit_filter: str | None,
    source_code_filter: str | None = None,
) -> RunConfig:
    lit = resolved_lit_filter(lit_filter)
    return RunConfig(
        lit_filter=lit,
        source_code_filter=resolved_source_code_filter(
            lit_filter=lit, source_code_filter=source_code_filter
        ),
    )


def write_run_config(
    output_dir: Path,
    *,
    lit_filter: str | None,
    source_code_filter: str | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    config = build_run_config(lit_filter=lit_filter, source_code_filter=source_code_filter)
    path = output_dir / DEFAULT_RUN_CONFIG_FILE
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    return path
