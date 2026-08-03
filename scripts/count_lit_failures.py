#!/usr/bin/env python3
"""Count LIT tests with failure-like result codes in a lit_failures.json report."""

import argparse
import json

FAILURE_CODES = frozenset({"FAIL", "TIMEOUT", "UNRESOLVED", "XPASS"})


def count_failures(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return 0
    return sum(1 for t in data.get("tests", []) if t.get("code") in FAILURE_CODES)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lit_failures_json", help="Path to lit_failures.json from coverage baseline")
    args = parser.parse_args()
    print(count_failures(args.lit_failures_json))


if __name__ == "__main__":
    main()
