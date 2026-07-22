"""Environment-variable fallbacks for LLVM path CLI flags."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

FUZZ_FILL_SANCOV = "FUZZ_FILL_SANCOV"
FUZZ_FILL_LLVM_LIT = "FUZZ_FILL_LLVM_LIT"
FUZZ_FILL_LLC = "FUZZ_FILL_LLC"
FUZZ_FILL_OPT = "FUZZ_FILL_OPT"
FUZZ_FILL_LLVM_REDUCE = "FUZZ_FILL_LLVM_REDUCE"
FUZZ_FILL_LLVM_DIS = "FUZZ_FILL_LLVM_DIS"
FUZZ_FILL_LLVM_REPO = "FUZZ_FILL_LLVM_REPO"

# Per-tool env vars unset by integration-tests/test.sh before lit runs.
FUZZ_FILL_TOOL_ENV_VARS = (
    FUZZ_FILL_SANCOV,
    FUZZ_FILL_LLVM_LIT,
    FUZZ_FILL_LLC,
    FUZZ_FILL_OPT,
    FUZZ_FILL_LLVM_REDUCE,
    FUZZ_FILL_LLVM_DIS,
)


def path_from_flag_or_env(
    value: Path | None,
    env_var: str,
    *,
    flag_name: str,
) -> Path:
    """Resolve a path from a CLI flag or environment variable."""
    if value is not None:
        return value.expanduser().resolve()

    raw = os.environ.get(env_var)
    if raw:
        return Path(raw).expanduser().resolve()

    raise SystemExit(f"{flag_name} is required (or set {env_var}).")


def require_executable(path: Path, *, flag_name: str) -> Path:
    """Verify *path* exists and is executable."""
    if not path.is_file():
        raise SystemExit(f"{flag_name}: not a file: {path}")
    if not os.access(path, os.X_OK):
        raise SystemExit(f"{flag_name}: not executable: {path}")
    return path


def existing_file_path(path_str: str) -> Path:
    """Argparse type: require an existing file; return its resolved path."""
    path = Path(path_str).expanduser()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"not a file: {path}")
    return path.resolve()


def existing_dir_path(path_str: str) -> Path:
    """Argparse type: require an existing directory; return its resolved path."""
    path = Path(path_str).expanduser()
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"not a directory: {path}")
    return path.resolve()


def executable_from_flag_or_env(
    value: Path | None,
    env_var: str,
    *,
    flag_name: str,
) -> Path:
    """Resolve an executable path from a CLI flag or environment variable."""
    return require_executable(
        path_from_flag_or_env(value, env_var, flag_name=flag_name),
        flag_name=flag_name,
    )
