#!/bin/bash
# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

# Build the four PR-gap recipes into one ccache directory and print how large
# that directory is after each recipe. This is the size a single warm-up cache
# has to hold. The cap starts high so ccache does not evict; any cleanup means
# the cap was too small and the measured total is short.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
    cat <<EOF
Usage: $(basename "$0") --llvm-dir <dir> --bootstrap-bin <dir> --work-dir <dir> [options]

Build these recipes, in order, into one CCACHE_DIR:

  allowlist-llvm.txt        X86;AMDGPU     (no projects)
  allowlist-llvm.txt        X86;SPIRV      (no projects)
  allowlist-clang.txt       all            clang
  allowlist-llvm-clang.txt  all            clang

Each recipe is built under --work-dir, then both of its build trees are deleted.
ccache is shared and kept. --work-dir must not already exist.

Options:
  --jobs <n>        Ninja compile jobs (default: nproc)
  --max-size <size> CCACHE_MAXSIZE (default: 20G). Raise it if the script
                    reports cleanups.
  --help, -h        Show this help

The script exits non-zero if ccache evicts anything. Compression matches CI
(CCACHE_COMPRESS=true), so the final byte count is the compressed cache.
EOF
}

LLVM_DIR=""
BOOTSTRAP_BIN=""
WORK_DIR=""
JOBS=""
MAX_SIZE="20G"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --llvm-dir)
            LLVM_DIR="$2"
            shift 2
            ;;
        --bootstrap-bin)
            BOOTSTRAP_BIN="$2"
            shift 2
            ;;
        --work-dir)
            WORK_DIR="$2"
            shift 2
            ;;
        --jobs)
            JOBS="$2"
            shift 2
            ;;
        --max-size)
            MAX_SIZE="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -z "${LLVM_DIR}" || -z "${BOOTSTRAP_BIN}" || -z "${WORK_DIR}" ]]; then
    usage >&2
    exit 2
fi

if [[ -z "${JOBS}" ]]; then
    JOBS="$(nproc)"
fi

if [[ ! "${JOBS}" =~ ^[1-9][0-9]*$ ]]; then
    echo "error: --jobs must be a positive integer: ${JOBS}" >&2
    exit 2
fi

if [[ ! -d "${LLVM_DIR}/llvm" ]]; then
    echo "error: LLVM source not found at ${LLVM_DIR}/llvm" >&2
    exit 1
fi

if [[ ! -x "${BOOTSTRAP_BIN}/clang" || ! -x "${BOOTSTRAP_BIN}/clang++" || ! -x "${BOOTSTRAP_BIN}/ld.lld" ]]; then
    echo "error: bootstrap bin must provide clang, clang++, and ld.lld: ${BOOTSTRAP_BIN}" >&2
    exit 1
fi

if [[ -e "${WORK_DIR}" ]]; then
    echo "error: --work-dir already exists: ${WORK_DIR}" >&2
    exit 1
fi

if ! command -v ccache >/dev/null 2>&1; then
    echo "error: ccache is not installed" >&2
    exit 1
fi

mkdir -p "${WORK_DIR}"
WORK_DIR="$(realpath "${WORK_DIR}")"
LLVM_DIR="$(realpath "${LLVM_DIR}")"
BOOTSTRAP_BIN="$(realpath "${BOOTSTRAP_BIN}")"

export CCACHE_DIR="${WORK_DIR}/ccache"
export CCACHE_MAXSIZE="${MAX_SIZE}"
export CCACHE_COMPRESS=true
mkdir -p "${CCACHE_DIR}"

SUMMARY="${WORK_DIR}/ccache-sizes.txt"
: > "${SUMMARY}"

echo "compiler: $("${BOOTSTRAP_BIN}/clang" --version | head -n 1)"
echo "ccache:   $(ccache --version | head -n 1)"
echo "CCACHE_DIR=${CCACHE_DIR}"
echo "CCACHE_MAXSIZE=${CCACHE_MAXSIZE}"
echo "CCACHE_COMPRESS=${CCACHE_COMPRESS}"
echo

cache_bytes() {
    du -sb "${CCACHE_DIR}" | awk '{print $1}'
}

stat_value() {
    local key="$1"
    local stats="$2"
    awk -F '\t' -v key="${key}" '$1 == key { print $2; found = 1 } END { if (!found) exit 1 }' <<<"${stats}"
}

EVICTED=0

build_recipe() {
    local name="$1"
    local allowlist="$2"
    local targets="$3"
    local projects="$4"
    local build_dir="${WORK_DIR}/build-${name}"
    local before after delta stats hits misses cleanups

    before="$(cache_bytes)"
    echo "=== ${name}: targets=${targets} projects=${projects:-<none>} ==="
    ccache --zero-stats

    local cmd=(
        "${REPO_ROOT}/scripts/build-llvm-sancov.sh"
        "${allowlist}"
        "${LLVM_DIR}"
        "${build_dir}"
        --bootstrap-bin "${BOOTSTRAP_BIN}"
        --targets "${targets}"
        --enable-ccache
        --ccache-compiler-check-version
    )
    if [[ -n "${projects}" ]]; then
        cmd+=(--enable-projects "${projects}")
    fi
    cmd+=("${JOBS}")
    "${cmd[@]}"

    stats="$(ccache --print-stats)"
    hits="$(stat_value direct_cache_hit "${stats}")"
    hits=$((hits + $(stat_value preprocessed_cache_hit "${stats}")))
    misses="$(stat_value cache_miss "${stats}")"
    cleanups="$(stat_value cleanups_performed "${stats}")"
    after="$(cache_bytes)"
    delta=$((after - before))

    if [[ "${cleanups}" != "0" ]]; then
        EVICTED=1
        echo "warning: ccache evicted ${cleanups} files during ${name}; raise --max-size" >&2
    fi

    printf '%s\t+%s\t%s\thits=%s\tmisses=%s\tcleanups=%s\n' \
        "${name}" "${delta}" "${after}" "${hits}" "${misses}" "${cleanups}" \
        | tee -a "${SUMMARY}"

    # build-llvm-sancov.sh writes the Release tool tree next to the instrumented one.
    rm -rf "${build_dir}" "${build_dir}.sancov-release"
    echo "removed ${build_dir} and ${build_dir}.sancov-release"
    echo
}

build_recipe llvm-x86-amdgpu \
    "${REPO_ROOT}/scripts/allowlist-llvm.txt" "X86;AMDGPU" ""
build_recipe llvm-x86-spirv \
    "${REPO_ROOT}/scripts/allowlist-llvm.txt" "X86;SPIRV" ""
build_recipe clang-all \
    "${REPO_ROOT}/scripts/allowlist-clang.txt" "all" "clang"
build_recipe llvm-clang-all \
    "${REPO_ROOT}/scripts/allowlist-llvm-clang.txt" "all" "clang"

echo "=== bytes added, then total (compressed ccache directory) ==="
cat "${SUMMARY}"

if [[ "${EVICTED}" -ne 0 ]]; then
    echo "error: measurement is short because ccache evicted files" >&2
    exit 1
fi
