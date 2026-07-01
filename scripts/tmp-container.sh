#!/usr/bin/env bash
# Run commands or an interactive shell in the fuzz-fill Docker test image.
#
#   tmp-container.sh                  interactive shell
#   tmp-container.sh <command> [args] run a command
#   tmp-container.sh --bind-repo ...  mount local fuzz-fill over /work/fuzz-fill
#
# The Python venv lives at /work/fuzz-fill-venv (outside the repo mount).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAME="${IMAGE_NAME:-fuzz-fill-test}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
CONTAINER_WORKDIR="/work/fuzz-fill"
CONTAINER_VENV="/work/fuzz-fill-venv"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--bind-repo] [command [args...]]

  (no arguments)           Start an interactive shell in the container.
  <command> [args...]      Run a command and exit.

Options:
  --bind-repo              Bind the local fuzz-fill checkout at ${CONTAINER_WORKDIR}.
                           The venv at ${CONTAINER_VENV} stays outside the mount.

Environment:
  IMAGE_NAME, IMAGE_TAG    Docker image (default: fuzz-fill-test:latest)

Examples:
  $(basename "$0")
  $(basename "$0") --bind-repo
  $(basename "$0") ./integration-tests/test.sh --venv ${CONTAINER_VENV} \\
      --llvm-build /work/llvm-build-uninstrumented/bin \\
      --llvm-sancov-build /work/llvm-build-sancov/bin \\
      --llvm-src /work/llvm-project -v integration-tests/
EOF
}

bind_repo=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --bind-repo)
            bind_repo=1
            shift
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
            break
            ;;
    esac
done

if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    echo "error: image not found: ${IMAGE}" >&2
    echo "Build it with: ${SCRIPT_DIR}/build-image.sh" >&2
    exit 1
fi

docker_args=(--rm)
mount_args=()

if [[ "${bind_repo}" -eq 1 ]]; then
    mount_args+=(-v "${REPO_ROOT}:${CONTAINER_WORKDIR}")
fi

if [[ $# -eq 0 ]]; then
    docker_args+=(-it)
    exec docker run "${docker_args[@]}" "${mount_args[@]}" -w "${CONTAINER_WORKDIR}" \
        "${IMAGE}" bash -l
fi

exec docker run "${docker_args[@]}" "${mount_args[@]}" -w "${CONTAINER_WORKDIR}" \
    "${IMAGE}" "$@"
