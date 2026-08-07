#!/usr/bin/env bash
# Shared Docker image flag parsing and prepare helpers for gap docker runners.
# Source after SCRIPT_DIR is set; requires ensure-image.sh.

: "${SCRIPT_DIR:?SCRIPT_DIR must be set before sourcing docker-image-cli.sh}"

docker_image_cli_init_vars() {
    image_name="${IMAGE_NAME:-fuzz-fill-test}"
    image_tag="${IMAGE_TAG:-latest}"
    image_ref=""
    pr_id=""
    build_image=0
    keep_image=0
    force_build=0
    llvm_repo=""
    backend_tests=""
    github_repo=""
}

# Parse one image-related flag. Returns 0 if consumed; sets DOCKER_IMAGE_CLI_SHIFT.
docker_image_cli_try_parse() {
    DOCKER_IMAGE_CLI_SHIFT=0

    case "$1" in
        --image)
            [[ $# -ge 2 ]] || { echo "error: --image requires a value" >&2; exit 2; }
            image_ref="$2"
            DOCKER_IMAGE_CLI_SHIFT=2
            return 0
            ;;
        --pr-id)
            [[ $# -ge 2 ]] || { echo "error: --pr-id requires a value" >&2; exit 2; }
            pr_id="$2"
            DOCKER_IMAGE_CLI_SHIFT=2
            return 0
            ;;
        --build-image)
            build_image=1
            DOCKER_IMAGE_CLI_SHIFT=1
            return 0
            ;;
        --keep-image)
            keep_image=1
            DOCKER_IMAGE_CLI_SHIFT=1
            return 0
            ;;
        --force-build)
            force_build=1
            DOCKER_IMAGE_CLI_SHIFT=1
            return 0
            ;;
        --llvm-repo)
            [[ $# -ge 2 ]] || { echo "error: --llvm-repo requires a value" >&2; exit 2; }
            llvm_repo="$2"
            DOCKER_IMAGE_CLI_SHIFT=2
            return 0
            ;;
        --backend-tests)
            [[ $# -ge 2 ]] || { echo "error: --backend-tests requires a value" >&2; exit 2; }
            backend_tests="$2"
            DOCKER_IMAGE_CLI_SHIFT=2
            return 0
            ;;
        --github-repo)
            [[ $# -ge 2 ]] || { echo "error: --github-repo requires a value" >&2; exit 2; }
            github_repo="$2"
            DOCKER_IMAGE_CLI_SHIFT=2
            return 0
            ;;
        --image-name)
            [[ $# -ge 2 ]] || { echo "error: --image-name requires a value" >&2; exit 2; }
            image_name="$2"
            DOCKER_IMAGE_CLI_SHIFT=2
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

docker_image_cli_prepare() {
    docker_image_validate_build_flags
    docker_image_normalize_backend_tests
    docker_image_validate_pr_id
    docker_image_resolve_ref
    docker_image_ensure
}
