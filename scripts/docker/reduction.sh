#!/usr/bin/env bash
# Reduction: batch-from-coverage inside a one-shot Docker container.
#
# Bind-mounts a gap-fill output directory at /mounted-gap-fill (read-only) and
# writes case directories under --output (mounted at /mounted-output/).
#
# Pass --bind-repo to run the local fuzz-fill checkout instead of the copy baked
# into the image at build time.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ "${IN_CONTAINER:-}" == 1 ]]; then
    # shellcheck source=scripts/lib/common.sh
    source "${REPO_ROOT}/scripts/lib/common.sh"

    cd "$REPO_ROOT"
    activate_venv_if_present "$REPO_ROOT"
    exec python -m reduce batch-from-coverage "$@"
fi

# shellcheck source=scripts/docker/ensure-image.sh
source "${SCRIPT_DIR}/ensure-image.sh"
# shellcheck source=scripts/docker/docker-image-cli.sh
source "${SCRIPT_DIR}/docker-image-cli.sh"
# shellcheck source=scripts/docker/docker-run.sh
source "${SCRIPT_DIR}/docker-run.sh"
# shellcheck source=scripts/lib/common.sh
source "${REPO_ROOT}/scripts/lib/common.sh"

CONTAINER_WORKDIR="${DOCKER_GAP_CONTAINER_WORKDIR}"
CONTAINER_SCRIPT="$(docker_gap_container_script "$0")"

docker_image_cli_init_vars
bind_repo=0
jobs=""
gap_fill_dir=""
output_dir=""
corpus_dir=""
declare -a passthrough_args=()

usage() {
    cat <<EOF
Usage: $(basename "$0") --gap-fill-dir <path> -n <N> [options]

Run batch-from-coverage in a temporary container.
Gap-fill output is mounted read-only at /mounted-gap-fill/.
Case directories are written under --output (default: <gap-fill-dir>/reduced/).

Required:
  --gap-fill-dir <path>         Host gap-fill output directory
  -n <N>, --n <N>               Reduce the first N gap-fill hits

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

Options (passed to batch-from-coverage):
  --output <path>               Host output directory (default: <gap-fill-dir>/reduced/)
  --corpus-dir <path>           Host fuzz corpus from gap filling (bind-mounted read-only)
  --bind-repo                   Mount the local fuzz-fill checkout at ${CONTAINER_WORKDIR}
  --scaffold-only               Create case dirs only; do not run llvm-reduce
  --ir-template <path>          IR interestingness template (default: src/reduce/template_interesting_ir.sh)
  --mir-template-dir <path>     Directory with interesting_mir.sh (required for llvm_reduce_mir)
  --pipeline <pass-ids>         Comma-separated reduce pass ids (default: llvm_reduce_ir)
  --with-creduce                Append creduce to --pipeline when missing
  --creduce-n <N>               creduce parallelism for pipeline steps
  --pass-under-test <pass>      LLVM pass id for extract_* / interesting_mir.sh
  --mtriple <triple>            Target triple for extract_* / interesting_mir.sh
  --mir-codegen-only            Use interesting_mir_codegen.sh template
  --extract-mir-output <basename>
  --extract-ir-output <basename>
  -j <n>, --jobs <n>            Parallel jobs when building images
  --help, -h                    Show this help

Examples:
  $(basename "$0") --gap-fill-dir ./data/gap-fill-out -n 1

  $(basename "$0") --gap-fill-dir ./data/gap-fill-out -n 3 \\
      --output ./data/reduced-out --scaffold-only

  $(basename "$0") --pr-id 203468 --gap-fill-dir ./data/gap-fill-out -n 2 -j "\$(nproc)"
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
        --help|-h)
            usage
            exit 0
            ;;
        --gap-fill-dir)
            [[ $# -ge 2 ]] || { echo "error: --gap-fill-dir requires a value" >&2; exit 2; }
            gap_fill_dir="$2"
            shift 2
            ;;
        --output)
            [[ $# -ge 2 ]] || { echo "error: --output requires a value" >&2; exit 2; }
            output_dir="$2"
            shift 2
            ;;
        --corpus-dir)
            [[ $# -ge 2 ]] || { echo "error: --corpus-dir requires a value" >&2; exit 2; }
            corpus_dir="$2"
            shift 2
            ;;
        --)
            shift
            passthrough_args+=("$@")
            break
            ;;
        *)
            passthrough_args+=("$1")
            shift
            ;;
    esac
done

if [[ -z "$gap_fill_dir" ]]; then
    echo "error: --gap-fill-dir is required" >&2
    usage >&2
    exit 2
fi

if [[ ! -d "$gap_fill_dir" ]]; then
    echo "error: --gap-fill-dir is not a directory: ${gap_fill_dir}" >&2
    exit 1
fi

gap_fill_dir="$(realpath "$gap_fill_dir")"
if [[ -z "$output_dir" ]]; then
    output_dir="${gap_fill_dir}/reduced"
fi
mkdir -p "$output_dir"
output_dir="$(realpath "$output_dir")"
if [[ -n "$corpus_dir" ]]; then
    if [[ ! -d "$corpus_dir" ]]; then
        echo "error: --corpus-dir is not a directory: ${corpus_dir}" >&2
        exit 1
    fi
    corpus_dir="$(realpath "$corpus_dir")"
fi

validate_jobs "$jobs"

DOCKER_IMAGE_MISSING_HINT="build with ${SCRIPT_DIR}/build-image.sh, or pass --build-image with --llvm-repo and --backend-tests"
docker_image_cli_prepare

echo "Using gap-fill output:"
echo "  gap-fill dir: ${gap_fill_dir}"
echo "  output dir:   ${output_dir}"
if [[ -n "$corpus_dir" ]]; then
    echo "  corpus dir:   ${corpus_dir}"
fi
echo

container_args=(
    --gap-fill-dir /mounted-gap-fill
    --output /mounted-output
)
if [[ -n "$corpus_dir" ]]; then
    container_args+=(--corpus-dir /mounted-candidate-tests)
fi
container_args+=("${passthrough_args[@]}")

docker_env=(-e "IN_CONTAINER=1")
docker_gap_append_jobs_env docker_env

extra_mounts=(
    -v "${gap_fill_dir}:/mounted-gap-fill:ro"
)
if [[ -n "$corpus_dir" ]]; then
    extra_mounts+=(-v "${corpus_dir}:/mounted-candidate-tests:ro")
fi
docker_gap_append_bind_repo_mount extra_mounts

docker_gap_run "$CONTAINER_SCRIPT" "$output_dir" "$image_ref" docker_env extra_mounts container_args

echo "Image: ${image_ref}"
echo "Reduction output: ${output_dir}"
