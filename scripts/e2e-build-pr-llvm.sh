#!/usr/bin/env bash
# Build the source-coverage LLVM tree for an e2e PR checkout, and optionally
# a SanitizerCoverage tree for gap-fill / address-map steps.
#
# Usage:
#   e2e-build-pr-llvm.sh <llvm_dir> <coverage_build> <allowlist> <backends> \
#       <bootstrap_bin> [--sancov-build <dir>]
#
# Honors FUZZ_FILL_E2E_CCACHE, FUZZ_FILL_E2E_CCACHE_COMPILER_CHECK_VERSION,
# and FUZZ_FILL_E2E_JOBS like the previous inline lit BUILD steps.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
    echo "usage: $(basename "$0") <llvm_dir> <coverage_build> <allowlist> <backends> <bootstrap_bin> [--sancov-build <dir>]" >&2
}

if [[ $# -lt 5 ]]; then
    usage
    exit 2
fi

LLVM_DIR="$1"
COVERAGE_BUILD="$2"
ALLOWLIST="$3"
BACKENDS="$4"
BOOTSTRAP_BIN="$5"
shift 5

SANCOV_BUILD=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --sancov-build)
            [[ $# -ge 2 ]] || { echo "error: --sancov-build requires a value" >&2; exit 2; }
            SANCOV_BUILD="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "error: unexpected argument: $1" >&2
            usage
            exit 2
            ;;
    esac
done

# shellcheck source=scripts/lib/gap-scope.sh
source "${REPO_ROOT}/scripts/lib/gap-scope.sh"

projects="$(gap_scope_enable_projects_for_allowlist "$ALLOWLIST")"

common_flags=(--bootstrap-bin "$BOOTSTRAP_BIN" --targets "$BACKENDS")
if [[ -n "$projects" ]]; then
    common_flags+=(--enable-projects "$projects")
else
    common_flags+=(--enable-projects "")
fi
if [[ "${FUZZ_FILL_E2E_CCACHE:-}" == 1 ]]; then
    common_flags+=(--enable-ccache)
fi
if [[ "${FUZZ_FILL_E2E_CCACHE_COMPILER_CHECK_VERSION:-}" == 1 ]]; then
    common_flags+=(--ccache-compiler-check-version)
fi

jobs_args=()
if [[ -n "${FUZZ_FILL_E2E_JOBS:-}" ]]; then
    jobs_args=("${FUZZ_FILL_E2E_JOBS}")
fi

run_build() {
    local -a cmd=("$@")
    if [[ -w /work ]]; then
        stdbuf -oL -eL "${cmd[@]}" 2>&1 | stdbuf -oL tee -a /work/e2e-progress.log
    else
        "${cmd[@]}"
    fi
}

if [[ -n "$SANCOV_BUILD" ]]; then
    if test -x "${SANCOV_BUILD}/bin/llvm-lit"; then
        echo "e2e-build-pr-llvm: sancov build present, skipping"
    else
        run_build \
            "${REPO_ROOT}/scripts/build-llvm-sancov.sh" \
            "$ALLOWLIST" \
            "$LLVM_DIR" \
            "$SANCOV_BUILD" \
            "${common_flags[@]}" \
            "${jobs_args[@]}"
    fi
fi

if test -f "${COVERAGE_BUILD}/test/lit.site.cfg.py"; then
    echo "e2e-build-pr-llvm: coverage build present, skipping"
else
    # Match Docker: disable ClangIR when clang is enabled (no mlir in e2e trees).
    run_build \
        "${REPO_ROOT}/scripts/build-llvm-coverage.sh" \
        "$LLVM_DIR" \
        "$COVERAGE_BUILD" \
        "${common_flags[@]}" \
        --disable-clangir \
        "${jobs_args[@]}"
fi
