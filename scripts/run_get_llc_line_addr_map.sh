#!/usr/bin/env bash
# Extract point_symbol_info.json from llc.0.symcov next to the coverage output root.
#
# Optional $1 = coverage output directory. Default:
#   <repo>/data/coverage_output/test_suite_full_coverage

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

DEFAULT_COV_DIR="$REPO_ROOT/data/coverage_output/test_suite_full_coverage"
COV_DIR="${1:-$DEFAULT_COV_DIR}"

# Optional: --filter "$PREFIX" (see symcov-line-map --help).
python -m coverage symcov-line-map \
      "$COV_DIR/llc.0.symcov"
