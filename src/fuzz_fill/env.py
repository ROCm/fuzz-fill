"""Environment-variable fallbacks for LLVM path CLI flags."""

from __future__ import annotations

import os
from pathlib import Path

FUZZ_FILL_LLVM_BIN = "FUZZ_FILL_LLVM_BIN"
FUZZ_FILL_LLVM_INSTRUMENTED_BIN = "FUZZ_FILL_LLVM_INSTRUMENTED_BIN"
FUZZ_FILL_LLVM_REPO = "FUZZ_FILL_LLVM_REPO"


def path_from_flag_or_env(
    value: Path | None,
    env_var: str,
    *,
    flag_name: str,
) -> Path:
    """Resolve a directory path from a CLI flag or environment variable."""
    if value is not None:
        return value.expanduser().resolve()

    raw = os.environ.get(env_var)
    if raw:
        return Path(raw).expanduser().resolve()

    raise SystemExit(f"{flag_name} is required (or set {env_var}).")
