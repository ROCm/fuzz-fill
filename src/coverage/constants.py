"""Defaults for llvm-lit + SanitizerCoverage runs."""

from __future__ import annotations

import shlex

DEFAULT_LIT_FILTER = "CodeGen/AMDGPU"

# Raw and merged files use <binary>.<digits>.sancov. Merged output uses this suffix; that exact
# file is excluded when collecting raw inputs. Prefix must match the binary basename for
# sancov -symbolize (llvm/tools/sancov/sancov.cpp SancovFileRegex).
MERGED_SANCOV_SUFFIX_ID = "0"

# Under ``--coverage-dir``, UBSAN writes raw ``<binary>.<pid>.sancov`` here for ``run`` and
# ``new-tests`` (when executing llc). Merged ``.<suffix>.sancov`` / ``.symcov`` stay in the
# coverage directory root (``run`` only).
RAW_SANCOV_DIRNAME = "raw_sancov"

# ``coverage new-tests`` writes under ``<parent from --coverage-dir>/NEW_TESTS_SUBDIR/``.
NEW_TESTS_SUBDIR = "new-tests"
NEW_TESTS_DEFAULT_BASELINE_CSV = "covered_either.csv"
NEW_TESTS_DEFAULT_LINE_ADDRESS_MAP_JSON = "llc.0.point_symbol_info.json"


def default_lit_command(lit_filter: str) -> str:
    return shlex.join(
        ["./bin/llvm-lit", "../llvm/test/", f"--filter={lit_filter}"]
    )
