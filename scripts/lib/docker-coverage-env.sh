#!/usr/bin/env bash
# Export coverage baseline and gap-fill tool paths inside a fuzz-fill Docker image.
# Source from in-container gap-finding entrypoints.

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
# shellcheck source=scripts/lib/common.sh
source "${LIB_DIR}/common.sh"

docker_export_coverage_env() {
    local coverage_build_dir="/work/llvm-build-coverage"
    local sancov_bin="/work/llvm-build-sancov/bin"
    local host_bin="/usr/lib/llvm-24/bin"
    local llvm_src="/work/llvm-project"
    local allowlist=""

    if [[ -f /work/.sancov-allowlist ]]; then
        allowlist="$(tr -d '[:space:]' < /work/.sancov-allowlist)"
        export COVERAGE_TARGET="$(normalize_coverage_target "$allowlist")"
    else
        unset COVERAGE_TARGET
    fi

    export FUZZ_FILL_COVERAGE_BUILD_DIR="${coverage_build_dir}"
    export FUZZ_FILL_HOST_BIN="${host_bin}"
    export FUZZ_FILL_LLVM_SRC="${llvm_src}"

    export FUZZ_FILL_SANCOV="${sancov_bin}/sancov"
    export FUZZ_FILL_LLVM_LIT="${sancov_bin}/llvm-lit"
    export COVERAGE_SANCOV="${FUZZ_FILL_SANCOV}"
    export COVERAGE_LLVM_LIT="${FUZZ_FILL_LLVM_LIT}"

    case "${COVERAGE_TARGET:-}" in
        clang)
            export COVERAGE_CLANG="${sancov_bin}/clang"
            unset FUZZ_FILL_LLC FUZZ_FILL_OPT COVERAGE_LLC COVERAGE_OPT
            ;;
        *)
            export FUZZ_FILL_LLC="${sancov_bin}/llc"
            export FUZZ_FILL_OPT="${sancov_bin}/opt"
            export COVERAGE_LLC="${FUZZ_FILL_LLC}"
            export COVERAGE_OPT="${FUZZ_FILL_OPT}"
            unset COVERAGE_CLANG
            ;;
    esac
}
