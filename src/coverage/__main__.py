"""CLI entry for ``python -m coverage`` (requires this package's ``coverage`` on ``sys.path`` first)."""

from __future__ import annotations

from coverage.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
