#!/usr/bin/env bash
# Gap filling: candidate-test -> incremental inside a one-shot Docker container.
#
# Requires a gap list from gap finding (baseline or PR), passed as explicit CSV
# paths (same flags as ``coverage incremental``). By default the host corpus is
# bind-mounted read-only at /mounted-candidate-tests (no copy); -n limits work
# inside candidate-test. Pass --stage-candidate-tests to copy the first N inputs
# into a temp dir before mounting. Nothing is baked into the image.
#
# Pass --bind-repo to run the local fuzz-fill checkout instead of the copy baked
# into the image at build time.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ "${IN_CONTAINER:-}" == 1 ]]; then
    # shellcheck source=scripts/lib/gap-filling.sh
    source "${REPO_ROOT}/scripts/lib/gap-filling.sh"

    : "${CANDIDATE_N:?CANDIDATE_N is required}"
    : "${UNCOVERED_CSV:?UNCOVERED_CSV is required}"
    : "${LLC_MAP_CSV:?LLC_MAP_CSV is required}"

    run_candidate_test /mounted-output/candidate_tests /mounted-candidate-tests "$CANDIDATE_N"

    run_incremental \
        /mounted-output/incremental \
        "$UNCOVERED_CSV" \
        "$LLC_MAP_CSV" \
        /mounted-output/candidate_tests
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
# shellcheck source=scripts/lib/candidate-inputs.sh
source "${REPO_ROOT}/scripts/lib/candidate-inputs.sh"

CONTAINER_WORKDIR="${DOCKER_GAP_CONTAINER_WORKDIR}"
CONTAINER_SCRIPT="$(docker_gap_container_script "$0")"

docker_image_cli_init_vars
output_dir=""
llc_address_line_map_csv=""
line_coverage_uncovered_csv=""
jobs=""
bind_repo=0
stage_candidate_tests=0
candidate_tests_dir=""
candidate_n=""

usage() {
    cat <<EOF
Usage: $(basename "$0") --output-dir <path> [options]

Run candidate-test and incremental in a temporary container.
Artifacts are written under --output-dir (mounted at /mounted-output/).

Required:
  --output-dir <path>           Host output directory (created if missing)
  --line-coverage-uncovered-csv <path>
                                Uncovered-lines CSV (``file``, ``line`` columns)
  --llc-address-line-map-csv <path>
                                LLC address-to-line map CSV from the same baseline run
  --candidate-tests-dir <path>  Host corpus root (bind-mounted read-only by default)
  -n <N>, --n <N>               Run only the first N candidate tests (.ll/.bc, sorted)

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
  --stage-candidate-tests       Copy the first N inputs to a temp dir before mounting
                                (default: bind-mount the full --candidate-tests-dir)
  -j <n>, --jobs <n>            Parallel jobs for candidate-test and ninja (build)
  --help, -h                    Show this help

Examples:
  $(basename "$0") --output-dir ./data \\
      --line-coverage-uncovered-csv line_coverage_uncovered.csv \\
      --llc-address-line-map-csv llc_address_line_map.csv \\
      --candidate-tests-dir /path/to/corpus -n 100 -j "\$(nproc)"

  $(basename "$0") --pr-id 203468 --output-dir ./data \\
      --line-coverage-uncovered-csv line_coverage_uncovered.csv \\
      --llc-address-line-map-csv llc_address_line_map.csv \\
      --candidate-tests-dir /path/to/corpus -n 100 -j "\$(nproc)"
EOF
}

