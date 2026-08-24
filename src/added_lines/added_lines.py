from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from fuzz_fill.git_revision import resolve_revision
from fuzz_fill.log import get_logger, log_timing, run_subprocess

logger = get_logger("added_lines")


@dataclass(frozen=True)
class AddedLine:
    """One line introduced on the post-image side of a unified diff hunk."""

    path: str
    line_no: int
    text: str


_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def _verify_git_repo(repo: Path) -> None:
    r = run_subprocess(
        logger,
        ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or r.stdout.strip() != "true":
        raise SystemExit(
            f"--llvm-repo is not a git working tree (git rev-parse failed): {repo}"
        )


def _resolve_commit(repo: Path, commit: str) -> str:
    """Full hash of ``commit`` in ``repo``, or exit when it does not resolve."""
    revision = resolve_revision(repo, commit)
    if revision is None:
        raise SystemExit(f"Invalid git revision {commit!r} in {repo}")
    return revision


def git_show_patch(repo: Path, commit: str) -> str:
    r = run_subprocess(
        logger,
        [
            "git",
            "-C",
            str(repo),
            "show",
            "--first-parent",
            "--no-color",
            "--pretty=format:",
            commit,
        ],
        label="git show",
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise SystemExit(
            f"git show failed ({r.returncode}) for {commit!r} in {repo}:\n{r.stderr.strip()}"
        )
    return r.stdout


def parse_added_lines(patch: str) -> list[AddedLine]:
    """Parse a unified diff and return every added line with its new file line number."""
    out: list[AddedLine] = []
    lines = patch.splitlines()

    current_path: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("Binary files ") and " differ" in line:
            current_path = None
            i += 1
            continue

        if line.startswith("+++ "):
            # +++ b/path or +++ /dev/null
            raw = line[4:].strip()
            if raw == "/dev/null":
                current_path = None
            elif raw.startswith("b/"):
                current_path = raw[2:]
            else:
                current_path = raw
            i += 1
            continue

        if line.startswith("diff --git "):
            # Defer path to following ---/+++ when possible
            i += 1
            continue

        m = _HUNK_RE.match(line)
        if m:
            new_line = int(m.group(1))
            i += 1
            while i < len(lines):
                body = lines[i]
                if body.startswith("diff --git ") or body.startswith("--- "):
                    break
                if _HUNK_RE.match(body):
                    break
                if not body:
                    i += 1
                    continue
                tag = body[0]
                rest = body[1:]
                if tag == "\\":
                    i += 1
                    continue
                if tag == " ":
                    new_line += 1
                elif tag == "-":
                    pass
                elif tag == "+":
                    if current_path is not None:
                        out.append(
                            AddedLine(path=current_path, line_no=new_line, text=rest)
                        )
                    new_line += 1
                else:
                    # e.g. 'No newline' without prefix in malformed input; skip
                    pass
                i += 1
            continue

        i += 1

    return out


def collect_added_lines(repo: Path, commit: str) -> tuple[str, list[AddedLine]]:
    """Resolved hash of ``commit`` and the lines it adds."""
    with log_timing(logger, "collect added lines"):
        _verify_git_repo(repo)
        revision = _resolve_commit(repo, commit)
        patch = git_show_patch(repo, commit)
        return revision, parse_added_lines(patch)
