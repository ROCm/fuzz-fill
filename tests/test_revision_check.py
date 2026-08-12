"""Tests for the cross-stage revision consistency check of ``coverage target-lines``."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from coverage.revision_check import check_revision_consistency
from fuzz_fill.git_revision import read_commit_file, resolve_revision, write_commit_file

SHA_A = "a" * 40
SHA_B = "b" * 40


def _make_repo(path: Path) -> str:
    """Create a git repo with a single commit and return its revision."""
    path.mkdir(parents=True, exist_ok=True)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@e",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@e",
        "PATH": "/usr/bin:/bin",
    }
    (path / "f.txt").write_text("x\n", encoding="utf-8")
    for cmd in (
        ["git", "init", "-q"],
        ["git", "add", "f.txt"],
        ["git", "commit", "-qm", "c"],
    ):
        subprocess.run(cmd, cwd=path, env=env, check=True)
    revision = resolve_revision(path)
    assert revision is not None
    return revision


class CheckRevisionConsistencyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._repo_dir = tempfile.TemporaryDirectory()
        cls.repo = Path(cls._repo_dir.name) / "repo"
        cls.revision = _make_repo(cls.repo)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._repo_dir.cleanup()

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.baseline_dir = Path(tmp.name) / "baseline"
        self.target_dir = Path(tmp.name) / "added-lines"
        self.baseline_dir.mkdir()
        self.target_dir.mkdir()

    def _run(self, baseline_rev: str | None, target_rev: str | None, repo: Path) -> None:
        if baseline_rev is not None:
            write_commit_file(self.baseline_dir, baseline_rev)
        if target_rev is not None:
            write_commit_file(self.target_dir, target_rev)
        check_revision_consistency(
            llvm_repo=repo,
            baseline_dir=self.baseline_dir,
            target_lines_dir=self.target_dir,
        )

    def test_all_revisions_equal_passes(self) -> None:
        self._run(self.revision, self.revision, self.repo)

    def test_baseline_revision_mismatch_raises(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self._run(SHA_A, self.revision, self.repo)
        self.assertIn("Revision mismatch", str(ctx.exception))

    def test_missing_commit_file_skips_check(self) -> None:
        self._run(SHA_A, None, self.repo)

    def test_non_git_llvm_repo_skips_check(self) -> None:
        self._run(SHA_A, SHA_B, self.baseline_dir)

    def test_read_missing_commit_file_returns_none(self) -> None:
        self.assertIsNone(read_commit_file(self.baseline_dir))

    def test_resolve_revision_outside_git_returns_none(self) -> None:
        self.assertIsNone(resolve_revision(self.baseline_dir))


if __name__ == "__main__":
    unittest.main()
