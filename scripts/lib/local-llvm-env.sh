#!/usr/bin/env bash
# Local LLVM path setup and coverage tool exports for gap pipeline scripts.
# Source from entrypoints or other scripts/lib modules; do not execute directly.
#
# setup_local_llvm_env_explicit <llvm_repo> <llvm_bin> <instrumented_bin_dir>
#   Sets LLVM_REPO, LLVM_BIN, INSTRUMENTED_BIN_DIR and exports COVERAGE_* tool paths.
# setup_local_llvm_env_with_lit_failures — legacy; prefer setup_local_llvm_env_explicit.

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
# shellcheck source=scripts/lib/common.sh
source "${LIB_DIR}/common.sh"

setup_local_llvm_env_explicit() {
    local llvm_repo="$1"
    local llvm_bin="$2"
    local instrumented_bin_dir="$3"

    LLVM_REPO="$(realpath "$llvm_repo")"
    LLVM_BIN="$(realpath "$llvm_bin")"
    INSTRUMENTED_BIN_DIR="$(realpath "$instrumented_bin_dir")"

    export COVERAGE_SANCOV="${LLVM_BIN}/sancov"
    export COVERAGE_LLVM_LIT="${INSTRUMENTED_BIN_DIR}/llvm-lit"
    export COVERAGE_LLC="${INSTRUMENTED_BIN_DIR}/llc"
    export COVERAGE_OPT="${INSTRUMENTED_BIN_DIR}/opt"
}

setup_local_llvm_env() {
    local repo_root="$1"
    local instrumented_subdir="${2:-build-amdgpu-bb/bin}"

    LLVM_REPO="${LLVM_REPO:-$(cd "${repo_root}/../llvm-project" && pwd)}"
    LLVM_BIN="${LLVM_BIN:-${LLVM_REPO}/build/bin}"
    INSTRUMENTED_BIN_DIR="${INSTRUMENTED_BIN_DIR:-${LLVM_REPO}/${instrumented_subdir}}"

    setup_local_llvm_env_explicit "$LLVM_REPO" "$LLVM_BIN" "$INSTRUMENTED_BIN_DIR"
}

setup_local_llvm_env_with_lit_failures() {
    setup_local_llvm_env "$@"
    export LIT_ALLOW_FAILURES=1
}

require_local_coverage_bins() {
    require_bin "$LLVM_BIN" sancov
    require_bin "$INSTRUMENTED_BIN_DIR" llvm-lit
    require_bin "$INSTRUMENTED_BIN_DIR" llc
    require_bin "$INSTRUMENTED_BIN_DIR" opt
}

require_local_reduce_bins() {
    require_bin "$INSTRUMENTED_BIN_DIR" llc
    require_bin "$LLVM_BIN" llvm-reduce
}

export_local_reduce_tools() {
    export COVERAGE_LLC="${INSTRUMENTED_BIN_DIR}/llc"
    export COVERAGE_LLVM_REDUCE="${LLVM_BIN}/llvm-reduce"
}
