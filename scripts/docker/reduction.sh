#!/usr/bin/env bash
# Reduction: batch-from-coverage inside a one-shot Docker container.
#
# Bind-mounts a gap-fill output directory at /mounted-gap-fill (read-only) and
# writes case directories under --output-dir (mounted at /mounted-output/).
#
# Pass --bind-repo to run the local fuzz-fill checkout instead of the copy baked
# into the image at build time.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ "${IN_CONTAINER:-}" == 1 ]]; then
    # shellcheck source=scripts/lib/gap-artifacts.sh
    source "${REPO_ROOT}/scripts/lib/gap-artifacts.sh"
    # shellcheck source=scripts/lib/reduction.sh
    source "${REPO_ROOT}/scripts/lib/reduction.sh"

    : "${REDUCTION_N:?REDUCTION_N is required}"
    : "${GAP_FILL_DIR:?GAP_FILL_DIR is required}"
    : "${OUTPUT_DIR:?OUTPUT_DIR is required}"

    new_coverage_csv="$(gap_fill_coverage_csv "$GAP_FILL_DIR")"
    candidate_tests_dir="$(gap_fill_candidate_tests_dir "$GAP_FILL_DIR")"
    validate_batch_reduction_inputs "$new_coverage_csv" "$candidate_tests_dir"

    # shellcheck disable=SC2206
    extra_args=(${REDUCTION_BATCH_EXTRA_ARGS:-})

    if [[ "${SCAFFOLD_ONLY:-0}" -eq 1 ]]; then
        :
    else
        export COVERAGE_LLC="${FUZZ_FILL_LLC:-/work/llvm-build-sancov/bin/llc}"
        export COVERAGE_LLVM_REDUCE="${FUZZ_FILL_LLVM_REDUCE:-/work/llvm-build-sancov/bin/llvm-reduce}"
    fi

    run_batch_from_coverage \
        "$new_coverage_csv" \
        "$candidate_tests_dir" \
        "$OUTPUT_DIR" \
        "$REDUCTION_N" \
        "${extra_args[@]}"
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
# shellcheck source=scripts/lib/gap-artifacts.sh
source "${REPO_ROOT}/scripts/lib/gap-artifacts.sh"
# shellcheck source=scripts/lib/reduction-local.sh
source "${REPO_ROOT}/scripts/lib/reduction-local.sh"
reduction_local_source_libs

CONTAINER_WORKDIR="${DOCKER_GAP_CONTAINER_WORKDIR}"
CONTAINER_SCRIPT="$(docker_gap_container_script "$0")"

docker_image_cli_init_vars
bind_repo=0
jobs=""

usage() {
    cat <<EOF
Usage: $(basename "$0") --gap-fill-dir <path> -n <N> [options]

Run batch-from-coverage in a temporary container.
Gap-fill output is mounted read-only at /mounted-gap-fill/.
Case directories are written under --output-dir (default: <gap-fill-dir>/reduced/).

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

Options:
  --output-dir <path>           Host output directory (default: <gap-fill-dir>/reduced/)
  --candidate-corpus-dir <path> Host fuzz corpus from gap filling (bind-mounted at /mounted-candidate-tests)
  --bind-repo                   Mount the local fuzz-fill checkout at ${CONTAINER_WORKDIR}
  --scaffold-only               Create case dirs only; do not run llvm-reduce
  --template-dir <path>         interesting_ir.sh template (default: example/amd/new-test-1)
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
      --output-dir ./data/reduced-out --scaffold-only

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
        --)
            shift
            break
            ;;
        *)
            if reduction_cli_try_parse "$1" "${2:-}"; then
                shift "${REDUCTION_CLI_SHIFT}"
                continue
            fi
            echo "error: unknown option: $1" >&2
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

if ! reduction_local_validate_required_paths; then
    usage >&2
    exit 1
fi

validate_jobs "$jobs"

DOCKER_IMAGE_MISSING_HINT="build with ${SCRIPT_DIR}/build-image.sh, or pass --build-image with --llvm-repo and --backend-tests"
docker_image_cli_prepare

reduction_local_prepare_paths
mkdir -p "$output_dir"
output_dir="$(realpath "$output_dir")"
gap_fill_dir="$(realpath "$gap_fill_dir")"

echo "Using gap-fill output:"
echo "  gap-fill dir:    ${gap_fill_dir}"
echo "  new coverage:    ${new_coverage_csv}"
echo "  candidate tests: ${candidate_tests_dir}"
if [[ -n "$candidate_corpus_dir" ]]; then
    echo "  candidate corpus: ${candidate_corpus_dir}"
fi
echo "  output dir:      ${output_dir} (n=${reduction_n})"
if [[ "$scaffold_only" -eq 1 ]]; then
    echo "  mode:            scaffold-only"
fi

rm -rf "${output_dir:?}"/*
mkdir -p "$output_dir"

reduction_local_batch_extra_args
extra_args_flat="${REDUCTION_BATCH_EXTRA_ARGS[*]-}"

docker_env=(
    -e "IN_CONTAINER=1"
    -e "REDUCTION_N=${reduction_n}"
    -e "GAP_FILL_DIR=/mounted-gap-fill"
    -e "OUTPUT_DIR=/mounted-output"
    -e "SCAFFOLD_ONLY=${scaffold_only}"
    -e "REDUCTION_BATCH_EXTRA_ARGS=${extra_args_flat}"
)
docker_gap_append_jobs_env docker_env

extra_mounts=(
    -v "${gap_fill_dir}:/mounted-gap-fill:ro"
)
if [[ -n "$candidate_corpus_dir" ]]; then
    extra_mounts+=(-v "${candidate_corpus_dir}:/mounted-candidate-tests:ro")
    docker_env+=(-e "REDUCTION_CORPUS_DIR=/mounted-candidate-tests")
fi
docker_gap_append_bind_repo_mount extra_mounts

docker_gap_run "$CONTAINER_SCRIPT" "$output_dir" "$image_ref" docker_env extra_mounts

echo "Image: ${image_ref}"
echo "Reduction output: ${output_dir}"
