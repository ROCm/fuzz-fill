#!/usr/bin/env bash
# Shared host-side helpers for docker gap-finding runners (baseline and PR).
# Source after SCRIPT_DIR and REPO_ROOT are set.

: "${SCRIPT_DIR:?SCRIPT_DIR must be set before sourcing gap-finding-docker.sh}"
: "${REPO_ROOT:?REPO_ROOT must be set before sourcing gap-finding-docker.sh}"

docker_gap_finding_source_host_libs() {
    local entrypoint="$1"

    # shellcheck source=scripts/docker/ensure-image.sh
    source "${SCRIPT_DIR}/ensure-image.sh"
    # shellcheck source=scripts/docker/docker-image-cli.sh
    source "${SCRIPT_DIR}/docker-image-cli.sh"
    # shellcheck source=scripts/docker/docker-run.sh
    source "${SCRIPT_DIR}/docker-run.sh"
    # shellcheck source=scripts/lib/common.sh
    source "${REPO_ROOT}/scripts/lib/common.sh"
    # shellcheck source=scripts/lib/lit-filters.sh
    source "${REPO_ROOT}/scripts/lib/lit-filters.sh"
    # shellcheck source=scripts/lib/lit-failures.sh
    source "${REPO_ROOT}/scripts/lib/lit-failures.sh"

    CONTAINER_WORKDIR="${DOCKER_GAP_CONTAINER_WORKDIR}"
    CONTAINER_SCRIPT="$(docker_gap_container_script "$entrypoint")"

    docker_image_cli_init_vars
    output_dir=""
    lit_filters=()
    jobs=""
    bind_repo=0
}

docker_gap_finding_usage_image_select_options() {
    cat <<EOF
Image (one of):
  --image <ref>                 Docker image ref (default: \${IMAGE_NAME:-fuzz-fill-test}:\${IMAGE_TAG:-latest})
  --pr-id <n>                   Use \${IMAGE_NAME:-fuzz-fill-test}:llvm-pr-<n>

EOF
}

docker_gap_finding_usage_image_build_options() {
    cat <<EOF
  --build-image                 Build PR image via build-image-pr.sh when missing
  --force-build                 Rebuild PR image even when the tag already exists
  --keep-image                  Keep PR image after run (default: remove when --build-image)
  --llvm-repo <path>            Local llvm-project clone (required with --build-image)
  --backend-tests <target>      amdgpu or spirv (required with --build-image)
  --github-repo <owner/repo>    GitHub repo hosting the PR (default: llvm/llvm-project)
  --image-name <name>           Image name when using --pr-id (default: fuzz-fill-test)
EOF
}

# Parse --output-dir or --lit-filter. Returns 0 if consumed; sets DOCKER_GAP_FINDING_SHIFT.
docker_gap_finding_try_parse_workflow() {
    DOCKER_GAP_FINDING_SHIFT=0

    case "$1" in
        --output-dir)
            [[ $# -ge 2 ]] || { echo "error: --output-dir requires a value" >&2; exit 2; }
            output_dir="$2"
            DOCKER_GAP_FINDING_SHIFT=2
            return 0
            ;;
        --lit-filter)
            [[ $# -ge 2 ]] || { echo "error: --lit-filter requires a value" >&2; exit 2; }
            lit_filters+=("$2")
            DOCKER_GAP_FINDING_SHIFT=2
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

docker_gap_finding_finish_arg_parse() {
    if [[ $# -gt 0 ]]; then
        echo "error: unexpected argument: $1" >&2
        return 1
    fi
    return 0
}

docker_gap_finding_require_output_dir() {
    if [[ -z "$output_dir" ]]; then
        echo "error: --output-dir is required" >&2
        return 1
    fi
    return 0
}

docker_gap_finding_prepare_output_dir() {
    mkdir -p "$output_dir"
    output_dir="$(realpath "$output_dir")"
}

docker_gap_default_lit_filters_from_image() {
    local allowlist

    if [[ ${#lit_filters[@]} -gt 0 ]]; then
        return 0
    fi

    allowlist="$(docker_image_read_allowlist)"
    mapfile -t lit_filters < <(default_lit_filters_for_allowlist "$allowlist")
    echo "Image allowlist: ${allowlist} -> ${#lit_filters[@]} lit-filter prefix(es)"
}

docker_gap_finding_write_lit_filters_file() {
    local filters_file="${output_dir}/.lit-filters"
    printf '%s\n' "${lit_filters[@]}" > "$filters_file"
}

# Override in entrypoints to parse workflow-specific flags (e.g. --commit).
docker_gap_finding_try_parse_extra() {
    return 1
}

# Parse shared host-side flags. Exits on --help or unknown options.
# Remaining args are passed to docker_gap_finding_finish_arg_parse.
docker_gap_finding_parse_host_args() {
    while [[ $# -gt 0 ]]; do
        if docker_image_cli_try_parse "$1" "${2:-}"; then
            shift "${DOCKER_IMAGE_CLI_SHIFT}"
            continue
        fi
        if docker_gap_cli_try_parse_common "$1" "${2:-}"; then
            shift "${DOCKER_GAP_CLI_SHIFT}"
            continue
        fi
        if docker_gap_finding_try_parse_workflow "$1" "${2:-}"; then
            shift "${DOCKER_GAP_FINDING_SHIFT}"
            continue
        fi
        if docker_gap_finding_try_parse_extra "$1" "${2:-}"; then
            shift "${DOCKER_GAP_FINDING_EXTRA_SHIFT:-1}"
            continue
        fi
        case "$1" in
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

    docker_gap_finding_finish_arg_parse "$@"
}

docker_gap_finding_validate_host_prerequisites() {
    if ! docker_gap_finding_require_output_dir; then
        return 1
    fi
    validate_jobs "$jobs"
    return 0
}

# require_mode: required | optional
docker_gap_finding_validate_image_selection() {
    local require_mode="${1:-optional}"

    if [[ -n "$image_ref" && -n "$pr_id" ]]; then
        echo "error: pass only one of --image or --pr-id" >&2
        exit 1
    fi

    if [[ "$require_mode" == required && -z "$image_ref" && -z "$pr_id" ]]; then
        echo "error: one of --image or --pr-id is required" >&2
        return 1
    fi

    return 0
}

docker_gap_finding_prepare_and_run() {
    local -n _env=$1

    docker_gap_append_jobs_env _env

    local extra_mounts=()
    docker_gap_append_bind_repo_mount extra_mounts

    docker_gap_run "$CONTAINER_SCRIPT" "$output_dir" "$image_ref" _env extra_mounts
}
