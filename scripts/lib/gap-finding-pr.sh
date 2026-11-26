#!/usr/bin/env bash
# PR gap-finding pipeline: baseline -> added_lines -> target-lines.
# Source from entrypoints or other scripts/lib modules; do not execute directly.
#
# run_gap_finding_pr <output_root> <commit> [llvm_repo] [filter ...]
# Optional env: same tool-path and JOBS vars as coverage-baseline.sh;

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
# shellcheck source=scripts/lib/coverage-baseline.sh
source "${LIB_DIR}/coverage-baseline.sh"

run_gap_finding_pr() {
    local output_root="$1"
    local commit="$2"
    local llvm_repo="${3:-}"
    shift 3
    local -a filters=("$@")

    local baseline_dir="${output_root}/baseline"
    local added_lines_dir="${output_root}/added-lines"
    local target_lines_dir="${output_root}/commit_lines_report"

    mkdir -p "$added_lines_dir" "$target_lines_dir"

    if [[ ${#filters[@]} -gt 0 ]]; then
        echo "=== coverage baseline (${#filters[@]} filter(s)) ==="
    else
        echo "=== coverage baseline ==="
    fi
    run_coverage_baseline "$baseline_dir" "${filters[@]}"

    echo "=== added_lines (commit=${commit}) ==="
    local -a added_args=(
        python -m added_lines
        --commit "$commit"
        --output-dir "$added_lines_dir"
    )
    if [[ -n "$llvm_repo" ]]; then
        added_args+=(--llvm-repo "$llvm_repo")
    fi
    "${added_args[@]}"

    echo "=== coverage target-lines ==="
    local -a target_args=(
        python -m coverage target-lines
        --output-dir "$target_lines_dir"
        --summary "${baseline_dir}/line_coverage_summary.csv"
        --target-lines-csv "${added_lines_dir}/added-lines.csv"
    )
    if [[ -n "$llvm_repo" ]]; then
        target_args+=(--llvm-repo "$llvm_repo")
    fi
    "${target_args[@]}"

    echo "=== gap-pruner ==="
    local llvm_src="${llvm_repo:-${FUZZ_FILL_LLVM_SRC:-${COVERAGE_LLVM_SRC:-${LLVM_SRC:-}}}}"
    local -a pruner_args=(
        python -m gap_pruner "${target_lines_dir}/target_lines_uncovered.csv"
        --output "${target_lines_dir}/target_lines_uncovered_pruned.csv"
    )
    if [[ -n "$llvm_src" ]]; then
        pruner_args+=(--llvm-src-dir "$llvm_src")
    fi
    "${pruner_args[@]}"
}
