#!/usr/bin/env bash
# Gap finding (baseline): run coverage baseline over a filtered LIT slice.
#
# Produces line_coverage_uncovered.csv and llc_address_line_map.csv under
# <output-dir>/baseline/. Use scripts/gap-filling-amdgpu.sh (or gap-filling Docker)
# to find fuzz tests that cover those gaps.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${REPO_ROOT}/data/coverage_output/bb_coverage_amdgpu_230726_full_filter"
BASELINE_OUTPUT_DIR=$OUTPUT_DIR/baseline

FILTER="${FILTER:-AMDGPU}"

# shellcheck source=scripts/lib/local-llvm-env.sh
source "${SCRIPT_DIR}/lib/local-llvm-env.sh"
# shellcheck source=scripts/lib/coverage-baseline.sh
source "${SCRIPT_DIR}/lib/coverage-baseline.sh"

rm -rf "$BASELINE_OUTPUT_DIR"

cd "$REPO_ROOT"

setup_local_llvm_env_with_lit_failures "$REPO_ROOT" "build-amdgpu-bb/bin"

run_coverage_baseline "$BASELINE_OUTPUT_DIR" "$FILTER"

echo "Uncovered baseline lines: $BASELINE_OUTPUT_DIR/line_coverage_uncovered.csv"
