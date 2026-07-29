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
# shellcheck source=scripts/docker/ensure-image.sh
source "${SCRIPT_DIR}/ensure-image.sh"
CONTAINER_WORKDIR="/work/fuzz-fill"

image_name="${IMAGE_NAME:-fuzz-fill-test}"
image_tag="${IMAGE_TAG:-latest}"
image_ref=""
pr_id=""
output_dir=""
lit_filter=""
jobs=""
bind_repo=0
build_image=0
keep_image=0
force_build=0
llvm_repo=""
backend_tests=""
github_repo=""

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

lit_filter_for_allowlist() {
    case "$1" in
        amdgpu) echo "CodeGen/AMDGPU" ;;
        spirv) echo "CodeGen/SPIRV" ;;
        *)
            echo "error: unsupported image allowlist: ${1} (expected amdgpu or spirv)" >&2
            exit 1
            ;;
    esac
}

validate_jobs() {
    if [[ -n "$jobs" ]] && { [[ ! "$jobs" =~ ^[0-9]+$ ]] || [[ "$jobs" -eq 0 ]]; }; then
        echo "error: -j/--jobs must be a positive integer: ${jobs}" >&2
        exit 1
    fi
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
        --lit-filter)
            [[ $# -ge 2 ]] || { echo "error: --lit-filter requires a value" >&2; exit 2; }
            lit_filter="$2"
            shift 2
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
        -j|--jobs)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            jobs="$2"
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

docker_image_validate_build_flags
docker_image_normalize_backend_tests
docker_image_validate_pr_id
docker_image_resolve_ref
validate_jobs

DOCKER_IMAGE_MISSING_HINT="build with ${SCRIPT_DIR}/build-image.sh, or pass --build-image with --llvm-repo and --backend-tests"
docker_image_ensure

if [[ -z "$lit_filter" ]]; then
    image_allowlist="$(docker_image_read_allowlist)"
    lit_filter="$(lit_filter_for_allowlist "$image_allowlist")"
    echo "Image allowlist: ${image_allowlist} -> lit-filter: ${lit_filter}"
fi

mkdir -p "$output_dir"
output_dir="$(realpath "$output_dir")"
rm -rf "${output_dir}/baseline"

docker_env=(-e "LIT_FILTER=${lit_filter}")
if [[ -n "$jobs" ]]; then
    docker_env+=(-e "JOBS=${jobs}")
fi

repo_mount=()
if [[ "${bind_repo}" -eq 1 ]]; then
    repo_mount=(-v "${REPO_ROOT}:${CONTAINER_WORKDIR}")
    echo "Using local fuzz-fill checkout: ${REPO_ROOT}"
fi

docker run --rm \
    -v "${output_dir}:/mounted-output" \
    "${repo_mount[@]}" \
    "${docker_env[@]}" \
    -w "${CONTAINER_WORKDIR}" \
    "${image_ref}" \
    bash -lc '
set -euo pipefail

baseline_args=(
    python -m coverage baseline
    --output-dir /mounted-output/baseline
    --lit-filter "${LIT_FILTER}"
    --lit-allow-failures
)
if [[ -n "${JOBS:-}" ]]; then
    baseline_args+=(-j "${JOBS}")
fi

echo "=== coverage baseline (lit-filter=${LIT_FILTER}) ==="
"${baseline_args[@]}"
'

echo "Image: ${image_ref}"
echo "LIT filter: ${lit_filter}"
echo "Wrote ${output_dir}/baseline/"

lit_failures_json="${output_dir}/baseline/lit_failures.json"
warning_file="${output_dir}/README-WARNING"

fail_count=0
if [[ -f "$lit_failures_json" ]]; then
    fail_count="$(python3 -c '
import json, sys
FAILURE_CODES = {"FAIL", "TIMEOUT", "UNRESOLVED", "XPASS"}
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    print(sum(1 for t in data.get("tests", []) if t.get("code") in FAILURE_CODES))
except Exception:
    print(0)
' "$lit_failures_json")"
fi

if [[ "$fail_count" -gt 0 ]]; then
    msg="WARNING: ${fail_count} LIT test(s) failed during the baseline run (e.g., failed a check, timed out, unresolved, or unexpectedly passed).
Failed tests may lead to an incomplete coverage profile. As a result,
downstream gap lists may report lines as uncovered even though they are
actually covered by a (failing) test.
Review baseline/lit_failures.json for the list of failing tests."

    if [[ -t 1 ]]; then
        printf '%b\n' "\033[1;31m${msg}\033[0m"
    else
        printf '%s\n' "$msg"
    fi

    printf '%s\n' "$msg" > "$warning_file"
    echo "Wrote ${warning_file}"
fi
