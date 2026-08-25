#!/usr/bin/env bash
# Gap-filling pipeline steps: candidate-test and incremental.
# Source from entrypoints or other scripts/lib modules; do not execute directly.
#
# Optional env (local runs):
#   COVERAGE_SANCOV, COVERAGE_LLC
#   JOBS

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
# shellcheck source=scripts/lib/common.sh
source "${LIB_DIR}/common.sh"

run_candidate_test() {
    local output_dir="$1"
    local candidate_tests_dir="$2"
    local n="$3"
    local settings_csv="${4:-}"

    local -a args=(
        python -m coverage candidate-test
        --output-dir "$output_dir"
        --candidate-tests-dir "$candidate_tests_dir"
    )

    if [[ -n "$n" ]]; then
        args+=(--n "$n")
    fi

    if [[ -n "${COVERAGE_LLC:-}" ]]; then
        args+=(--llc "$COVERAGE_LLC")
    fi
    if [[ -n "$settings_csv" ]]; then
        args+=(--settings-csv "$settings_csv")
    fi
    if [[ "${RESUME:-}" == 1 ]]; then
        args+=(--resume)
    fi
    if [[ -n "${JOBS:-}" ]]; then
        args+=(-j "$JOBS")
    fi

    echo "=== coverage candidate-test (n=${n:-all}, resume=${RESUME:-0}) ==="
    "${args[@]}"
}

run_incremental() {
    local output_dir="$1"
    local uncovered_csv="$2"
    local llc_map_csv="$3"
    local candidate_tests_output_dir="$4"

    local -a args=(
        python -m coverage incremental
        --output-dir "$output_dir"
        --line-coverage-uncovered-csv "$uncovered_csv"
        --llc-address-line-map-csv "$llc_map_csv"
        --candidate-tests-output-dir "$candidate_tests_output_dir"
    )

    if [[ -n "${COVERAGE_SANCOV:-}" ]]; then
        args+=(--sancov "$COVERAGE_SANCOV")
    fi

    echo "=== coverage incremental ==="
    "${args[@]}"
}
