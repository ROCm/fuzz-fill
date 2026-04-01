"""
LLVM SanitizerCoverage helpers: merge raw ``*.sancov``, symbolize, and outlines.

This package is named ``coverage`` and can shadow PyPI ``coverage`` if both are importable;
put this repo's ``src`` first on ``PYTHONPATH``, or use a venv without the PyPI package.

Run the CLI as ``python -m coverage`` (with ``src`` on the path or after ``pip install -e .``),
or ``llvm-test-suite-coverage``, or ``scripts/get_llvm_test_suite_coverage.py`` (shim that
prepends ``src``).
"""

from __future__ import annotations

from coverage.config import CoverageConfig
from coverage.constants import (
    DEFAULT_LIT_FILTER,
    MERGED_SANCOV_SUFFIX_ID,
    default_lit_command,
)
from coverage.sancov import BinaryCoverageResult, SanCov
from coverage.session import CoverageSession
from coverage.runner import TestCommandRunner

__all__ = [
    "BinaryCoverageResult",
    "CoverageConfig",
    "CoverageSession",
    "DEFAULT_LIT_FILTER",
    "MERGED_SANCOV_SUFFIX_ID",
    "SanCov",
    "TestCommandRunner",
    "default_lit_command",
]
