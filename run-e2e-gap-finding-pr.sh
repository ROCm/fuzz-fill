#!/usr/bin/env bash
# Local runner for integration-tests/e2e/gap-finding-pr/pr-214457.test
#
# Uses the same LLVM 22.1.8 release bootstrap as the Docker image.
# Run from repo root: ./run-e2e-gap-finding-pr.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

LLVM_RELEASE_VERSION="${LLVM_RELEASE_VERSION:-22.1.8}"
CACHE="${LLVM_RELEASE_CACHE:-${HOME}/.cache/llvm-releases}"
TARBALL="LLVM-${LLVM_RELEASE_VERSION}-Linux-X64.tar.xz"
BOOTSTRAP_ROOT="${CACHE}/LLVM-${LLVM_RELEASE_VERSION}-Linux-X64"

VENV="${VENV:-${REPO_ROOT}/venv}"
LLVM_SRC="${LLVM_SRC:-${REPO_ROOT}/llvm-project}"
LLVM_BIN="${LLVM_BIN:-${LLVM_SRC}/build/bin}"

ensure_bootstrap() {
    if [[ -n "${FUZZ_FILL_E2E_BOOTSTRAP_BIN:-}" && -x "${FUZZ_FILL_E2E_BOOTSTRAP_BIN}/clang" ]]; then
        echo "Using bootstrap: ${FUZZ_FILL_E2E_BOOTSTRAP_BIN}"
        return 0
    fi

    mkdir -p "$CACHE"
    if [[ ! -f "${CACHE}/${TARBALL}" ]]; then
        echo "Downloading ${TARBALL} ..."
        curl -fsSL \
            "https://github.com/llvm/llvm-project/releases/download/llvmorg-${LLVM_RELEASE_VERSION}/${TARBALL}" \
            -o "${CACHE}/${TARBALL}"
    fi

    if [[ ! -x "${BOOTSTRAP_ROOT}/bin/clang" ]]; then
        echo "Extracting bootstrap to ${BOOTSTRAP_ROOT} ..."
        rm -rf "$BOOTSTRAP_ROOT"
        mkdir -p "$BOOTSTRAP_ROOT"
        tar -xJf "${CACHE}/${TARBALL}" -C "$BOOTSTRAP_ROOT" --strip-components=1
    fi

    export FUZZ_FILL_E2E_BOOTSTRAP_BIN="${BOOTSTRAP_ROOT}/bin"
    echo "Using bootstrap: ${FUZZ_FILL_E2E_BOOTSTRAP_BIN}"
}

ensure_bootstrap

if [[ -z "${GH_TOKEN:-}" ]] && command -v gh >/dev/null 2>&1; then
    GH_TOKEN="$(gh auth token 2>/dev/null || true)"
    export GH_TOKEN
fi
if [[ -z "${GH_TOKEN:-}" ]]; then
    echo "error: GH_TOKEN is required (pr-214457.test REQUIRES: gh-token)" >&2
    echo "hint: export GH_TOKEN=\$(gh auth token) or run gh auth login" >&2
    exit 1
fi

[[ -d "${LLVM_SRC}/llvm" ]] || {
    echo "error: llvm-project not found at ${LLVM_SRC}" >&2
    exit 1
}
[[ -d "$LLVM_BIN" ]] || {
    echo "error: LLVM bin dir not found: ${LLVM_BIN}" >&2
    echo "hint: set LLVM_BIN to any tree with FileCheck/sancov (lit config only)" >&2
    exit 1
}
[[ -f "${VENV}/bin/activate" ]] || {
    echo "Creating venv at ${VENV} ..."
    python3 -m venv "$VENV"
    # shellcheck disable=SC1091
    source "${VENV}/bin/activate"
    pip install -e "$REPO_ROOT"
}

echo "=== e2e: pr-214457.test ==="
"${REPO_ROOT}/integration-tests/test.sh" \
    --venv "$VENV" \
    --llvm-build "$LLVM_BIN" \
    --llvm-sancov-build "$LLVM_BIN" \
    --llvm-src "$LLVM_SRC" \
    --param e2e=1 \
    -v integration-tests/e2e/gap-finding-pr/pr-214457.test
