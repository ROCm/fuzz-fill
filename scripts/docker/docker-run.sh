#!/usr/bin/env bash
# Shared docker run helpers for gap docker runners.
# Source after SCRIPT_DIR and REPO_ROOT are set.

: "${REPO_ROOT:?REPO_ROOT must be set before sourcing docker-run.sh}"

DOCKER_GAP_CONTAINER_WORKDIR="/work/fuzz-fill"

docker_gap_container_script() {
    printf '%s/scripts/docker/%s' "$DOCKER_GAP_CONTAINER_WORKDIR" "$(basename "$1")"
}

# Parse --bind-repo or -j/--jobs. Returns 0 if consumed; sets DOCKER_GAP_CLI_SHIFT.
docker_gap_cli_try_parse_common() {
    DOCKER_GAP_CLI_SHIFT=0

    case "$1" in
        --bind-repo)
            bind_repo=1
            DOCKER_GAP_CLI_SHIFT=1
            return 0
            ;;
        -j|--jobs)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            jobs="$2"
            DOCKER_GAP_CLI_SHIFT=2
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

docker_gap_append_bind_repo_mount() {
    local -n _mounts=$1
    if [[ "${bind_repo:-0}" -eq 1 ]]; then
        _mounts+=(-v "${REPO_ROOT}:${DOCKER_GAP_CONTAINER_WORKDIR}")
        echo "Using local fuzz-fill checkout: ${REPO_ROOT}"
    fi
}

docker_gap_append_jobs_env() {
    local -n _env=$1
    if [[ -n "${jobs:-}" ]]; then
        _env+=(-e "JOBS=${jobs}")
    fi
}

# Run the current docker gap workflow script inside a container.
# Optional 6th argument: nameref to an array of args passed to the container script.
docker_gap_run() {
    local container_script="$1"
    local host_output_dir="$2"
    local image="$3"
    local -n _env=$4
    local -n _mounts=$5
    local -a script_args=()
    if [[ $# -ge 6 ]]; then
        local -n _script_args=$6
        script_args=("${_script_args[@]}")
    fi

    docker run --rm \
        -v "${host_output_dir}:/mounted-output" \
        "${_mounts[@]}" \
        "${_env[@]}" \
        -w "${DOCKER_GAP_CONTAINER_WORKDIR}" \
        "${image}" \
        bash "${container_script}" "${script_args[@]}"
}
