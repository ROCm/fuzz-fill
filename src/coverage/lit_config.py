"""Helpers for source-baseline lit filters and integration-test env forwarding."""

from __future__ import annotations

from pathlib import Path

LIT_SITE_CONFIG_REL = Path("test/lit.site.cfg.py")
PATCH_MARKER = "# fuzz-fill: SanitizerCoverage env forwarding"

PATCH_SNIPPET = f"""
{PATCH_MARKER}
# Appended by fuzz-fill (src/coverage/lit_config.py). Re-applied after CMake
# regenerates this file. Forwards coverage variables from the llvm-lit process
# into every test subprocess.
import os as _fuzz_fill_os
for _fuzz_fill_name in ("UBSAN_OPTIONS",):
    _fuzz_fill_val = _fuzz_fill_os.environ.get(_fuzz_fill_name)
    if _fuzz_fill_val:
        config.environment[_fuzz_fill_name] = _fuzz_fill_val
"""


def llvm_build_root(llvm_lit: Path) -> Path:
    """Top of the instrumented LLVM build tree (parent of ``bin/``)."""
    return llvm_lit.resolve().parent.parent


def lit_site_config_path(llvm_lit: Path) -> Path:
    """``test/lit.site.cfg.py`` for the instrumented LLVM build."""
    return llvm_build_root(llvm_lit) / LIT_SITE_CONFIG_REL


def ensure_lit_sancov_env_forwarding(
    llvm_lit: Path,
    *,
    site_cfg: Path | None = None,
) -> Path:
    """Append fuzz-fill's lit env forwarding hook to a build site config.

    The patch is idempotent and is re-applied if CMake regenerates the file.
    Defaults to the llvm ``test/lit.site.cfg.py``.
    """
    path = site_cfg if site_cfg is not None else lit_site_config_path(llvm_lit)
    if not path.is_file():
        raise FileNotFoundError(
            f"LLVM lit site config not found at {path}. "
            "Expected an instrumented LLVM build containing "
            f"{path.relative_to(llvm_build_root(llvm_lit))} (--llvm-lit={llvm_lit})."
        )

    text = path.read_text(encoding="utf-8")
    if PATCH_MARKER in text:
        return path

    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + PATCH_SNIPPET, encoding="utf-8")
    return path


def build_lit_filter_regex(lit_filters: list[str]) -> str:
    """Combine one or more llvm-lit ``--filter=`` regex fragments."""
    normalized = [
        prefix.strip().strip("/")
        for prefix in lit_filters
        if prefix.strip().strip("/")
    ]
    if not normalized:
        raise ValueError("lit_filters must not be empty")
    if len(normalized) == 1:
        return normalized[0]
    return "|".join(normalized)
