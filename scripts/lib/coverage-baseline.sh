#!/usr/bin/env bash
# coverage baseline pipeline step.
# Source from entrypoints or other scripts/lib modules; do not execute directly.
#
# Optional env (local runs set these; Docker omits them and uses image PATH):
#   COVERAGE_SANCOV, COVERAGE_LLVM_LIT, COVERAGE_LLC, COVERAGE_OPT
#   LIT_ALLOW_FAILURES  — any non-empty value adds --lit-allow-failures
#   JOBS                — parallel llvm-lit jobs (-j)

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
# shellcheck source=scripts/lib/common.sh
source "${LIB_DIR}/common.sh"

run_coverage_baseline() {
    local output_dir="$1"
    shift
    local -a lit_filters=("$@")

    local -a args=(
        python -m coverage baseline
        --output-dir "$output_dir"
    )

    if [[ -n "${COVERAGE_SANCOV:-}" ]]; then
        args+=(--sancov "$COVERAGE_SANCOV")
    fi
    if [[ -n "${COVERAGE_LLVM_LIT:-}" ]]; then
        args+=(--llvm-lit "$COVERAGE_LLVM_LIT")
    fi
    if [[ -n "${COVERAGE_LLC:-}" ]]; then
        args+=(--llc "$COVERAGE_LLC")
    fi
    if [[ -n "${COVERAGE_OPT:-}" ]]; then
        args+=(--opt "$COVERAGE_OPT")
    fi

    local lit_filter
    for lit_filter in "${lit_filters[@]}"; do
        args+=(--lit-filter "$lit_filter")
    done

    if [[ -n "${LIT_ALLOW_FAILURES:-}" ]]; then
        args+=(--lit-allow-failures)
    fi
    if [[ -n "${JOBS:-}" ]]; then
        args+=(-j "$JOBS")
    fi

    "${args[@]}"

    python -m gap_pruner "${output_dir}/line_coverage_uncovered.csv" \
        --output "${output_dir}/line_coverage_uncovered_pruned.csv"
}
