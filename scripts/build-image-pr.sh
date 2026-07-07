#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

llvm_repo=""
pr_id=""
github_repo=""
image_tag=""
allowlist=""
ninja_jobs=""
keep_worktree=0

usage() {
    cat <<EOF
Usage: $(basename "$0") --llvm-repo <path> --pr-id <n> --allowlist <target> [options]

Fetch an LLVM pull request, squash it into a single commit in an isolated git
worktree, and build the fuzz-fill Docker test image from that tree.

Required:
  --llvm-repo <path>     Local llvm-project git clone (must contain llvm/)
  --pr-id <n>            GitHub pull request number
  --allowlist <target>   SanitizerCoverage allowlist: amdgpu or spirv

Options:
  --github-repo <owner/repo>
                         GitHub repo hosting the PR (default: llvm/llvm-project)
  --tag <tag>            Docker image tag (default: llvm-pr-<pr-id>)
  -j <n>, --jobs <n>     Parallel jobs for ninja when building LLVM (default: unconstrained)
  --keep-worktree        Keep this run's worktree, branch, and Docker build
                         clone after a successful build (default: remove them)
  --help, -h             Show this help

Worktrees are created at:
  <fuzz-fill>/.fuzz-fill-llvm-pr-worktrees/pr-<id>-<timestamp>/

A standalone llvm-project clone for the Docker build context is created at:
  <fuzz-fill>/.fuzz-fill-llvm-pr-worktrees/.docker-llvm/pr-<id>-<timestamp>/

Branches are named:
  fuzz-fill/pr-<id>-squash-<timestamp>

Requires: git, gh, docker (BuildKit), and scripts/build-image.sh.

Examples:
  $(basename "$0") --llvm-repo ../llvm-project --pr-id 185430 --allowlist amdgpu
  $(basename "$0") --llvm-repo ../llvm-project --pr-id 185430 --allowlist spirv --keep-worktree
  $(basename "$0") --llvm-repo ../llvm-project --pr-id 42 --allowlist amdgpu --tag llvm-pr-42 -j 8
EOF
}

validate_ninja_jobs() {
    if [[ -n "$ninja_jobs" ]] && { [[ ! "$ninja_jobs" =~ ^[0-9]+$ ]] || [[ "$ninja_jobs" -eq 0 ]]; }; then
        echo "error: -j/--jobs must be a positive integer: ${ninja_jobs}" >&2
        exit 1
    fi
}

parse_github_repo_from_remote() {
    local url="$1"
    if [[ "$url" =~ github\.com[:/]([^/]+)/([^/.]+)(\.git)?/?$ ]]; then
        echo "${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
        return 0
    fi
    return 1
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
        -j|--jobs)
            if [[ $# -lt 2 ]]; then
                echo "error: $1 requires a value" >&2
                exit 1
            fi
            ninja_jobs="$2"
            shift 2
            ;;
        --keep-worktree)
            keep_worktree=1
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

base_ref_oid="$(gh api "repos/${github_repo}/pulls/${pr_id}" --jq .base.sha)"
pr_title="$(gh pr view "$pr_id" --repo "$github_repo" --json title -q .title)"

if [[ -z "$base_ref_oid" || "$base_ref_oid" == "null" ]]; then
    echo "error: could not resolve base ref for ${github_repo}#${pr_id}" >&2
    exit 1
fi

echo "Preparing ${github_repo}#${pr_id}: ${pr_title}"
echo "  base: ${base_ref_oid}"

pr_head_ref="refs/fuzz-fill/pr-${pr_id}/head"
origin_repo=""
origin_url=""
if origin_url="$(git -C "$llvm_repo" remote get-url origin 2>/dev/null)"; then
    origin_repo="$(parse_github_repo_from_remote "$origin_url" || true)"
fi

if [[ "$origin_repo" == "$github_repo" ]]; then
    echo "Fetching PR head via origin (${origin_url})"
    git -C "$llvm_repo" fetch origin "pull/${pr_id}/head:${pr_head_ref}"
else
    fetch_url="https://github.com/${github_repo}.git"
    echo "Fetching PR head via ${fetch_url}"
    git -C "$llvm_repo" fetch "$fetch_url" "pull/${pr_id}/head:${pr_head_ref}"
fi

ts="$(date -u +%Y%m%dT%H%M%SZ)"
branch="fuzz-fill/pr-${pr_id}-squash-${ts}"
worktree_root="${REPO_ROOT}/.fuzz-fill-llvm-pr-worktrees"
worktree_path="${worktree_root}/pr-${pr_id}-${ts}"

mkdir -p "$worktree_root"

echo "Creating worktree ${worktree_path} on branch ${branch}"
git -C "$llvm_repo" worktree add -B "$branch" "$worktree_path" "$base_ref_oid"

echo "Squashing PR changes into a single commit"
git -C "$worktree_path" merge --squash "$pr_head_ref"
if ! git -C "$worktree_path" commit -m "Squash ${github_repo}#${pr_id} for fuzz-fill image build (${ts})"; then
    echo "error: squash commit failed (is the PR empty?): ${github_repo}#${pr_id}" >&2
    exit 1
fi

# Worktrees store .git as a gitdir: pointer to the main repo on the host; Docker
# copies that file verbatim, so git commands fail inside the image. Clone a
# self-contained repo for the build context so git-related fuzz-fill commands
# (e.g. added_lines) work in the container. Depth 2 is enough for git show
# --first-parent on HEAD (squash commit + its parent).
docker_llvm_path="${worktree_root}/.docker-llvm/pr-${pr_id}-${ts}"
echo "Creating standalone llvm-project clone for Docker build at ${docker_llvm_path}"
rm -rf "$docker_llvm_path"
mkdir -p "$(dirname "$docker_llvm_path")"
git clone --depth 2 --no-local "file://${worktree_path}" "$docker_llvm_path"
if ! git -C "$docker_llvm_path" rev-parse HEAD >/dev/null 2>&1; then
    echo "error: failed to create standalone llvm-project clone for Docker build" >&2
    exit 1
fi

build_args=(--llvm-dir "$docker_llvm_path" --tag "$image_tag" --allowlist "$allowlist")
if [[ -n "$ninja_jobs" ]]; then
    build_args+=(-j "$ninja_jobs")
fi

echo "Building Docker image ${IMAGE_NAME:-fuzz-fill-test}:${image_tag}"
"${SCRIPT_DIR}/build-image.sh" "${build_args[@]}"

if [[ "$keep_worktree" -eq 0 ]]; then
    echo "Removing worktree ${worktree_path}"
    git -C "$llvm_repo" worktree remove --force "$worktree_path"
    git -C "$llvm_repo" branch -D "$branch" || true
    echo "Removing Docker build clone ${docker_llvm_path}"
    rm -rf "$docker_llvm_path"
fi

echo "Done: ${IMAGE_NAME:-fuzz-fill-test}:${image_tag} from ${github_repo}#${pr_id} (${branch})"
