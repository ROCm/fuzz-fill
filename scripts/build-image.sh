#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-fuzz-fill-test}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

docker build \
    --build-arg UID="$(id -u)" \
    --build-arg GID="$(id -g)" \
    --build-arg USERNAME="$(id -un)" \
    -f "${REPO_ROOT}/Dockerfile" \
    -t "${IMAGE_NAME}:${IMAGE_TAG}" \
    "${REPO_ROOT}"

echo "Built ${IMAGE_NAME}:${IMAGE_TAG} for UID=$(id -u) GID=$(id -g) USER=$(id -un)"
