#!/usr/bin/env bash
# LIT filter resolution for baseline coverage runs.
# Source from entrypoints or other scripts/lib modules; do not execute directly.

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
: "${SCRIPTS_DIR:=$(cd "${LIB_DIR}/.." && pwd)}"
: "${REPO_ROOT:=$(cd "${SCRIPTS_DIR}/.." && pwd)}"

# Single default prefix for docker gap-finding-baseline (one --lit-filter).
lit_filter_for_allowlist() {
    case "$1" in
        amdgpu) echo "CodeGen/AMDGPU" ;;
        spirv) echo "CodeGen/SPIRV" ;;
        *)
            echo "error: unsupported image allowlist: ${1} (expected amdgpu or spirv)" >&2
            exit 1
            ;;
    esac
}

# Full filter list for docker gap-finding-pr and gap-filling-amdgpu defaults.
# Prints one prefix per line (for mapfile).
default_lit_filters_for_allowlist() {
    case "$1" in
        amdgpu)
            # shellcheck source=scripts/lit-filters-amdgpu.sh
            source "${SCRIPTS_DIR}/lit-filters-amdgpu.sh"
            printf '%s\n' "${AMDGPU_LIT_FILTERS[@]}"
            ;;
        spirv)
            printf '%s\n' "CodeGen/SPIRV"
            ;;
        *)
            echo "error: unsupported image allowlist: ${1} (expected amdgpu or spirv)" >&2
            return 1
            ;;
    esac
}
