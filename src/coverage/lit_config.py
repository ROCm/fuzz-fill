"""Patch the LLVM build tree so lit forwards SanitizerCoverage env vars."""

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


def lit_test_suite_path(llvm_lit: Path) -> Path:
    """Build-tree test suite entry point (same path ``check-llvm`` passes to llvm-lit)."""
    return llvm_build_root(llvm_lit) / "test"


def ensure_lit_sancov_env_forwarding(llvm_lit: Path) -> Path:
    """Append fuzz-fill's lit env forwarding hook to the build site config.

    The patch is idempotent and is re-applied if CMake regenerates the file.
    """
    path = lit_site_config_path(llvm_lit)
    if not path.is_file():
        raise FileNotFoundError(
            f"LLVM lit site config not found at {path}. "
            "Expected an instrumented LLVM build containing "
            f"{LIT_SITE_CONFIG_REL} (--llvm-lit={llvm_lit})."
        )

    text = path.read_text(encoding="utf-8")
    if PATCH_MARKER in text:
        return path

    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + PATCH_SNIPPET, encoding="utf-8")
    return path
