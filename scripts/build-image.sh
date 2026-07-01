#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-fuzz-fill-test}"

llvm_dir=""
image_tag="${IMAGE_TAG:-latest}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--llvm-dir <path>] [--tag <tag>] [--help]

Build the fuzz-fill Docker test image.

Options:
  --llvm-dir <path>   Use a local llvm-project checkout instead of downloading
                      the pinned LLVM revision from GitHub. The path must
                      contain an llvm/ subdirectory.
  --tag <tag>         Docker image tag (default: latest)

Environment:
  IMAGE_NAME          Docker image name (default: fuzz-fill-test)

Examples:
  $(basename "$0")
  $(basename "$0") --llvm-dir llvm-project
  $(basename "$0") --llvm-dir /path/to/llvm-project --tag local-llvm
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --llvm-dir)
            if [[ $# -lt 2 ]]; then
                echo "error: --llvm-dir requires a value" >&2
                exit 1
            fi
            llvm_dir="$2"
            shift 2
            ;;
        --tag)
            if [[ $# -lt 2 ]]; then
                echo "error: --tag requires a value" >&2
                exit 1
            fi
            image_tag="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            echo "error: unexpected argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

llvm_context=""
llvm_context_tmp=""
cleanup() {
    if [[ -n "$llvm_context_tmp" ]]; then
        rmdir "$llvm_context_tmp"
    fi
}
trap cleanup EXIT

if [[ -n "$llvm_dir" ]]; then
    if [[ ! -d "${llvm_dir}/llvm" ]]; then
        echo "error: --llvm-dir must be an llvm-project checkout (directory containing llvm/): ${llvm_dir}" >&2
        exit 1
    fi
    llvm_context="$(realpath "${llvm_dir}")"
    echo "Using local llvm-project: ${llvm_context}"
else
    llvm_context_tmp="$(mktemp -d -p /tmp)"
    llvm_context="$llvm_context_tmp"
fi

docker build \
    --build-context "llvm=${llvm_context}" \
    --build-arg UID="$(id -u)" \
    --build-arg GID="$(id -g)" \
    --build-arg USERNAME="$(id -un)" \
    -f "${REPO_ROOT}/Dockerfile" \
    -t "${IMAGE_NAME}:${image_tag}" \
    "${REPO_ROOT}"

echo "Built ${IMAGE_NAME}:${image_tag} for UID=$(id -u) GID=$(id -g) USER=$(id -un)"
