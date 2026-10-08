"""Classify changed paths into gap-analysis backends, tests, and allowlist."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from gap_scope.constants import (
    ALLOWLIST_CLANG,
    ALLOWLIST_LLVM,
    ALLOWLIST_LLVM_CLANG,
    LLVM_ALL_TARGETS,
    TEST_PATH_PREFIXES,
)


@dataclass(frozen=True)
class GapScope:
    """Resolved gap-analysis scope for a set of changed files."""

    rule: int
    action: str  # "run" or "skip"
    backends: str  # "all" or "X86;AMDGPU;..."
    tests: tuple[str, ...]  # ("llvm/test",) and/or ("clang/test",)
    allowlist: str  # absolute path, or "" when skip
    reason: str


def normalize_repo_path(path: str) -> str:
    """Normalize a git path relative to llvm-project root."""
    return path.replace("\\", "/").lstrip("./")


def is_test_path(path: str) -> bool:
    """True when *path* should be ignored for rule classification."""
    return any(path.startswith(prefix) for prefix in TEST_PATH_PREFIXES)


def filter_classification_paths(paths: list[str]) -> list[str]:
    """Drop test-tree paths; return remaining normalized paths."""
    kept: list[str] = []
    for raw in paths:
        path = normalize_repo_path(raw)
        if not path or is_test_path(path):
            continue
        kept.append(path)
    return kept


def _backend_from_target_path(path: str) -> str | None:
    """Return the backend name if *path* is under llvm/lib/Target/<Backend>/."""
    prefix = "llvm/lib/Target/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :]
    if not rest:
        return None
    backend = rest.split("/", 1)[0]
    if not backend or backend not in LLVM_ALL_TARGETS:
        return None
    # Require a file under the backend directory (not Target/CMakeLists.txt alone).
    if "/" not in rest:
        return None
    return backend


def _is_clang_lib_path(path: str) -> bool:
    return path.startswith("clang/lib/")


def _is_llvm_lib_path(path: str) -> bool:
    return path.startswith("llvm/lib/")


def classify_changed_paths(paths: list[str]) -> GapScope:
    """Apply first-match-wins rules 1–4 to *paths*."""
    remaining = filter_classification_paths(paths)
    if not remaining:
        return GapScope(
            rule=4,
            action="skip",
            backends="",
            tests=(),
            allowlist="",
            reason="no non-test changes under llvm/lib or clang/lib",
        )

    backends_found: list[str] = []
    all_backend_only = True
    for path in remaining:
        backend = _backend_from_target_path(path)
        if backend is None:
            all_backend_only = False
            break
        if backend not in backends_found:
            backends_found.append(backend)

    if all_backend_only and backends_found:
        targets = ["X86"]
        for backend in sorted(backends_found):
            if backend not in targets:
                targets.append(backend)
        return GapScope(
            rule=1,
            action="run",
            backends=";".join(targets),
            tests=("llvm/test",),
            allowlist=str(ALLOWLIST_LLVM.resolve()),
            reason=(
                "backend-only changes under llvm/lib/Target/"
                f"{{{','.join(sorted(backends_found))}}}/"
            ),
        )

    if all(_is_clang_lib_path(path) for path in remaining):
        return GapScope(
            rule=2,
            action="run",
            backends="all",
            tests=("clang/test",),
            allowlist=str(ALLOWLIST_CLANG.resolve()),
            reason="changes only under clang/lib/",
        )

    if any(_is_llvm_lib_path(path) or _is_clang_lib_path(path) for path in remaining):
        return GapScope(
            rule=3,
            action="run",
            backends="all",
            tests=("llvm/test", "clang/test"),
            allowlist=str(ALLOWLIST_LLVM_CLANG.resolve()),
            reason="changes under llvm/lib/ and/or clang/lib/",
        )

    return GapScope(
        rule=4,
        action="skip",
        backends="",
        tests=(),
        allowlist="",
        reason="no matching llvm/lib or clang/lib changes",
    )


def list_changed_paths(
    repo: Path,
    commit: str,
) -> list[str]:
    """Return paths changed by *commit* via ``git diff-tree --name-only``.

    ``--root`` includes the initial commit, which otherwise diffs against nothing.
    """
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "--root",
            "--first-parent",
            commit,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def classify_commit(repo: Path, commit: str) -> GapScope:
    """Classify *commit* in *repo*."""
    return classify_changed_paths(list_changed_paths(repo, commit))


def scope_to_json(scope: GapScope) -> str:
    """Serialize *scope* as JSON (tests as a list)."""
    data = asdict(scope)
    data["tests"] = list(scope.tests)
    return json.dumps(data, indent=2) + "\n"
