"""Shared utilities for scripts in this folder."""
import subprocess
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


def abort_at_line(info: dict) -> None:
    """Replace the line in info['file'] at info['line'] with info['replace']."""
    path = info["file"]
    line = info["line"]
    replacement_line = info["replace"]
    lines = path.read_text().splitlines(keepends=True)
    idx = line - 1
    lines[idx] = replacement_line
    path.write_text("".join(lines))
    cmd = ["git", "diff", path]
    result = subprocess.run(cmd, cwd=path.parent, capture_output=True, text=True)
    if result.stdout == "":
        raise RuntimeError("File not modified!")
