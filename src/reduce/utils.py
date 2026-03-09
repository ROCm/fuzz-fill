"""Shared utilities for scripts in this folder."""
import subprocess
import os
from pathlib import PurePosixPath, Path
from urllib.parse import urlparse


def get_repo_base(script_file: str) -> Path:
    """Return the repo root (parent of the scripts/ directory)."""
    return Path(script_file).resolve().parent.parent


def get_file(llvm_project: Path, url: str) -> Path | None:
    """Resolve an llvm-project file path from a GitHub blob URL."""
    parts = PurePosixPath(urlparse(url).path).parts
    try:
        llvm_idx = parts.index("llvm", parts.index("llvm-project") + 1)
    except ValueError:
        return None
    return Path(llvm_project, *parts[llvm_idx:])


def get_line_number(url: str) -> int | None:
    """Extract line number from a GitHub blob URL fragment (e.g. L121 -> 121)."""
    fragment = urlparse(url).fragment
    if fragment.startswith("L") and fragment[1:].isdigit():
        return int(fragment[1:])
    return None

def run_one_test_with_coverage(
    llc_bin: Path,
    test_cmd: str,
    fuzzer_test_dir: Path,
    coverage_dir: Path,
) -> subprocess.CompletedProcess:
    """Run a single llc test with ASan coverage enabled."""
    cmd = [str(llc_bin)] + test_cmd.split()[1:]
    env = os.environ.copy()
    env['UBSAN_OPTIONS'] = f'coverage=1:coverage_dir={coverage_dir}'
    return subprocess.run(cmd, cwd=fuzzer_test_dir, capture_output=True, text=True, env=env)
