#!/usr/bin/env bash
# Install the apt.llvm.org snapshot toolchain used as the fuzz-fill bootstrap.
#
# Usage: install-llvm-apt.sh <major>
#   e.g. install-llvm-apt.sh 24
#
# Packages come from the unversioned snapshot component. The repository only
# retains the latest build, so dated package versions are not pinned.

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $(basename "$0") <major>" >&2
    echo "  e.g. $(basename "$0") 24" >&2
    exit 2
fi

LLVM_MAJOR="$1"
if [[ ! "${LLVM_MAJOR}" =~ ^[0-9]+$ ]]; then
    echo "error: major must be a positive integer: ${LLVM_MAJOR}" >&2
    exit 1
fi

BOOTSTRAP_BIN="/usr/lib/llvm-${LLVM_MAJOR}/bin"

if [[ -r /etc/os-release ]]; then
    # shellcheck source=/dev/null
    . /etc/os-release
fi

if [[ -z "${VERSION_CODENAME:-}" ]]; then
    echo "error: VERSION_CODENAME is unset; cannot select apt.llvm.org suite" >&2
    exit 1
fi

codename="${VERSION_CODENAME}"
key_path=/etc/apt/trusted.gpg.d/apt.llvm.org.asc
list_path=/etc/apt/sources.list.d/llvm-snapshot.list

curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key -o "${key_path}"
printf 'deb http://apt.llvm.org/%s/ llvm-toolchain-%s main\n' \
    "${codename}" "${codename}" > "${list_path}"

apt-get update
apt-get install -y --no-install-recommends \
    "clang-${LLVM_MAJOR}" \
    "lld-${LLVM_MAJOR}" \
    "libclang-rt-${LLVM_MAJOR}-dev"

if [[ -z "${GITHUB_ACTIONS:-}" ]]; then
    rm -rf /var/lib/apt/lists/*
fi

for tool in clang clang++ ld.lld; do
    if [[ ! -x "${BOOTSTRAP_BIN}/${tool}" ]]; then
        echo "error: expected executable missing: ${BOOTSTRAP_BIN}/${tool}" >&2
        exit 1
    fi
done

echo "=== fuzz-fill: apt.llvm.org bootstrap = ${BOOTSTRAP_BIN} ==="
"${BOOTSTRAP_BIN}/clang" --version
