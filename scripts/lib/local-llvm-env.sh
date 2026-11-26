#!/usr/bin/env bash
# Local LLVM path setup and coverage tool exports for gap pipeline scripts.
# Source from entrypoints or other scripts/lib modules; do not execute directly.
#
# setup_local_llvm_env <llvm_repo> <coverage_bin> [instrumented_bin_dir]
#   Sets LLVM_REPO, LLVM_BIN, INSTRUMENTED_BIN_DIR and exports baseline/gap-fill tool paths.
#   instrumented_bin_dir may be empty when the caller only needs source baseline.

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
# shellcheck source=scripts/lib/common.sh
source "${LIB_DIR}/common.sh"

setup_local_llvm_env() {
    local llvm_repo="$1"
    local llvm_bin="$2"
    local instrumented_bin_dir="${3:-}"
    local coverage_build_dir
    local host_bin

    LLVM_REPO="$(realpath "$llvm_repo")"
    LLVM_BIN="$(realpath "$llvm_bin")"
    coverage_build_dir="${FUZZ_FILL_COVERAGE_BUILD_DIR:-${COVERAGE_BUILD_DIR:-$(realpath "${LLVM_BIN}/..")}}"
    host_bin="${FUZZ_FILL_HOST_BIN:-${COVERAGE_HOST_BIN:-${LLVM_BIN}}}"

    export FUZZ_FILL_COVERAGE_BUILD_DIR="$(realpath "${coverage_build_dir}")"
    export FUZZ_FILL_HOST_BIN="$(realpath "${host_bin}")"
    export FUZZ_FILL_LLVM_SRC="${LLVM_REPO}"

    if [[ -n "$instrumented_bin_dir" ]]; then
        INSTRUMENTED_BIN_DIR="$(realpath "$instrumented_bin_dir")"
        export FUZZ_FILL_SANCOV="${INSTRUMENTED_BIN_DIR}/sancov"
        export FUZZ_FILL_LLVM_LIT="${INSTRUMENTED_BIN_DIR}/llvm-lit"
        export FUZZ_FILL_LLC="${INSTRUMENTED_BIN_DIR}/llc"
        export FUZZ_FILL_OPT="${INSTRUMENTED_BIN_DIR}/opt"
        export COVERAGE_SANCOV="${FUZZ_FILL_SANCOV}"
        export COVERAGE_LLVM_LIT="${FUZZ_FILL_LLVM_LIT}"
        export COVERAGE_LLC="${FUZZ_FILL_LLC}"
        export COVERAGE_OPT="${FUZZ_FILL_OPT}"
    else
        INSTRUMENTED_BIN_DIR=""
    fi
}

require_local_coverage_bins() {
    local host_bin="${FUZZ_FILL_HOST_BIN:-${COVERAGE_HOST_BIN:-$LLVM_BIN}}"
    require_bin "$host_bin" llvm-profdata
    require_bin "$host_bin" llvm-cov
}

require_local_gap_fill_bins() {
    require_bin "$INSTRUMENTED_BIN_DIR" sancov
    require_bin "$INSTRUMENTED_BIN_DIR" llc
}

require_local_reduce_bins() {
    require_bin "$INSTRUMENTED_BIN_DIR" llc
    require_bin "$LLVM_BIN" llvm-reduce
}

export_local_reduce_tools() {
    export FUZZ_FILL_LLC="${INSTRUMENTED_BIN_DIR}/llc"
    export COVERAGE_LLC="${FUZZ_FILL_LLC}"
    export COVERAGE_LLVM_REDUCE="${LLVM_BIN}/llvm-reduce"
    export COVERAGE_LLVM_DIS="${LLVM_BIN}/llvm-dis"
}
