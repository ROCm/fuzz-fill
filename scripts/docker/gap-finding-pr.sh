#!/usr/bin/env bash
# Gap finding (PR): baseline -> added_lines -> target-lines in a one-shot Docker container.
#
# Host output is bind-mounted at /mounted-output/ in the container.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ "${IN_CONTAINER:-}" == 1 ]]; then
    # shellcheck source=scripts/lib/gap-finding-pr.sh
    source "${REPO_ROOT}/scripts/lib/gap-finding-pr.sh"

    commit="${COMMIT_REV:-$(git -C /work/llvm-project rev-parse HEAD)}"

    mapfile -t lit_filters < /mounted-output/.lit-filters

    export LIT_ALLOW_FAILURES=1

    run_gap_finding_pr /mounted-output "$commit" "" "${lit_filters[@]}"
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

CONTAINER_SCRIPT="$(docker_gap_container_script "$0")"

docker_image_cli_init_vars
output_dir=""
lit_filters=()
commit_rev=""
jobs=""

usage() {
    cat <<EOF
Usage: $(basename "$0") (--image <ref> | --pr-id <n>) --output-dir <path> [options]

Run coverage baseline, added_lines, and target-lines in a temporary container.
Artifacts are written under --output-dir (mounted at /mounted-output/).

Required (one of):
  --image <ref>            Full Docker image ref (e.g. fuzz-fill-test:llvm-pr-203468)
  --pr-id <n>              Derive image as \${IMAGE_NAME:-fuzz-fill-test}:llvm-pr-<n>

Required:
  --output-dir <path>      Host output directory (created if missing)

Options:
  --build-image            Build PR image via build-image-pr.sh when missing
  --force-build            Rebuild PR image even when the tag already exists
  --keep-image             Keep the PR image after detection (default: remove it
                           when --build-image was used)
  --llvm-repo <path>       Local llvm-project clone (required with --build-image)
  --backend-tests <target> amdgpu or spirv (required with --build-image)
  --github-repo <owner/repo>
                           GitHub repo hosting the PR (default: llvm/llvm-project)
  --lit-filter <dir>       LIT regex prefix; repeat for multiple (default values available in: scripts/lit-filters-amdgpu.sh for amdgpu, CodeGen/SPIRV for spirv)
  --image-name <name>      Image name when using --pr-id (default: fuzz-fill-test)
  --commit <rev>           Revision for added_lines (default: HEAD in image llvm-project)
  -j <n>, --jobs <n>       Parallel jobs for llvm-lit; with --build-image, also for ninja
  --help, -h               Show this help

Examples:
  $(basename "$0") --build-image --llvm-repo /path/llvm-project --pr-id 203468 \\
      --backend-tests amdgpu --output-dir ./data/gap-finding-pr-203468 -j "\$(nproc)"
  $(basename "$0") --pr-id 203468 --output-dir ./data/gap-finding-pr-203468
  $(basename "$0") --pr-id 203468 --output-dir ./data/gap-finding-pr-203468 \\
      --lit-filter CodeGen/AMDGPU -j "\$(nproc)"
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
            lit_filters+=("$2")
            shift 2
            ;;
        --commit)
            [[ $# -ge 2 ]] || { echo "error: --commit requires a value" >&2; exit 2; }
            commit_rev="$2"
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

if [[ -n "$image_ref" && -n "$pr_id" ]]; then
    echo "error: pass only one of --image or --pr-id" >&2
    exit 1
fi

if [[ -z "$image_ref" && -z "$pr_id" ]]; then
    echo "error: one of --image or --pr-id is required" >&2
    usage >&2
    exit 1
fi

if [[ -z "$output_dir" ]]; then
    echo "error: --output-dir is required" >&2
    usage >&2
    exit 1
fi

validate_jobs "$jobs"

DOCKER_IMAGE_MISSING_HINT="pass --build-image with --llvm-repo and --backend-tests to build it first"
docker_image_cli_prepare

if [[ ${#lit_filters[@]} -eq 0 ]]; then
    image_allowlist="$(docker_image_read_allowlist)"
    mapfile -t lit_filters < <(default_lit_filters_for_allowlist "$image_allowlist")
    echo "Image allowlist: ${image_allowlist} -> ${#lit_filters[@]} lit-filter prefix(es)"
fi

mkdir -p "$output_dir"
output_dir="$(realpath "$output_dir")"

lit_filters_file="${output_dir}/.lit-filters"
printf '%s\n' "${lit_filters[@]}" > "$lit_filters_file"

docker_env=(-e "IN_CONTAINER=1")
if [[ -n "$commit_rev" ]]; then
    docker_env+=(-e "COMMIT_REV=${commit_rev}")
fi
docker_gap_append_jobs_env docker_env

extra_mounts=()
docker_gap_run "$CONTAINER_SCRIPT" "$output_dir" "$image_ref" docker_env extra_mounts

report="${output_dir}/commit_lines_report/target_lines_uncovered.csv"
echo "Wrote ${report}"
echo "Image: ${image_ref}"
echo "LIT filters: ${lit_filters[*]}"

emit_lit_failures_warning "$output_dir" "target_lines_uncovered.csv"
