#!/usr/bin/env bash
# Shared helpers for fuzz-fill pipeline scripts.
# Source from entrypoints or other scripts/lib modules; do not execute directly.

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
: "${SCRIPTS_DIR:=$(cd "${LIB_DIR}/.." && pwd)}"
: "${REPO_ROOT:=$(cd "${SCRIPTS_DIR}/.." && pwd)}"

validate_jobs() {
    local jobs="$1"
    if [[ -n "$jobs" ]] && { [[ ! "$jobs" =~ ^[0-9]+$ ]] || [[ "$jobs" -eq 0 ]]; }; then
        echo "error: -j/--jobs must be a positive integer: ${jobs}" >&2
        exit 1
    fi
}

require_bin() {
    local dir="$1" tool="$2"
    if [[ ! -x "$dir/$tool" ]]; then
        echo "error: missing $dir/$tool" >&2
        exit 1
    fi
}

activate_venv_if_present() {
    local repo_root="${1:-$REPO_ROOT}"
    if [[ -f "$repo_root/venv/bin/activate" ]]; then
        # shellcheck disable=SC1091
        source "$repo_root/venv/bin/activate"
    fi
}
