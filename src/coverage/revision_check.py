"""Record the baseline revision and cross-check it against later stages."""

from __future__ import annotations

from pathlib import Path

from coverage.lit_config import llvm_source_root
from fuzz_fill.git_revision import (
    commit_file_path,
    read_commit_file,
    resolve_revision,
    write_commit_file,
)
from fuzz_fill.log import get_logger

logger = get_logger("coverage.revision_check")


def record_baseline_revision(llvm_lit: Path, output_dir: Path) -> None:
    """Record the revision of the LLVM source tree the baseline was run against.

    The tree is the one configured in the build's ``lit.site.cfg.py``. Nothing
    is recorded when it cannot be located or is not a git checkout.
    """
    try:
        source_root = llvm_source_root(llvm_lit)
    except (FileNotFoundError, ValueError) as e:
        logger.info("not recording the baseline revision: %s", e)
        return

    revision = resolve_revision(source_root)
    if revision is None:
        logger.info(
            "not recording the baseline revision, %s is not a git checkout",
            source_root,
        )
        return

    path = write_commit_file(output_dir, revision)
    logger.info("recorded baseline revision %s in %s", revision, path)


def check_revision_consistency(
    *,
    llvm_repo: Path,
    baseline_dir: Path,
    target_lines_dir: Path,
) -> None:
    """Fail when baseline, target lines and ``--llvm-repo`` are different revisions.

    ``coverage baseline`` and ``added_lines`` record their revision in a
    ``COMMIT`` file next to their outputs. The check is skipped when either file
    is missing (artifacts from an older run, or a baseline built from a
    non-git source tree).
    """
    baseline_revision = read_commit_file(baseline_dir)
    target_revision = read_commit_file(target_lines_dir)
    if baseline_revision is None or target_revision is None:
        logger.info(
            "skipping the revision check, no recorded revision in %s / %s",
            commit_file_path(baseline_dir),
            commit_file_path(target_lines_dir),
        )
        return

    repo_revision = resolve_revision(llvm_repo)
    if repo_revision is None:
        logger.warning(
            "skipping the revision check, cannot resolve HEAD of --llvm-repo %s",
            llvm_repo,
        )
        return

    revisions = {
        "baseline": baseline_revision,
        "target lines": target_revision,
        "--llvm-repo HEAD": repo_revision,
    }
    if len(set(revisions.values())) == 1:
        logger.info("revision check passed (%s)", repo_revision)
        return

    details = "\n".join(f"  {name}: {rev}" for name, rev in revisions.items())
    raise SystemExit(
        "Revision mismatch between pipeline stages:\n"
        f"{details}\n"
        "Re-run `coverage baseline` and `added_lines` against the same revision, "
        "or pass --no-commit-check to skip this check."
    )
