#!/usr/bin/env bash
# Gap finding (baseline): run coverage baseline inside a one-shot Docker container.
#
# Host output is bind-mounted at /mounted-output/. Writes baseline/ under --output-dir.
#
# Pass --bind-repo to run the local fuzz-fill checkout instead of the copy baked
# into the image at build time.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ "${IN_CONTAINER:-}" == 1 ]]; then
    # shellcheck source=scripts/lib/coverage-baseline.sh
    source "${REPO_ROOT}/scripts/lib/coverage-baseline.sh"

    : "${LIT_FILTER:?LIT_FILTER is required}"

    export LIT_ALLOW_FAILURES=1

    echo "=== coverage baseline (lit-filter=${LIT_FILTER}) ==="
    run_coverage_baseline /mounted-output/baseline "$LIT_FILTER"
    exit 0
fi

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
CONTAINER_SCRIPT="$(docker_gap_container_script "$0")"

docker_image_cli_init_vars
output_dir=""
lit_filter=""
jobs=""
bind_repo=0

usage() {
    cat <<EOF
Usage: $(basename "$0") --output-dir <path> [options]

Run coverage baseline in a temporary container.
Artifacts are written under --output-dir/baseline/ (mounted at /mounted-output/).

Required:
  --output-dir <path>           Host output directory (created if missing)

Image (one of):
  --image <ref>                 Docker image ref (default: \${IMAGE_NAME:-fuzz-fill-test}:\${IMAGE_TAG:-latest})
  --pr-id <n>                   Use \${IMAGE_NAME:-fuzz-fill-test}:llvm-pr-<n>

Image build (optional; reuses existing image when omitted):
  --build-image                 Build PR image via build-image-pr.sh when missing
  --force-build                 Rebuild PR image even when the tag already exists
  --keep-image                  Keep PR image after run (default: remove when --build-image)
  --llvm-repo <path>            Local llvm-project clone (required with --build-image)
  --backend-tests <target>      amdgpu or spirv (required with --build-image)
  --github-repo <owner/repo>    GitHub repo hosting the PR (default: llvm/llvm-project)
  --image-name <name>           Image name when using --pr-id (default: fuzz-fill-test)

Options:
  --bind-repo                   Mount the local fuzz-fill checkout at ${CONTAINER_WORKDIR}
  --lit-filter <prefix>         LIT --filter= prefix (default: from image /work/.sancov-allowlist)
  -j <n>, --jobs <n>            Parallel jobs for llvm-lit and ninja (build)
  --help, -h                    Show this help

Examples:
  $(basename "$0") --output-dir ./data/baseline -j "\$(nproc)"
  $(basename "$0") --pr-id 203468 --output-dir ./data/pr-baseline -j "\$(nproc)"
  $(basename "$0") --build-image --llvm-repo /path/llvm-project --pr-id 203468 \\
      --backend-tests amdgpu --output-dir ./data/pr-baseline -j "\$(nproc)"
EOF
}

while [[ $# -gt 0 ]]; do
    if docker_image_cli_try_parse "$1" "${2:-}"; then
        shift "${DOCKER_IMAGE_CLI_SHIFT}"
        continue
    fi
    if docker_gap_cli_try_parse_common "$1" "${2:-}"; then
        shift "${DOCKER_GAP_CLI_SHIFT}"
        continue
    fi
    case "$1" in
        --output-dir)
            [[ $# -ge 2 ]] || { echo "error: --output-dir requires a value" >&2; exit 2; }
            output_dir="$2"
            shift 2
            ;;
        --lit-filter)
            [[ $# -ge 2 ]] || { echo "error: --lit-filter requires a value" >&2; exit 2; }
            lit_filter="$2"
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

if [[ $# -gt 0 ]]; then
    echo "error: unexpected argument: $1" >&2
    usage >&2
    exit 2
fi

if [[ -z "$output_dir" ]]; then
    echo "error: --output-dir is required" >&2
    usage >&2
    exit 1
fi

validate_jobs "$jobs"

DOCKER_IMAGE_MISSING_HINT="build with ${SCRIPT_DIR}/build-image.sh, or pass --build-image with --llvm-repo and --backend-tests"
docker_image_cli_prepare

if [[ -z "$lit_filter" ]]; then
    image_allowlist="$(docker_image_read_allowlist)"
    lit_filter="$(lit_filter_for_allowlist "$image_allowlist")"
    echo "Image allowlist: ${image_allowlist} -> lit-filter: ${lit_filter}"
fi

mkdir -p "$output_dir"
output_dir="$(realpath "$output_dir")"
rm -rf "${output_dir}/baseline"

docker_env=(-e "IN_CONTAINER=1" -e "LIT_FILTER=${lit_filter}")
docker_gap_append_jobs_env docker_env

extra_mounts=()
docker_gap_append_bind_repo_mount extra_mounts

docker_gap_run "$CONTAINER_SCRIPT" "$output_dir" "$image_ref" docker_env extra_mounts

echo "Image: ${image_ref}"
echo "LIT filter: ${lit_filter}"
echo "Wrote ${output_dir}/baseline/"

emit_lit_failures_warning "$output_dir" "downstream gap lists"
