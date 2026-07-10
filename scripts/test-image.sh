#!/usr/bin/env bash
# Run fuzz-fill unit and integration tests in the Docker test image.
#
#   test-image.sh
#   test-image.sh --bind-repo
#   test-image.sh --tag local-llvm -v integration-tests/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

image_name="${IMAGE_NAME:-fuzz-fill-test}"
image_tag="${IMAGE_TAG:-latest}"
bind_repo=0

usage() {
    cat <<EOF
Usage: $(basename "$0") [options] [lit args...]

Run unit tests, then integration tests, inside the fuzz-fill Docker test image.

Options:
  --bind-repo            Mount the local fuzz-fill checkout over /work/fuzz-fill.
  --image-name <name>    Docker image name (default: fuzz-fill-test)
  --tag <tag>            Docker image tag (default: latest)
  --help, -h             Show this help

Any remaining arguments are forwarded to lit via integration-tests/test.sh.
If none are given, defaults to: -v integration-tests/

Environment:
  IMAGE_NAME, IMAGE_TAG   Defaults for --image-name and --tag

Examples:
  $(basename "$0")
  $(basename "$0") --tag local-llvm
  $(basename "$0") --bind-repo -v integration-tests/
  $(basename "$0") integration-tests/smoke.test
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bind-repo)
            bind_repo=1
            shift
            ;;
        --image-name)
            if [[ $# -lt 2 ]]; then
                echo "error: --image-name requires a value" >&2
                exit 1
            fi
            image_name="$2"
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
        *)
            break
            ;;
    esac
done

if [[ $# -eq 0 ]]; then
    set -- -v integration-tests/
fi

tmp_container_args=()
if [[ "${bind_repo}" -eq 1 ]]; then
    tmp_container_args+=(--bind-repo)
fi

run_in_container() {
    env IMAGE_NAME="${image_name}" IMAGE_TAG="${image_tag}" \
        "${SCRIPT_DIR}/tmp-container.sh" "${tmp_container_args[@]}" "$@"
}

echo "=== unit tests ==="
run_in_container python -m unittest discover -s tests -v

echo "=== integration tests ==="
run_in_container ./integration-tests/test.sh \
    --venv /work/fuzz-fill-venv \
    --llvm-build /work/llvm-build-sancov/bin \
    --llvm-sancov-build /work/llvm-build-sancov/bin \
    --llvm-src /work/llvm-project \
    "$@"
