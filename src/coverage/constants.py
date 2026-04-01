"""Defaults for llvm-lit + SanitizerCoverage runs."""

from __future__ import annotations

import shlex

DEFAULT_LIT_FILTER = "CodeGen/AMDGPU"

# Raw and merged files use <binary>.<digits>.sancov. Merged output uses this suffix; that exact
# file is excluded when collecting raw inputs. Prefix must match the binary basename for
# sancov -symbolize (llvm/tools/sancov/sancov.cpp SancovFileRegex).
MERGED_SANCOV_SUFFIX_ID = "0"


def default_lit_command(lit_filter: str) -> str:
    return shlex.join(
        ["./bin/llvm-lit", "../llvm/test/", f"--filter={lit_filter}"]
    )
