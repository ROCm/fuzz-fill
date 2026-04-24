from __future__ import annotations

import argparse
import secrets
import sys
import time
from pathlib import Path

from cov_new.constants import (
    _COVERAGE_DIR_PREFIX_RUN,
    _COVERAGE_DIR_PREFIX_NEW_TESTS,
    _COVERAGE_DEFAULT_FOLDER_RUN,
    _COVERAGE_DEFAULT_FOLDER_NEW_TESTS,
    _NEW_TESTS_OUTPUT_IN_SANCOV_PREFIX,
)

def main():

    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(
        dest="subcmd",
        metavar="{test-suite,new-tests,diff}",
        required=True,
    )
    sub.add_parser("test-suite")
    sub.add_parser("new-tests")
    sub.add_parser("diff")

    args = parser.parse_args()

    if args.subcmd == "test-suite":
        print("Getting baseline coverage for the test suite")
    elif args.subcmd == "new-tests":
        print("Getting coverage for the new tests")
    elif args.subcmd == "diff":
        print("Getting incremental coverage for new tests relative to the baseline test suite")
    else:
        print(f"Unknown subcommand: {args.subcmd}")
        return 1


if __name__ == "__main__":
    main()
