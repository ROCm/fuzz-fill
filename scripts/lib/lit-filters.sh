#!/usr/bin/env bash
# Legacy LIT filter helpers. Gap-finding entrypoints no longer map allowlist
# presets to these lists; keep the files for optional --lit-filter reuse.

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
: "${SCRIPTS_DIR:=$(cd "${LIB_DIR}/.." && pwd)}"
: "${REPO_ROOT:=$(cd "${SCRIPTS_DIR}/.." && pwd)}"

# Prints one prefix per line (for mapfile).
default_lit_filters_for_allowlist() {
    case "$1" in
        amdgpu)
            # shellcheck source=scripts/lit-filters-amdgpu.sh
            source "${SCRIPTS_DIR}/lit-filters-amdgpu.sh"
            printf '%s\n' "${AMDGPU_LIT_FILTERS[@]}"
            ;;
        spirv)
            # shellcheck source=scripts/lit-filters-spirv.sh
            source "${SCRIPTS_DIR}/lit-filters-spirv.sh"
            printf '%s\n' "${SPIRV_LIT_FILTERS[@]}"
            ;;
        *)
            echo "error: unsupported allowlist preset for legacy filters: ${1} (expected amdgpu or spirv)" >&2
            return 1
            ;;
    esac
}
