#!/bin/bash
# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
IMAGE="${COMPILE_REQUIREMENTS_IMAGE:-ubuntu:24.04}"
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"

usage() {
    cat <<EOF
Usage: $(basename "$0")

Compile pinned Python dependencies from pyproject.toml into requirements.txt
inside ${IMAGE} (Python 3.12, matching CI).

The lockfile is generated on demand (not committed). CI runs this before
SPDX SBOM generation so trivy can resolve transitive Python dependencies.

Environment:
  COMPILE_REQUIREMENTS_IMAGE   Docker image (default: ubuntu:24.04)

Examples:
  $(basename "$0")
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown argument: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if ! command -v docker >/dev/null 2>&1; then
    echo "error: docker not found in PATH" >&2
    exit 1
fi

if [[ ! -f "${REPO_ROOT}/pyproject.toml" ]]; then
    echo "error: pyproject.toml not found at ${REPO_ROOT}/pyproject.toml" >&2
    exit 1
fi

echo "=== Compiling requirements in ${IMAGE} ==="
docker run --rm -i \
    -v "${REPO_ROOT}:/work" \
    -w /work \
    -e HOST_UID="${HOST_UID}" \
    -e HOST_GID="${HOST_GID}" \
    "${IMAGE}" \
    bash -s <<'EOF'
export DEBIAN_FRONTEND=noninteractive
set -euo pipefail
apt-get update -qq
apt-get install -y --no-install-recommends \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    >/dev/null

python3 -m venv /tmp/venv-lock
# pip 26.2 moved stdlib_pkgs out of pip._internal.utils.compat; current
# pip-tools still imports it there, so cap pip below 26.2 for now.
/tmp/venv-lock/bin/pip install --upgrade 'pip>=24,<26.2' setuptools wheel >/dev/null
/tmp/venv-lock/bin/pip install 'pip-tools>=7.4.1' typing_extensions >/dev/null

PIP_COMPILE=(/tmp/venv-lock/bin/pip-compile pyproject.toml --strip-extras --allow-unsafe --no-header --quiet)

{
    cat <<'HEADER'
#
# Generated lockfile for fuzz-fill (Python 3.12). Not committed to the repo.
# Produced by scripts/compile-requirements.sh (CI: SBOM_main workflow).
#
HEADER
    "${PIP_COMPILE[@]}" -o -
} > requirements.txt

echo "Wrote requirements.txt"
chown "${HOST_UID}:${HOST_GID}" requirements.txt
EOF
