#!/usr/bin/env bash
# Shared Docker image resolution, PR build, and reuse helpers for fuzz-fill docker runners.
# Source this file from runner scripts; do not execute directly.

: "${SCRIPT_DIR:?SCRIPT_DIR must be set before sourcing ensure-image.sh}"

docker_image_cleanup_built() {
    if [[ "${build_image:-0}" -eq 1 && "${keep_image:-0}" -eq 0 && -n "${image_ref:-}" ]]; then
        if docker image inspect "${image_ref}" >/dev/null 2>&1; then
            echo "Removing Docker image ${image_ref}"
            docker rmi "${image_ref}"
        fi
    fi
}

docker_image_validate_pr_id() {
    if [[ -z "${pr_id:-}" ]]; then
        return 0
    fi
    if [[ ! "$pr_id" =~ ^[0-9]+$ ]] || [[ "$pr_id" -eq 0 ]]; then
        echo "error: --pr-id must be a positive integer: ${pr_id}" >&2
        exit 1
    fi
}

docker_image_normalize_backend_tests() {
    if [[ -z "${backend_tests:-}" ]]; then
        return 0
    fi
    backend_tests="$(printf '%s' "$backend_tests" | tr '[:upper:]' '[:lower:]')"
    case "$backend_tests" in
        amdgpu|spirv) ;;
        *)
            echo "error: --backend-tests must be amdgpu or spirv: ${backend_tests}" >&2
            exit 1
            ;;
    esac
}

docker_image_resolve_ref() {
    local name="${image_name:-${IMAGE_NAME:-fuzz-fill-test}}"
    if [[ -n "${pr_id:-}" ]]; then
        image_ref="${name}:llvm-pr-${pr_id}"
    elif [[ -z "${image_ref:-}" ]]; then
        image_ref="${name}:${image_tag:-latest}"
    fi
}

docker_image_validate_build_flags() {
    if [[ -n "${image_ref:-}" && -n "${pr_id:-}" ]]; then
        echo "error: pass only one of --image or --pr-id" >&2
        exit 1
    fi

    if [[ -n "${image_ref:-}" && "${build_image:-0}" -eq 1 ]]; then
        echo "error: --build-image cannot be used with --image" >&2
        exit 1
    fi

    if [[ "${force_build:-0}" -eq 1 && "${build_image:-0}" -eq 0 ]]; then
        echo "error: --force-build requires --build-image" >&2
        exit 1
    fi

    if [[ "${build_image:-0}" -eq 0 ]]; then
        if [[ -n "${llvm_repo:-}" || -n "${backend_tests:-}" || -n "${github_repo:-}" \
              || "${keep_image:-0}" -eq 1 || "${force_build:-0}" -eq 1 ]]; then
            echo "error: --llvm-repo, --backend-tests, --github-repo, --keep-image, and --force-build require --build-image" >&2
            exit 1
        fi
        return 0
    fi

    if [[ -z "${llvm_repo:-}" ]]; then
        echo "error: --llvm-repo is required with --build-image" >&2
        exit 1
    fi
    if [[ -z "${pr_id:-}" ]]; then
        echo "error: --pr-id is required with --build-image" >&2
        exit 1
    fi
    if [[ -z "${backend_tests:-}" ]]; then
        echo "error: --backend-tests is required with --build-image" >&2
        exit 1
    fi
}

docker_image_read_allowlist() {
    local allowlist
    if ! allowlist="$(docker run --rm --entrypoint cat "${image_ref}" /work/.sancov-allowlist 2>/dev/null | tr -d '[:space:]')"; then
        echo "error: failed to read /work/.sancov-allowlist from image: ${image_ref}" >&2
        exit 1
    fi
    if [[ -z "$allowlist" ]]; then
        echo "error: /work/.sancov-allowlist is empty in image: ${image_ref}" >&2
        exit 1
    fi
    printf '%s' "$allowlist"
}

docker_image_ensure() {
    if [[ "${build_image:-0}" -eq 1 && "${keep_image:-0}" -eq 0 ]]; then
        trap docker_image_cleanup_built EXIT
    fi

    if [[ "${build_image:-0}" -eq 1 ]]; then
        if docker image inspect "${image_ref}" >/dev/null 2>&1 && [[ "${force_build:-0}" -eq 0 ]]; then
            echo "Reusing existing Docker image ${image_ref}"
        else
            if [[ "${force_build:-0}" -eq 1 ]]; then
                echo "=== rebuild PR image (--force-build) ==="
            else
                echo "=== build PR image ==="
            fi

            build_args=(
                --llvm-repo "$llvm_repo"
                --pr-id "$pr_id"
                --allowlist "$backend_tests"
            )
            if [[ -n "${github_repo:-}" ]]; then
                build_args+=(--github-repo "$github_repo")
            fi
            if [[ -n "${jobs:-}" ]]; then
                build_args+=(-j "$jobs")
            fi

            "${SCRIPT_DIR}/build-image-pr.sh" "${build_args[@]}"
        fi
    fi

    if ! docker image inspect "${image_ref}" >/dev/null 2>&1; then
        echo "error: image not found: ${image_ref}" >&2
        if [[ -n "${DOCKER_IMAGE_MISSING_HINT:-}" ]]; then
            echo "hint: ${DOCKER_IMAGE_MISSING_HINT}" >&2
        fi
        exit 1
    fi
}
