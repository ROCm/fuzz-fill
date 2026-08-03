#!/usr/bin/env bash
# Gap-reducing pipeline step via batch_reduce_using_coverage.py.
# Source from entrypoints or other scripts/lib modules; do not execute directly.
#
# run_gap_reducing <coverage_csv> <candidate_tests_dir> <reduced_dir> <row> <pipeline>
#
# Optional env:
#   BATCH_REDUCE_SCRIPT  — path to batch_reduce_using_coverage.py
#                          (default: scripts/batch_reduce_using_coverage.py under SCRIPTS_DIR)
#   COVERAGE_LLC, COVERAGE_LLVM_REDUCE — tool paths (omitted in prepare-only or Docker)
#   WITH_CREDUCE, CREDUCE_N, PASS_UNDER_TEST, MTRIPLE, EXTRACT_MIR_OUTPUT, MIR_CODEGEN_ONLY
#   PREPARE_ONLY         — any non-empty value skips --llc/--llvm-reduce

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
# shellcheck source=scripts/lib/common.sh
source "${LIB_DIR}/common.sh"

run_gap_reducing() {
    local coverage_csv="$1"
    local candidate_tests_dir="$2"
    local reduced_dir="$3"
    local reduce_row="$4"
    local pipeline="$5"

    local batch_script="${BATCH_REDUCE_SCRIPT:-${SCRIPTS_DIR}/batch_reduce_using_coverage.py}"
    local python="${BATCH_REDUCE_PYTHON:-python3}"

    local -a batch_args=(
        "$python" "$batch_script"
        --csv "$coverage_csv"
        --candidate-tests "$candidate_tests_dir"
        --output "$reduced_dir"
        --n "$reduce_row"
        --pipeline "$pipeline"
    )

    if [[ -n "${WITH_CREDUCE:-}" ]]; then
        batch_args+=(--with-creduce)
    fi
    if [[ -n "${CREDUCE_N:-}" ]]; then
        batch_args+=(--creduce-n "$CREDUCE_N")
    fi
    if [[ -n "${PASS_UNDER_TEST:-}" ]]; then
        batch_args+=(--pass-under-test "$PASS_UNDER_TEST")
    fi
    if [[ -n "${MTRIPLE:-}" ]]; then
        batch_args+=(--mtriple "$MTRIPLE")
    fi
    if [[ -n "${EXTRACT_MIR_OUTPUT:-}" ]]; then
        batch_args+=(--extract-mir-output "$EXTRACT_MIR_OUTPUT")
    fi
    if [[ -n "${MIR_CODEGEN_ONLY:-}" ]]; then
        batch_args+=(--mir-codegen-only)
    fi
    if [[ -z "${PREPARE_ONLY:-}" ]]; then
        if [[ -n "${COVERAGE_LLC:-}" ]]; then
            batch_args+=(--llc "$COVERAGE_LLC")
        fi
        if [[ -n "${COVERAGE_LLVM_REDUCE:-}" ]]; then
            batch_args+=(--llvm-reduce "$COVERAGE_LLVM_REDUCE")
        fi
    fi

    echo "=== gap reducing (row=${reduce_row}, pipeline=${pipeline}) ==="
    "${batch_args[@]}"
}
