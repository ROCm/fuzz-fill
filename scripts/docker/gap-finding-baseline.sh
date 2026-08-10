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

    mapfile -t lit_filters < /mounted-output/.lit-filters

    export LIT_ALLOW_FAILURES=1

    echo "=== coverage baseline (${#lit_filters[@]} lit-filter prefix(es)) ==="
    run_coverage_baseline /mounted-output/baseline "${lit_filters[@]}"
    exit 0
fi

# shellcheck source=scripts/docker/gap-finding-docker.sh
source "${SCRIPT_DIR}/gap-finding-docker.sh"
docker_gap_finding_source_host_libs "$0"

usage() {
    cat <<EOF
Usage: $(basename "$0") --output-dir <path> [options]

Run coverage baseline in a temporary container.
Artifacts are written under --output-dir/baseline/ (mounted at /mounted-output/).

Required:
  --output-dir <path>           Host output directory (created if missing)

$(docker_gap_finding_usage_image_select_options)

Image build (optional; reuses existing image when omitted):
$(docker_gap_finding_usage_image_build_options)

Options:
  --bind-repo                   Mount the local fuzz-fill checkout at ${CONTAINER_WORKDIR}
  --lit-filter <prefix>         LIT --filter= prefix; repeat for multiple (default: from image /work/.sancov-allowlist)
  -j <n>, --jobs <n>            Parallel jobs for llvm-lit and ninja (build)
  --help, -h                    Show this help

Examples:
  $(basename "$0") --output-dir ./data/baseline -j "\$(nproc)"
  $(basename "$0") --pr-id 203468 --output-dir ./data/pr-baseline -j "\$(nproc)"
  $(basename "$0") --build-image --llvm-repo /path/llvm-project --pr-id 203468 \\
      --backend-tests amdgpu --output-dir ./data/pr-baseline -j "\$(nproc)"
EOF
}

if ! docker_gap_finding_parse_host_args "$@"; then
    usage >&2
    exit 2
fi

if ! docker_gap_finding_validate_host_prerequisites; then
    usage >&2
    exit 1
fi

DOCKER_IMAGE_MISSING_HINT="build with ${SCRIPT_DIR}/build-image.sh, or pass --build-image with --llvm-repo and --backend-tests"
docker_image_cli_prepare

docker_gap_default_lit_filters_from_image

docker_gap_finding_prepare_output_dir
docker_gap_finding_write_lit_filters_file
rm -rf "${output_dir}/baseline"

docker_env=(-e "IN_CONTAINER=1")
docker_gap_finding_prepare_and_run docker_env

echo "Image: ${image_ref}"
echo "LIT filters: ${lit_filters[*]}"
echo "Wrote ${output_dir}/baseline/"

emit_lit_failures_warning "$output_dir" "downstream gap lists"
