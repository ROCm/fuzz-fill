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
        if [[ -n "${llvm_repo:-}" || -n "${backends:-}" || -n "${allowlist:-}" \
              || "${auto_scope:-0}" -eq 1 \
              || -n "${github_repo:-}" || "${keep_image:-0}" -eq 1 \
              || "${force_build:-0}" -eq 1 ]]; then
            echo "error: --llvm-repo, --backends, --allowlist, --auto, --github-repo, --keep-image, and --force-build require --build-image" >&2
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
    if [[ "${auto_scope:-0}" -eq 1 ]]; then
        if [[ -n "${backends:-}" || ${#tests[@]} -gt 0 || -n "${allowlist:-}" ]]; then
            echo "error: --auto cannot be combined with --backends, --tests, or --allowlist" >&2
            exit 1
        fi
    fi
}

docker_image_read_test_suites() {
    if ! docker run --rm --entrypoint cat "${image_ref}" /work/.gap-test-suites 2>/dev/null; then
        printf '%s\n' "llvm/test"
    fi
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

            local build_args build_rc suite
            build_args=(
                --llvm-repo "$llvm_repo"
                --pr-id "$pr_id"
            )
            if [[ "${auto_scope:-0}" -eq 1 ]]; then
                build_args+=(--auto)
            else
                if [[ -n "${backends:-}" ]]; then
                    build_args+=(--targets "$backends")
                fi
                if [[ -n "${allowlist:-}" ]]; then
                    build_args+=(--allowlist "$allowlist")
                fi
                for suite in "${tests[@]}"; do
                    build_args+=(--tests "$suite")
                done
            fi
            if [[ -n "${github_repo:-}" ]]; then
                build_args+=(--github-repo "$github_repo")
            fi
            if [[ -n "${jobs:-}" ]]; then
                build_args+=(-j "$jobs")
            fi

            build_rc=0
            "${SCRIPT_DIR}/build-image-pr.sh" "${build_args[@]}" || build_rc=$?
            if [[ "$build_rc" -eq 2 ]]; then
                exit 0
            fi
            if [[ "$build_rc" -ne 0 ]]; then
                exit "$build_rc"
            fi
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
