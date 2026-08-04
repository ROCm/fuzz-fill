#!/usr/bin/env bash
# Gap reducing: reduce one row from gap-filling output inside a one-shot Docker container.
#
# Requires --output-dir from a prior gap-filling run:
#   incremental/new_coverage.csv
#   candidate_tests/
#
# Writes reduced/ under --output-dir. Pass --bind-repo to use the local fuzz-fill checkout.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONTAINER_WORKDIR="/work/fuzz-fill"
CONTAINER_SCRIPT="${CONTAINER_WORKDIR}/scripts/docker/$(basename "$0")"

if [[ "${IN_CONTAINER:-}" == 1 ]]; then
    # shellcheck source=scripts/lib/gap-reducing.sh
    source "${REPO_ROOT}/scripts/lib/gap-reducing.sh"

    : "${REDUCE_ROW:?REDUCE_ROW is required}"
    : "${PIPELINE:?PIPELINE is required}"
    : "${PREPARE_ONLY:?PREPARE_ONLY is required}"

    export BATCH_REDUCE_PYTHON=python

    if [[ "${PREPARE_ONLY}" -eq 0 ]]; then
        export COVERAGE_LLC=/work/llvm-build-sancov/bin/llc
        export COVERAGE_LLVM_REDUCE=/work/llvm-build-sancov/bin/llvm-reduce
    fi

    run_gap_reducing \
        /mounted-output/incremental/new_coverage.csv \
        /mounted-output/candidate_tests \
        /mounted-output/reduced \
        "$REDUCE_ROW" \
        "$PIPELINE"
    exit 0
fi

# shellcheck source=scripts/docker/ensure-image.sh
source "${SCRIPT_DIR}/ensure-image.sh"

image_name="${IMAGE_NAME:-fuzz-fill-test}"
image_tag="${IMAGE_TAG:-latest}"
image_ref=""
pr_id=""
output_dir=""
reduce_row=1
pipeline="llvm_reduce_ir"
prepare_only=0
bind_repo=0
with_creduce=0
creduce_n=""
pass_under_test=""
mtriple=""
extract_mir_output=""
mir_codegen_only=0
build_image=0
keep_image=0
force_build=0
llvm_repo=""
backend_tests=""
github_repo=""

