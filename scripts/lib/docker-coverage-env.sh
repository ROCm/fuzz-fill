#!/usr/bin/env bash
# Export COVERAGE_* tool paths for baseline runs inside a fuzz-fill Docker image.
# Source from in-container gap-finding entrypoints.

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
# shellcheck source=scripts/lib/common.sh
source "${LIB_DIR}/common.sh"

docker_export_coverage_env() {
    local instrumented_bin="/work/llvm-build-sancov/bin"
    local allowlist=""

    if [[ -f /work/.sancov-allowlist ]]; then
        allowlist="$(tr -d '[:space:]' < /work/.sancov-allowlist)"
        export COVERAGE_TARGET="$(normalize_coverage_target "$allowlist")"
    else
        unset COVERAGE_TARGET
    fi

    export COVERAGE_SANCOV="${instrumented_bin}/sancov"
    export COVERAGE_LLVM_LIT="${instrumented_bin}/llvm-lit"

    case "${COVERAGE_TARGET:-}" in
        clang)
            export COVERAGE_CLANG="${instrumented_bin}/clang"
            unset COVERAGE_LLC COVERAGE_OPT
            ;;
        *)
            export COVERAGE_LLC="${instrumented_bin}/llc"
            export COVERAGE_OPT="${instrumented_bin}/opt"
            unset COVERAGE_CLANG
            ;;
    esac
}