validate_candidate_n() {
    if [[ ! "$candidate_n" =~ ^[0-9]+$ ]] || [[ "$candidate_n" -eq 0 ]]; then
        echo "error: -n/--n must be a positive integer: ${candidate_n}" >&2
        exit 1
    fi
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
        --line-coverage-uncovered-csv)
            [[ $# -ge 2 ]] || { echo "error: --line-coverage-uncovered-csv requires a value" >&2; exit 2; }
            line_coverage_uncovered_csv="$2"
            shift 2
            ;;
        --llc-address-line-map-csv)
            [[ $# -ge 2 ]] || { echo "error: --llc-address-line-map-csv requires a value" >&2; exit 2; }
            llc_address_line_map_csv="$2"
            shift 2
            ;;
        --stage-candidate-tests)
            stage_candidate_tests=1
            shift
            ;;
        --candidate-tests-dir)
            [[ $# -ge 2 ]] || { echo "error: --candidate-tests-dir requires a value" >&2; exit 2; }
            candidate_tests_dir="$2"
            shift 2
            ;;
        -n|--n)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            candidate_n="$2"
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

if [[ -z "$candidate_tests_dir" || -z "$candidate_n" ]]; then
    echo "error: --candidate-tests-dir and -n are required" >&2
    usage >&2
    exit 1
fi

validate_candidate_n
if [[ ! -d "$candidate_tests_dir" ]]; then
    echo "error: --candidate-tests-dir is not a directory: ${candidate_tests_dir}" >&2
    exit 1
fi

resolve_gap_profile_csv_paths line_coverage_uncovered_csv llc_address_line_map_csv
validate_jobs "$jobs"

DOCKER_IMAGE_MISSING_HINT="build with ${SCRIPT_DIR}/build-image.sh, or pass --build-image with --llvm-repo and --backend-tests"
docker_image_cli_prepare

container_uncovered_csv="/mounted-profile/line_coverage_uncovered.csv"
container_llc_map_csv="/mounted-profile/llc_address_line_map.csv"

echo "Using coverage profile:"
echo "  uncovered lines: ${line_coverage_uncovered_csv}"
echo "  address map:     ${llc_address_line_map_csv}"

mkdir -p "$output_dir"
output_dir="$(realpath "$output_dir")"
candidate_tests_dir="$(realpath "$candidate_tests_dir")"

if [[ "${stage_candidate_tests}" -eq 1 ]]; then
    candidate_staging_dir="$(mktemp -d -t fuzz-fill-candidate-tests.XXXXXX)"
    cleanup_staging() {
        rm -rf "${candidate_staging_dir}"
    }
    trap cleanup_staging EXIT
    stage_candidate_tests "$candidate_tests_dir" "$candidate_n" "$candidate_staging_dir"
    candidate_mount=(-v "${candidate_staging_dir}:/mounted-candidate-tests:ro")
else
    mapfile -t candidate_files < <(collect_candidate_inputs "$candidate_tests_dir")
    if [[ "${#candidate_files[@]}" -eq 0 ]]; then
        echo "error: no .ll or .bc files under --candidate-tests-dir: ${candidate_tests_dir}" >&2
        exit 1
    fi
    candidate_mount=(-v "${candidate_tests_dir}:/mounted-candidate-tests:ro")
    echo "Bind-mounting candidate corpus (no copy): ${candidate_tests_dir}"
fi

rm -rf "${output_dir}/candidate_tests" "${output_dir}/incremental"

docker_env=(
    -e "IN_CONTAINER=1"
    -e "CANDIDATE_N=${candidate_n}"
    -e "UNCOVERED_CSV=${container_uncovered_csv}"
    -e "LLC_MAP_CSV=${container_llc_map_csv}"
)
docker_gap_append_jobs_env docker_env

extra_mounts=(
    -v "${line_coverage_uncovered_csv}:${container_uncovered_csv}:ro"
    -v "${llc_address_line_map_csv}:${container_llc_map_csv}:ro"
)
extra_mounts+=("${candidate_mount[@]}")
docker_gap_append_bind_repo_mount extra_mounts

docker_gap_run "$CONTAINER_SCRIPT" "$output_dir" "$image_ref" docker_env extra_mounts

echo "Image: ${image_ref}"
report="${output_dir}/incremental/new_coverage.csv"
echo "Wrote ${report}"
