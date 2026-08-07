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

# shellcheck source=scripts/docker/gap-finding-docker.sh
source "${SCRIPT_DIR}/gap-finding-docker.sh"
docker_gap_finding_source_host_libs "$0"

commit_rev=""

docker_gap_finding_try_parse_extra() {
    DOCKER_GAP_FINDING_EXTRA_SHIFT=0

    case "$1" in
        --commit)
            [[ $# -ge 2 ]] || { echo "error: --commit requires a value" >&2; exit 2; }
            commit_rev="$2"
            DOCKER_GAP_FINDING_EXTRA_SHIFT=2
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

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
$(docker_gap_finding_usage_image_build_options)
  --lit-filter <dir>       LIT regex prefix; repeat for multiple (default values available in: scripts/lit-filters-amdgpu.sh for amdgpu, CodeGen/SPIRV for spirv)
  --commit <rev>           Revision for added_lines (default: HEAD in image llvm-project)
  --bind-repo              Mount the local fuzz-fill checkout at ${CONTAINER_WORKDIR}
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

if ! docker_gap_finding_parse_host_args "$@"; then
    usage >&2
    exit 2
fi

if ! docker_gap_finding_validate_image_selection required; then
    usage >&2
    exit 1
fi

if ! docker_gap_finding_validate_host_prerequisites; then
    usage >&2
    exit 1
fi

DOCKER_IMAGE_MISSING_HINT="pass --build-image with --llvm-repo and --backend-tests to build it first"
docker_image_cli_prepare

docker_gap_default_lit_filters_from_image multi

docker_gap_finding_prepare_output_dir
docker_gap_finding_write_lit_filters_file

docker_env=(-e "IN_CONTAINER=1")
if [[ -n "$commit_rev" ]]; then
    docker_env+=(-e "COMMIT_REV=${commit_rev}")
fi
docker_gap_finding_prepare_and_run docker_env

report="${output_dir}/commit_lines_report/target_lines_uncovered.csv"
echo "Wrote ${report}"
echo "Image: ${image_ref}"
echo "LIT filters: ${lit_filters[*]}"

emit_lit_failures_warning "$output_dir" "target_lines_uncovered.csv"
