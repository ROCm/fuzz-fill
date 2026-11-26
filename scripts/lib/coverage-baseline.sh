#!/usr/bin/env bash
# coverage baseline pipeline step.
# Source from entrypoints or other scripts/lib modules; do not execute directly.
#
# Optional env:
#   FUZZ_FILL_COVERAGE_BUILD_DIR / COVERAGE_BUILD_DIR  — coverage build dir
#   FUZZ_FILL_HOST_BIN / COVERAGE_HOST_BIN             — host LLVM bin dir
#   FUZZ_FILL_LLVM_SRC / COVERAGE_LLVM_SRC / LLVM_SRC  — llvm-project source
#   JOBS                                               — parallel check-all jobs (-j)
#
# Remaining arguments are --filter regexes for the source baseline check-all run.

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
# shellcheck source=scripts/lib/common.sh
source "${LIB_DIR}/common.sh"

run_coverage_baseline() {
    local output_dir="$1"
    shift
    local -a filters=("$@")
    local build_dir="${FUZZ_FILL_COVERAGE_BUILD_DIR:-${COVERAGE_BUILD_DIR:-}}"
    local host_bin="${FUZZ_FILL_HOST_BIN:-${COVERAGE_HOST_BIN:-}}"
    local llvm_src="${FUZZ_FILL_LLVM_SRC:-${COVERAGE_LLVM_SRC:-${LLVM_SRC:-}}}"

    local -a args=(
        python -m coverage baseline
        --output-dir "$output_dir"
    )

    if [[ -n "$build_dir" ]]; then
        args+=(--build-dir "$build_dir")
    fi
    if [[ -n "$host_bin" ]]; then
        args+=(--host-bin "$host_bin")
    fi
    if [[ -n "$llvm_src" ]]; then
        args+=(--llvm-src "$llvm_src")
    fi

    local filter
    for filter in "${filters[@]}"; do
        args+=(--filter "$filter")
    done
    if [[ -n "${JOBS:-}" ]]; then
        args+=(-j "$JOBS")
    fi

    "${args[@]}"

    local -a pruner_args=(
        python -m gap_pruner "${output_dir}/line_coverage_uncovered.csv"
        --output "${output_dir}/line_coverage_uncovered_pruned.csv"
    )
    if [[ -n "$llvm_src" ]]; then
        pruner_args+=(--llvm-src-dir "$llvm_src")
    fi
    "${pruner_args[@]}"
}
