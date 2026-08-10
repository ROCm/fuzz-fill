#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck source=scripts/lib/prepare-pr-llvm.sh
source "${REPO_ROOT}/scripts/lib/prepare-pr-llvm.sh"

llvm_repo=""
pr_id=""
github_repo=""
image_tag=""
allowlist=""
sancov_instrumentation_mode=""
ninja_jobs=""
keep_clone=0
no_cache=0

usage() {
    cat <<EOF
Usage: $(basename "$0") --llvm-repo <path> --pr-id <n> --allowlist <target> [options]

Fetch an LLVM pull request, squash it into a single commit in a standalone
llvm-project clone, and build the fuzz-fill Docker test image from that tree.

Required:
  --llvm-repo <path>     Local llvm-project git clone (must contain llvm/)
  --pr-id <n>            GitHub pull request number
  --allowlist <target>   SanitizerCoverage allowlist: amdgpu or spirv

Options:
  --sancov-instrumentation-mode func|bb|edge
                         SanitizerCoverage instrumentation mode (default: bb).
                         fuzz-fill expects basic-block (bb) coverage; func or edge will likely break it.
  --github-repo <owner/repo>
                         GitHub repo hosting the PR (default: llvm/llvm-project)
  --tag <tag>            Docker image tag (default: llvm-pr-<pr-id>)
  -j <n>, --jobs <n>     Parallel jobs for ninja when building LLVM (default: unconstrained)
  --keep-clone           Keep this run's llvm-project clone after a successful
                         build (default: remove it)
  --keep-worktree        Alias for --keep-clone
  --no-cache             Pass --no-cache to docker build (ignore layer cache)
  --help, -h             Show this help

Standalone llvm-project clones are created at:
  <fuzz-fill>/.fuzz-fill-llvm-pr-worktrees/pr-<id>-<timestamp>/

Squash branches are named:
  fuzz-fill/pr-<id>-squash-<timestamp>

Requires: git, gh, docker (BuildKit), and scripts/build-image.sh.

Examples:
  $(basename "$0") --llvm-repo ../llvm-project --pr-id 185430 --allowlist amdgpu
  $(basename "$0") --llvm-repo ../llvm-project --pr-id 185430 --allowlist spirv --keep-clone
  $(basename "$0") --llvm-repo ../llvm-project --pr-id 42 --allowlist amdgpu --sancov-instrumentation-mode edge --tag llvm-pr-42 -j 8
EOF
}

validate_ninja_jobs() {
    if [[ -n "$ninja_jobs" ]] && { [[ ! "$ninja_jobs" =~ ^[0-9]+$ ]] || [[ "$ninja_jobs" -eq 0 ]]; }; then
        echo "error: -j/--jobs must be a positive integer: ${ninja_jobs}" >&2
        exit 1
    fi
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "error: required command not found: $1" >&2
        exit 1
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --llvm-repo)
            if [[ $# -lt 2 ]]; then
                echo "error: --llvm-repo requires a value" >&2
                exit 1
            fi
            llvm_repo="$2"
            shift 2
            ;;
        --pr-id)
            if [[ $# -lt 2 ]]; then
                echo "error: --pr-id requires a value" >&2
                exit 1
            fi
            pr_id="$2"
            shift 2
            ;;
        --github-repo)
            if [[ $# -lt 2 ]]; then
                echo "error: --github-repo requires a value" >&2
                exit 1
            fi
            github_repo="$2"
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
        -j|--jobs)
            if [[ $# -lt 2 ]]; then
                echo "error: $1 requires a value" >&2
                exit 1
            fi
            ninja_jobs="$2"
            shift 2
            ;;
        --keep-clone|--keep-worktree)
            keep_clone=1
            shift
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

if [[ $# -gt 0 ]]; then
    echo "error: unexpected argument: $1" >&2
    usage >&2
    exit 2
fi

if [[ -z "$llvm_repo" ]]; then
    echo "error: --llvm-repo is required" >&2
    usage >&2
    exit 1
fi

if [[ -z "$pr_id" ]]; then
    echo "error: --pr-id is required" >&2
    usage >&2
    exit 1
fi

if [[ -z "$allowlist" ]]; then
    echo "error: --allowlist is required" >&2
    usage >&2
    exit 1
fi

if [[ ! "$pr_id" =~ ^[0-9]+$ ]] || [[ "$pr_id" -eq 0 ]]; then
    echo "error: --pr-id must be a positive integer: ${pr_id}" >&2
    exit 1
fi

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

require_command git
require_command gh
require_command docker

if [[ ! -d "$llvm_repo" ]]; then
    echo "error: --llvm-repo is not a directory: ${llvm_repo}" >&2
    exit 1
fi

llvm_repo="$(realpath "$llvm_repo")"

if ! git -C "$llvm_repo" rev-parse --git-dir >/dev/null 2>&1; then
    echo "error: --llvm-repo is not a git repository: ${llvm_repo}" >&2
    exit 1
fi

if [[ ! -d "${llvm_repo}/llvm" ]]; then
    echo "error: --llvm-repo must contain an llvm/ subdirectory: ${llvm_repo}" >&2
    exit 1
fi

github_repo="${github_repo:-llvm/llvm-project}"

if [[ -z "$image_tag" ]]; then
    image_tag="llvm-pr-${pr_id}"
fi

ts="$(date -u +%Y%m%dT%H%M%SZ)"
branch="fuzz-fill/pr-${pr_id}-squash-${ts}"
pr_build_root="${REPO_ROOT}/.fuzz-fill-llvm-pr-worktrees"
docker_llvm_path="${pr_build_root}/pr-${pr_id}-${ts}"
squash_msg="Squash ${github_repo}#${pr_id} for fuzz-fill image build (${ts})"

mkdir -p "$pr_build_root"

prepare_pr_llvm_worktree \
    --pr-id "$pr_id" \
    --dest "$docker_llvm_path" \
    --github-repo "$github_repo" \
    --reference "$llvm_repo" \
    --branch "$branch" \
    --squash-message "$squash_msg"

build_args=(--llvm-dir "$docker_llvm_path" --tag "$image_tag" --allowlist "$allowlist")
if [[ -n "$sancov_instrumentation_mode" ]]; then
    build_args+=(--sancov-instrumentation-mode "$sancov_instrumentation_mode")
fi
if [[ -n "$ninja_jobs" ]]; then
    build_args+=(-j "$ninja_jobs")
fi
if [[ "$no_cache" -eq 1 ]]; then
    build_args+=(--no-cache)
fi

if [[ -n "$sancov_instrumentation_mode" ]]; then
    echo "SanitizerCoverage instrumentation mode: ${sancov_instrumentation_mode}"
else
    echo "SanitizerCoverage instrumentation mode: bb (default)"
fi

echo "Building Docker image ${IMAGE_NAME:-fuzz-fill-test}:${image_tag}"
"${SCRIPT_DIR}/build-image.sh" "${build_args[@]}"

if [[ "$keep_clone" -eq 0 ]]; then
    echo "Removing llvm-project clone ${docker_llvm_path}"
    rm -rf "$docker_llvm_path"
fi

echo "Done: ${IMAGE_NAME:-fuzz-fill-test}:${image_tag} from ${github_repo}#${pr_id} (${branch})"
