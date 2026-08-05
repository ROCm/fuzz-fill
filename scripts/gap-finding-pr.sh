#!/usr/bin/env bash
# Gap finding (PR-specific): baseline -> added_lines -> target-lines.
#
# Produces commit_lines_report/target_lines_uncovered.csv — added source lines
# the baseline still does not cover. Run from fuzz-fill repo root.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${REPO_ROOT}/data/coverage_output/bb_coverage_commit_lines_170626"
TARGET_LINES_REPORT_DIR=$OUTPUT_DIR/commit_lines_report

# Faster CodeGen-only subset: FILTER=CodeGen/AMDGPU
FILTER="${FILTER:-AMDGPU}"

COMMIT=b01fe4e

# shellcheck source=scripts/lib/local-llvm-env.sh
source "${SCRIPT_DIR}/lib/local-llvm-env.sh"
# shellcheck source=scripts/lib/gap-finding-pr.sh
source "${SCRIPT_DIR}/lib/gap-finding-pr.sh"

cd "$REPO_ROOT"

setup_local_llvm_env_with_lit_failures "$REPO_ROOT" "build-amdgpu-bb/bin"

run_gap_finding_pr "$OUTPUT_DIR" "$COMMIT" "${LLVM_REPO}" "$FILTER"

echo "Uncovered PR target lines: $TARGET_LINES_REPORT_DIR/target_lines_uncovered.csv"
