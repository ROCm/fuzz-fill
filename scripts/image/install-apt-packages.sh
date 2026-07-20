#!/usr/bin/env bash
# Install apt packages for a fuzz-fill test image profile.
#
# Profiles match Dockerfile stages: release, source, builder, runtime.
# The all profile installs the union of every stage (for single-container CI).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APT_DIR="${SCRIPT_DIR}/apt"

usage() {
    cat <<EOF
Usage: $(basename "$0") <profile>

Profiles:
  release   Dockerfile llvm-release stage
  source    Dockerfile llvm-source stage
  builder   Dockerfile llvm-builder stage
  runtime   Dockerfile final stage
  all       Union of release, source, builder, and runtime (CI)
EOF
}

read_packages() {
    local packages_file="${APT_DIR}/${1}.packages"
    if [[ ! -f "$packages_file" ]]; then
        echo "error: missing package list: ${packages_file}" >&2
        return 1
    fi
    grep -Ev '^[[:space:]]*(#|$)' "$packages_file"
}

merge_profiles() {
    local -A seen=()
    local profile pkg

    for profile in "$@"; do
        while IFS= read -r pkg; do
            [[ -z "$pkg" ]] && continue
            if [[ -z "${seen[$pkg]+x}" ]]; then
                seen[$pkg]=1
                packages+=("$pkg")
            fi
        done < <(read_packages "$profile")
    done
}

if [[ $# -ne 1 ]]; then
    usage >&2
    exit 2
fi

profile="$1"
declare -a packages=()

case "$profile" in
    all)
        merge_profiles release source builder runtime
        ;;
    release|source|builder|runtime)
        while IFS= read -r pkg; do
            [[ -z "$pkg" ]] && continue
            packages+=("$pkg")
        done < <(read_packages "$profile")
        ;;
    *)
        echo "error: unknown profile: ${profile}" >&2
        usage >&2
        exit 1
        ;;
esac

if [[ ${#packages[@]} -eq 0 ]]; then
    echo "error: no packages listed for profile: ${profile}" >&2
    exit 1
fi

apt-get update
apt-get install -y --no-install-recommends "${packages[@]}"
if [[ -z "${GITHUB_ACTIONS:-}" ]]; then
    rm -rf /var/lib/apt/lists/*
fi
