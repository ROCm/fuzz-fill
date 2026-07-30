"""Patch the LLVM build tree so lit forwards SanitizerCoverage env vars."""

from __future__ import annotations

import os
import re
from pathlib import Path

from coverage.constants import (
    BASELINE_LIT_PRIORITY_ELAPSED,
    DEFAULT_LIT_FILTER_DIRS,
    MAX_LIT_JOBS,
)

LIT_SITE_CONFIG_REL = Path("test/lit.site.cfg.py")
LIT_TEST_TIMES_NAME = ".lit_test_times.txt"
PATCH_MARKER = "# fuzz-fill: SanitizerCoverage env forwarding"
_LLVM_SRC_ROOT_RE = re.compile(
    r"""config\.llvm_src_root\s*=\s*path\(r(?P<quote>["'])(?P<path>.+?)(?P=quote)\)"""
)

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


def lit_test_times_path(llvm_lit: Path) -> Path:
    """``test/.lit_test_times.txt`` in the instrumented LLVM build (lit exec_root)."""
    return lit_test_suite_path(llvm_lit) / LIT_TEST_TIMES_NAME


def _resolve_lit_site_path(site_cfg: Path, configured_path: str) -> Path:
    """Resolve a ``path(...)`` value from ``lit.site.cfg.py`` like upstream lit."""
    if not configured_path:
        return Path()

    site_cfg = site_cfg.resolve()
    candidate = Path(configured_path)
    if candidate.is_absolute():
        return Path(os.path.realpath(candidate))
    return Path(os.path.realpath(site_cfg.parent / configured_path))


def llvm_test_source_root(llvm_lit: Path) -> Path:
    """``llvm/test`` in the LLVM source tree configured by ``lit.site.cfg.py``."""
    site_cfg = lit_site_config_path(llvm_lit)
    if not site_cfg.is_file():
        raise FileNotFoundError(
            f"LLVM lit site config not found at {site_cfg}. "
            "Expected an instrumented LLVM build containing "
            f"{LIT_SITE_CONFIG_REL} (--llvm-lit={llvm_lit})."
        )

    match = _LLVM_SRC_ROOT_RE.search(site_cfg.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(
            f"Could not parse config.llvm_src_root from {site_cfg}. "
            "Expected a generated lit.site.cfg.py from an LLVM build."
        )
    llvm_src_root = _resolve_lit_site_path(site_cfg, match.group("path"))
    return llvm_src_root / "test"


def filter_existing_lit_priority_tests(
    llvm_lit: Path,
    priority_tests: tuple[str, ...],
) -> tuple[str, ...]:
    """Return ``path_in_suite`` entries that exist under ``llvm/test``."""
    source_root = llvm_test_source_root(llvm_lit)
    existing: list[str] = []
    missing: list[str] = []
    for path_in_suite in priority_tests:
        if (source_root / path_in_suite).is_file():
            existing.append(path_in_suite)
        else:
            missing.append(path_in_suite)

    if missing:
        print(
            "warning: skipping lit priority scheduling for missing test(s):\n  "
            + "\n  ".join(missing),
            flush=True,
        )
    return tuple(existing)


def _read_lit_test_times(path: Path) -> dict[str, float]:
    """Parse llvm-lit timing file (``<seconds> <path_in_suite>`` per line)."""
    if not path.is_file():
        return {}

    times: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2:
            continue
        time_str, test_path = fields
        try:
            times[test_path.strip()] = float(time_str)
        except ValueError:
            continue
    return times


def _write_lit_test_times(path: Path, times: dict[str, float]) -> None:
    """Write llvm-lit timing file using the same ``%e`` format as upstream lit."""
    lines = [f"{elapsed:e} {name}" for name, elapsed in sorted(times.items())]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def seed_lit_priority_test_times(
    llvm_lit: Path,
    priority_tests: tuple[str, ...],
    *,
    priority_elapsed: float = BASELINE_LIT_PRIORITY_ELAPSED,
) -> Path:
    """Boost priority tests in ``.lit_test_times.txt`` for smart lit ordering.

    llvm-lit ``--order=smart`` (the default) sorts by descending
    ``previous_elapsed``. Seeding high values on cold runs front-loads the
    slowest tests under parallel ``-j``.
    """
    path = lit_test_times_path(llvm_lit)
    path.parent.mkdir(parents=True, exist_ok=True)

    times = _read_lit_test_times(path)
    for test_path in priority_tests:
        times[test_path] = max(times.get(test_path, 0.0), priority_elapsed)

    _write_lit_test_times(path, times)
    return path


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


def default_lit_job_count() -> int:
    """Match llvm-lit's default worker count (``lit.util.usable_core_count``)."""
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:
        return os.cpu_count() or 1


def resolve_lit_job_count(requested: int | None, *, max_jobs: int = MAX_LIT_JOBS) -> int:
    """Resolve llvm-lit ``-j`` value, capping at *max_jobs* when needed."""
    effective = requested if requested is not None else default_lit_job_count()
    effective = max(1, effective)
    if effective > max_jobs:
        print(
            f"warning: capping llvm-lit -j from {effective} to {max_jobs} "
            "to work around high core-count issues in Docker",
            flush=True,
        )
        return max_jobs
    return effective


def build_lit_filter_regex(lit_filters: list[str]) -> str:
    """Combine one or more llvm-lit ``--filter=`` regex fragments."""
    normalized = [prefix.strip().strip("/") for prefix in lit_filters if prefix.strip().strip("/")]
    if not normalized:
        raise ValueError("lit_filters must not be empty")
    if len(normalized) == 1:
        return normalized[0]
    return "|".join(normalized)


def resolved_lit_filter(lit_filters: list[str] | None) -> str:
    filters = lit_filters if lit_filters else DEFAULT_LIT_FILTER_DIRS
    return build_lit_filter_regex(filters)
