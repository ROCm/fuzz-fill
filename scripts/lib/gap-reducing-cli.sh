#!/usr/bin/env bash
# Shared gap-reducing validation, env setup, and Docker env helpers.
# Source from entrypoints or other scripts/lib modules; do not execute directly.

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
# shellcheck source=scripts/lib/common.sh
source "${LIB_DIR}/common.sh"

gap_reducing_validate_row() {
    local row="$1"
    if [[ ! "$row" =~ ^[0-9]+$ ]] || [[ "$row" -eq 0 ]]; then
        echo "error: --row must be a positive integer: ${row}" >&2
        exit 1
    fi
}

gap_reducing_validate_creduce_n() {
    local n="$1"
    if [[ -n "$n" ]] && { [[ ! "$n" =~ ^[0-9]+$ ]] || [[ "$n" -eq 0 ]]; }; then
        echo "error: --creduce-n must be a positive integer: ${n}" >&2
        exit 1
    fi
}

# Apply reduce extras to the environment for run_gap_reducing (local host or in-container).
# Optional args fall back to existing env when omitted (local WITH_CREDUCE=1 workflow).
gap_reducing_apply_env() {
    local prepare_only="${1:-0}"
    local with_creduce="${2:-${WITH_CREDUCE:-0}}"
    local creduce_n="${3:-${CREDUCE_N:-}}"
    local pass_under_test="${4:-${PASS_UNDER_TEST:-}}"
    local mtriple="${5:-${MTRIPLE:-}}"
    local extract_mir_output="${6:-${EXTRACT_MIR_OUTPUT:-}}"
    local mir_codegen_only="${7:-${MIR_CODEGEN_ONLY:-0}}"

    if [[ "$prepare_only" -eq 1 ]]; then
        export PREPARE_ONLY=1
    else
        unset PREPARE_ONLY
    fi

    if [[ "$with_creduce" == 1 ]]; then
        export WITH_CREDUCE=1
    else
        unset WITH_CREDUCE
    fi

    if [[ -n "$creduce_n" ]]; then
        export CREDUCE_N="$creduce_n"
    else
        unset CREDUCE_N
    fi

    if [[ -n "$pass_under_test" ]]; then
        export PASS_UNDER_TEST="$pass_under_test"
    else
        unset PASS_UNDER_TEST
    fi

    if [[ -n "$mtriple" ]]; then
        export MTRIPLE="$mtriple"
    else
        unset MTRIPLE
    fi

    if [[ -n "$extract_mir_output" ]]; then
        export EXTRACT_MIR_OUTPUT="$extract_mir_output"
    else
        unset EXTRACT_MIR_OUTPUT
    fi

    if [[ "$mir_codegen_only" == 1 ]]; then
        export MIR_CODEGEN_ONLY=1
    else
        unset MIR_CODEGEN_ONLY
    fi
}

# Append reduce-related -e flags to a docker_env array (nameref).
gap_reducing_append_docker_env() {
    local -n _env=$1
    local reduce_row="$2"
    local pipeline="$3"
    local prepare_only="${4:-0}"
    local with_creduce="${5:-0}"
    local creduce_n="${6:-}"
    local pass_under_test="${7:-}"
    local mtriple="${8:-}"
    local extract_mir_output="${9:-}"
    local mir_codegen_only="${10:-0}"

    _env+=(
        -e "REDUCE_ROW=${reduce_row}"
        -e "PIPELINE=${pipeline}"
        -e "PREPARE_ONLY=${prepare_only}"
        -e "WITH_CREDUCE=${with_creduce}"
    )

    if [[ -n "$creduce_n" ]]; then
        _env+=(-e "CREDUCE_N=${creduce_n}")
    fi
    if [[ -n "$pass_under_test" ]]; then
        _env+=(-e "PASS_UNDER_TEST=${pass_under_test}")
    fi
    if [[ -n "$mtriple" ]]; then
        _env+=(-e "MTRIPLE=${mtriple}")
    fi
    if [[ -n "$extract_mir_output" ]]; then
        _env+=(-e "EXTRACT_MIR_OUTPUT=${extract_mir_output}")
    fi
    if [[ "$mir_codegen_only" -eq 1 ]]; then
        _env+=(-e "MIR_CODEGEN_ONLY=1")
    fi
}

gap_reducing_print_summary() {
    local output_dir="$1"
    local reduce_row="$2"
    local pipeline="$3"
    local prepare_only="${4:-0}"
    local output_label="${5:-Gap-fill output}"

    echo "${output_label}: ${output_dir}"
    echo "Reducing row:      ${reduce_row}"
    echo "Pipeline:          ${pipeline}"
    if [[ "$prepare_only" -eq 1 ]]; then
        echo "Mode:              prepare-only"
    fi
}