usage() {
    cat <<EOF
Usage: $(basename "$0") --output-dir <path> [options]

Reduce one row from gap-filling output in a temporary container.
Requires incremental/new_coverage.csv and candidate_tests/ under --output-dir.

Required:
  --output-dir <path>           Gap-fill output directory (mounted at /mounted-output/)

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
  --row <n>                     CSV row to reduce (default: 1)
  --prepare-only                Create harness under reduced/ without running reduce
  --pipeline <ids>              Reduce pipeline pass ids (default: llvm_reduce_ir)
  --with-creduce                Append creduce to the pipeline
  --creduce-n <n>               Parallelism for creduce steps
  --pass-under-test <pass>      For MIR pipelines
  --mtriple <triple>            For MIR pipelines
  --extract-mir-output <name>   Basename for extract_mir_before_pass output
  --mir-codegen-only            Use codegen-only MIR template
  --bind-repo                   Mount the local fuzz-fill checkout at ${CONTAINER_WORKDIR}
  --help, -h                    Show this help

Examples:
  $(basename "$0") --output-dir ./data/fill-100
  $(basename "$0") --pr-id 203468 --output-dir ./data/fill-100 --prepare-only
  $(basename "$0") --bind-repo --output-dir ./data/fill-100 --with-creduce
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image)
            [[ $# -ge 2 ]] || { echo "error: --image requires a value" >&2; exit 2; }
            image_ref="$2"
            shift 2
            ;;
        --pr-id)
            [[ $# -ge 2 ]] || { echo "error: --pr-id requires a value" >&2; exit 2; }
            pr_id="$2"
            shift 2
            ;;
        --output-dir)
            [[ $# -ge 2 ]] || { echo "error: --output-dir requires a value" >&2; exit 2; }
            output_dir="$2"
            shift 2
            ;;
        --row)
            [[ $# -ge 2 ]] || { echo "error: --row requires a value" >&2; exit 2; }
            reduce_row="$2"
            shift 2
            ;;
        --prepare-only)
            prepare_only=1
            shift
            ;;
        --pipeline)
            [[ $# -ge 2 ]] || { echo "error: --pipeline requires a value" >&2; exit 2; }
            pipeline="$2"
            shift 2
            ;;
        --with-creduce)
            with_creduce=1
            shift
            ;;
        --creduce-n)
            [[ $# -ge 2 ]] || { echo "error: --creduce-n requires a value" >&2; exit 2; }
            creduce_n="$2"
            shift 2
            ;;
        --pass-under-test)
            [[ $# -ge 2 ]] || { echo "error: --pass-under-test requires a value" >&2; exit 2; }
            pass_under_test="$2"
            shift 2
            ;;
        --mtriple)
            [[ $# -ge 2 ]] || { echo "error: --mtriple requires a value" >&2; exit 2; }
            mtriple="$2"
            shift 2
            ;;
        --extract-mir-output)
            [[ $# -ge 2 ]] || { echo "error: --extract-mir-output requires a value" >&2; exit 2; }
            extract_mir_output="$2"
            shift 2
            ;;
        --mir-codegen-only)
            mir_codegen_only=1
            shift
            ;;
        --bind-repo)
            bind_repo=1
            shift
            ;;
        --build-image)
            build_image=1
            shift
            ;;
        --keep-image)
            keep_image=1
            shift
            ;;
        --force-build)
            force_build=1
            shift
            ;;
        --llvm-repo)
            [[ $# -ge 2 ]] || { echo "error: --llvm-repo requires a value" >&2; exit 2; }
            llvm_repo="$2"
            shift 2
            ;;
        --backend-tests)
            [[ $# -ge 2 ]] || { echo "error: --backend-tests requires a value" >&2; exit 2; }
            backend_tests="$2"
            shift 2
            ;;
        --github-repo)
            [[ $# -ge 2 ]] || { echo "error: --github-repo requires a value" >&2; exit 2; }
            github_repo="$2"
            shift 2
            ;;
        --image-name)
            [[ $# -ge 2 ]] || { echo "error: --image-name requires a value" >&2; exit 2; }
            image_name="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -z "$output_dir" ]]; then
    echo "error: --output-dir is required" >&2
    usage >&2
    exit 1
fi

if [[ ! "$reduce_row" =~ ^[0-9]+$ ]] || [[ "$reduce_row" -eq 0 ]]; then
    echo "error: --row must be a positive integer: ${reduce_row}" >&2
    exit 1
fi

if [[ -n "$creduce_n" ]] && { [[ ! "$creduce_n" =~ ^[0-9]+$ ]] || [[ "$creduce_n" -eq 0 ]]; }; then
    echo "error: --creduce-n must be a positive integer: ${creduce_n}" >&2
    exit 1
fi

# shellcheck source=scripts/lib/gap-artifacts.sh
source "${REPO_ROOT}/scripts/lib/gap-artifacts.sh"

output_dir="$(realpath "$output_dir")"
coverage_csv="$(gap_fill_coverage_csv "$output_dir")"
candidate_tests_dir="$(gap_fill_candidate_tests_dir "$output_dir")"
validate_gap_fill_artifacts "$coverage_csv" "$candidate_tests_dir" \
    "run scripts/docker/gap-filling.sh first"

docker_image_validate_build_flags
docker_image_normalize_backend_tests
docker_image_validate_pr_id
docker_image_resolve_ref

DOCKER_IMAGE_MISSING_HINT="build with ${SCRIPT_DIR}/build-image.sh, or pass --build-image with --llvm-repo and --backend-tests"
docker_image_ensure

docker_env=(
    -e "IN_CONTAINER=1"
    -e "REDUCE_ROW=${reduce_row}"
    -e "PIPELINE=${pipeline}"
    -e "PREPARE_ONLY=${prepare_only}"
    -e "WITH_CREDUCE=${with_creduce}"
)
if [[ -n "$creduce_n" ]]; then
    docker_env+=(-e "CREDUCE_N=${creduce_n}")
fi
if [[ -n "$pass_under_test" ]]; then
    docker_env+=(-e "PASS_UNDER_TEST=${pass_under_test}")
fi
if [[ -n "$mtriple" ]]; then
    docker_env+=(-e "MTRIPLE=${mtriple}")
fi
if [[ -n "$extract_mir_output" ]]; then
    docker_env+=(-e "EXTRACT_MIR_OUTPUT=${extract_mir_output}")
fi
if [[ "$mir_codegen_only" -eq 1 ]]; then
    docker_env+=(-e "MIR_CODEGEN_ONLY=1")
fi

repo_mount=()
if [[ "${bind_repo}" -eq 1 ]]; then
    repo_mount=(-v "${REPO_ROOT}:${CONTAINER_WORKDIR}")
    echo "Using local fuzz-fill checkout: ${REPO_ROOT}"
fi

echo "Gap-fill output: ${output_dir}"
echo "Reducing row:      ${reduce_row}"
echo "Pipeline:          ${pipeline}"
if [[ "$prepare_only" -eq 1 ]]; then
    echo "Mode:              prepare-only"
fi

docker run --rm \
    -v "${output_dir}:/mounted-output" \
    "${repo_mount[@]}" \
    "${docker_env[@]}" \
    -w "${CONTAINER_WORKDIR}" \
    "${image_ref}" \
    bash "${CONTAINER_SCRIPT}"

echo "Image: ${image_ref}"
echo "Wrote ${output_dir}/reduced/"
