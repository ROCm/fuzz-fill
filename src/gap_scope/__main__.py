"""CLI: classify a commit into gap-analysis scope parameters."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fuzz_fill.env import FUZZ_FILL_LLVM_REPO, path_from_flag_or_env
from gap_scope.classifier import classify_commit, scope_to_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify an LLVM commit into gap-analysis backends, tests, "
            "and allowlist (first-match-wins rules)."
        )
    )
    parser.add_argument(
        "--llvm-repo",
        type=Path,
        default=None,
        help=f"llvm-project git checkout (or set {FUZZ_FILL_LLVM_REPO}).",
    )
    parser.add_argument(
        "--commit",
        type=str,
        required=True,
        help="Commit or revision accepted by git diff-tree.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full GapScope as JSON.",
    )
    args = parser.parse_args(argv)

    repo = path_from_flag_or_env(
        args.llvm_repo, FUZZ_FILL_LLVM_REPO, flag_name="--llvm-repo"
    )
    scope = classify_commit(repo, args.commit)

    if args.json:
        sys.stdout.write(scope_to_json(scope))
        return 0

    print(f"action={scope.action}")
    print(f"rule={scope.rule}")
    print(f"backends={scope.backends}")
    print(f"tests={','.join(scope.tests)}")
    print(f"allowlist={scope.allowlist}")
    print(f"reason={scope.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
