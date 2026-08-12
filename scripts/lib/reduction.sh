#!/usr/bin/env bash
# Reduction pipeline: batch-from-coverage scaffolding and optional reduce runs.
# Source from entrypoints or other scripts/lib modules; do not execute directly.
#
# Optional env (local/Docker runs):
#   COVERAGE_LLC, COVERAGE_LLVM_REDUCE, COVERAGE_LLVM_DIS

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
# shellcheck source=scripts/lib/common.sh
source "${LIB_DIR}/common.sh"

run_batch_from_coverage() {
    local csv="$1"
    local candidate_tests="$2"
    local output="$3"
    local n="$4"
    shift 4

    local -a args=(
        python -m reduce batch-from-coverage
        --csv "$csv"
        --candidate-tests "$candidate_tests"
        --output "$output"
        --n "$n"
    )

    if [[ -n "${COVERAGE_LLC:-}" ]]; then
        args+=(--llc "$COVERAGE_LLC")
    fi
    if [[ -n "${COVERAGE_LLVM_REDUCE:-}" ]]; then
        args+=(--llvm-reduce "$COVERAGE_LLVM_REDUCE")
    fi
    if [[ -n "${COVERAGE_LLVM_DIS:-}" ]]; then
        args+=(--llvm-dis "$COVERAGE_LLVM_DIS")
    fi
    if [[ -n "${REDUCTION_CORPUS_DIR:-}" ]]; then
        args+=(--corpus-dir "$REDUCTION_CORPUS_DIR")
    fi

    args+=("$@")

    echo "=== reduce batch-from-coverage (n=${n}) ==="
    "${args[@]}"
}
