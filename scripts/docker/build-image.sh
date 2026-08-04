#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-fuzz-fill-test}"

llvm_dir=""
image_tag="${IMAGE_TAG:-latest}"
allowlist="amdgpu"
sancov_instrumentation_mode=""
llvm_release_version="22.1.8"
ninja_jobs=""
no_cache=0

usage() {
    cat <<EOF
Usage: $(basename "$0") [--llvm-dir <path>] [--tag <tag>] [--allowlist <target>] [options]

Build the fuzz-fill Docker test image.

Options:
  --llvm-dir <path>              Use a local llvm-project checkout instead of downloading
                                 the tagged LLVM source from GitHub. The path must
                                 contain an llvm/ subdirectory.
  --llvm-release-version <ver>   Official LLVM GitHub release for bootstrap toolchain
                                 (default: 22.1.8)
  --tag <tag>                    Docker image tag (default: latest)
  --allowlist <target>           SanitizerCoverage allowlist target: amdgpu or spirv
                                 (default: amdgpu)
  --sancov-instrumentation-mode func|bb|edge
                                 SanitizerCoverage instrumentation mode (default: bb).
                                 fuzz-fill expects basic-block (bb) coverage; func or edge will likely break it.
  -j <n>, --jobs <n>             Parallel jobs for ninja when building LLVM (default: unconstrained)
  --no-cache                     Pass --no-cache to docker build (ignore layer cache)

Environment:
  IMAGE_NAME                     Docker image name (default: fuzz-fill-test)

Examples:
  $(basename "$0")
  $(basename "$0") --llvm-dir llvm-project
  $(basename "$0") --llvm-dir /path/to/llvm-project --tag local-llvm
  $(basename "$0") --allowlist spirv --tag spirv
  $(basename "$0") --sancov-instrumentation-mode edge --tag edge
  $(basename "$0") --llvm-release-version 22.1.8 -j "\$(nproc)"
EOF
}

validate_ninja_jobs() {
    if [[ -n "$ninja_jobs" ]] && { [[ ! "$ninja_jobs" =~ ^[0-9]+$ ]] || [[ "$ninja_jobs" -eq 0 ]]; }; then
        echo "error: -j/--jobs must be a positive integer: ${ninja_jobs}" >&2
        exit 1
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --llvm-dir)
            if [[ $# -lt 2 ]]; then
                echo "error: --llvm-dir requires a value" >&2
                exit 1
            fi
            llvm_dir="$2"
            shift 2
            ;;
        --tag)
            if [[ $# -lt 2 ]]; then
                echo "error: --tag requires a value" >&2
                exit 1
            fi
            image_tag="$2"
            shift 2
            ;;
        --allowlist)
            if [[ $# -lt 2 ]]; then
                echo "error: --allowlist requires a value" >&2
                exit 1
            fi
            allowlist="$2"
            shift 2
            ;;
        --sancov-instrumentation-mode)
            if [[ $# -lt 2 ]]; then
                echo "error: --sancov-instrumentation-mode requires a value" >&2
                exit 1
            fi
            sancov_instrumentation_mode="$2"
            shift 2
            ;;
        --llvm-release-version)
            if [[ $# -lt 2 ]]; then
                echo "error: --llvm-release-version requires a value" >&2
                exit 1
            fi
            llvm_release_version="$2"
            shift 2
            ;;
        -j|--jobs)
            if [[ $# -lt 2 ]]; then
                echo "error: $1 requires a value" >&2
                exit 1
            fi
            ninja_jobs="$2"
            shift 2
            ;;
        --no-cache)
            no_cache=1
            shift
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

case "$allowlist" in
    amdgpu|spirv) ;;
    *)
        echo "error: --allowlist must be amdgpu or spirv: ${allowlist}" >&2
        exit 1
        ;;
esac

case "$sancov_instrumentation_mode" in
    ""|func|bb|edge) ;;
    *)
        echo "error: --sancov-instrumentation-mode must be func, bb, or edge: ${sancov_instrumentation_mode}" >&2
        exit 1
        ;;
esac

validate_ninja_jobs

llvm_context=""
llvm_context_tmp=""
cleanup() {
    if [[ -n "$llvm_context_tmp" ]]; then
        rmdir "$llvm_context_tmp"
    fi
}
trap cleanup EXIT

if [[ -n "$llvm_dir" ]]; then
    if [[ ! -d "${llvm_dir}/llvm" ]]; then
        echo "error: --llvm-dir must be an llvm-project checkout (directory containing llvm/): ${llvm_dir}" >&2
        exit 1
    fi
    llvm_context="$(realpath "${llvm_dir}")"
    echo "Using local llvm-project: ${llvm_context}"
    echo "warning: bootstrap clang/clang++ should be new enough to compile this LLVM source" >&2
else
    llvm_context_tmp="$(mktemp -d -p /tmp)"
    llvm_context="$llvm_context_tmp"
fi

docker_build_args=(
    --build-context "llvm=${llvm_context}"
    --build-arg LLVM_RELEASE_VERSION="${llvm_release_version}"
    --build-arg SANCOV_ALLOWLIST="${allowlist}"
    --build-arg UID="$(id -u)"
    --build-arg GID="$(id -g)"
    --build-arg USERNAME="$(id -un)"
)
if [[ -n "$sancov_instrumentation_mode" ]]; then
    docker_build_args+=(--build-arg SANCOV_INSTRUMENTATION_MODE="${sancov_instrumentation_mode}")
fi
if [[ -n "$ninja_jobs" ]]; then
    docker_build_args+=(--build-arg NINJA_JOBS="${ninja_jobs}")
fi
if [[ "$no_cache" -eq 1 ]]; then
    docker_build_args+=(--no-cache)
fi

docker build \
    "${docker_build_args[@]}" \
    -f "${REPO_ROOT}/Dockerfile" \
    -t "${IMAGE_NAME}:${image_tag}" \
    "${REPO_ROOT}"

echo "Built ${IMAGE_NAME}:${image_tag} for UID=$(id -u) GID=$(id -g) USER=$(id -un)"
