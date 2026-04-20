#!/usr/bin/env bash
# Run the coverage pipeline described in README.md (Coverage module / TL;DR).
#
# Edit the "User configuration" block below (no command-line arguments). Optional env overrides
# (LLVM, TESTS_DIR, PREFIX, …) still work for child scripts if you export them before running.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

# ---------------------------------------------------------------------------
# User configuration — edit paths for your machine
# ---------------------------------------------------------------------------
# Directory name under <repo>/data/coverage_output/ (full path is passed to each step).
OUT_BASENAME="test_suite_full_coverage_bb_200426"

# LLVM build tree: lit --cwd and coverage --build-dir for run + new-tests.
WORK_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
BUILD_DIR="$WORK_ROOT/llvm-project/build-amdgpu-bb"
# ---------------------------------------------------------------------------

COV_DIR="$REPO_ROOT/data/coverage_output/$OUT_BASENAME"

if [[ ! -d "$BUILD_DIR" ]]; then
  echo "[full_coverage_run] ERROR: BUILD_DIR is not a directory: $BUILD_DIR" >&2
  echo "[full_coverage_run] Edit BUILD_DIR (and WORK_ROOT if needed) at the top of this script." >&2
  exit 1
fi
export BUILD_DIR="$(cd "$BUILD_DIR" && pwd)"

echo "[full_coverage_run] OUT_BASENAME=$OUT_BASENAME"
echo "[full_coverage_run] COV_DIR=$COV_DIR"
echo "[full_coverage_run] BUILD_DIR=$BUILD_DIR"
echo

"$SCRIPT_DIR/run_get_llvm_test_suite_coverage.sh" "$COV_DIR"
"$SCRIPT_DIR/run_get_joint_sancov.sh" "$COV_DIR"
"$SCRIPT_DIR/run_get_llc_line_addr_map.sh" "$COV_DIR"
"$SCRIPT_DIR/run_get_new_test_coverage.sh" "$COV_DIR"
"$SCRIPT_DIR/run_analyse_new_coverage.sh" "$COV_DIR"

echo
echo "[full_coverage_run] Done. Stacked novel lines (if any):"
echo "  $COV_DIR/new-tests/llc_test_novel_source_lines/analyse_stacked_novel_lines/all_novel_source_lines.csv"
