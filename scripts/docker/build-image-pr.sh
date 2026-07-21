#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

llvm_repo=""
pr_id=""
github_repo=""
image_tag=""
allowlist=""
ninja_jobs=""
keep_clone=0

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
  --github-repo <owner/repo>
                         GitHub repo hosting the PR (default: llvm/llvm-project)
  --tag <tag>            Docker image tag (default: llvm-pr-<pr-id>)
  -j <n>, --jobs <n>     Parallel jobs for ninja when building LLVM (default: unconstrained)
  --keep-clone           Keep this run's llvm-project clone after a successful
                         build (default: remove it)
  --keep-worktree        Alias for --keep-clone
  --help, -h             Show this help

Standalone llvm-project clones are created at:
  <fuzz-fill>/.fuzz-fill-llvm-pr-worktrees/pr-<id>-<timestamp>/

Squash branches are named:
  fuzz-fill/pr-<id>-squash-<timestamp>

Requires: git, gh, docker (BuildKit), and scripts/build-image.sh.

Examples:
  $(basename "$0") --llvm-repo ../llvm-project --pr-id 185430 --allowlist amdgpu
  $(basename "$0") --llvm-repo ../llvm-project --pr-id 185430 --allowlist spirv --keep-clone
  $(basename "$0") --llvm-repo ../llvm-project --pr-id 42 --allowlist amdgpu --tag llvm-pr-42 -j 8
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

export_self_contained_clone() {
    local repo="$1"
    local minimal_path="${repo}.minimal"

    # Worktrees and reference clones use alternates; Docker copies .git verbatim,
    # so git commands fail inside the image unless the repo is self-contained.
    # Depth 2 is enough for git show --first-parent on HEAD (squash + merge-base).
    rm -rf "$minimal_path"
    git clone --depth 2 --no-local "file://${repo}" "$minimal_path"
    rm -rf "$repo"
    mv "$minimal_path" "$repo"
}

commit_available() {
    local repo="$1"
    local sha="$2"
    git -C "$repo" rev-parse --verify "${sha}^{commit}" >/dev/null 2>&1
}

ensure_commit_available() {
    local repo="$1"
    local sha="$2"
    local label="$3"
    local fetch_url="$4"

    if commit_available "$repo" "$sha"; then
        return 0
    fi

    echo "${label} ${sha} not in local object store; fetching from ${fetch_url}"
    git -C "$repo" fetch "$fetch_url" "${sha}"
    if ! commit_available "$repo" "$sha"; then
        echo "error: could not resolve ${label} ${sha} from --llvm-repo or ${fetch_url}" >&2
        echo "hint: check --github-repo, network access, and that the PR still exists" >&2
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
        --keep-clone|--keep-worktree)
            keep_clone=1
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
echo "  base (target branch tip): ${base_ref_oid}"

pr_head_ref="refs/fuzz-fill/pr-${pr_id}/head"
pr_fetch_url="https://github.com/${github_repo}.git"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
branch="fuzz-fill/pr-${pr_id}-squash-${ts}"
pr_build_root="${REPO_ROOT}/.fuzz-fill-llvm-pr-worktrees"
docker_llvm_path="${pr_build_root}/pr-${pr_id}-${ts}"

mkdir -p "$pr_build_root"
rm -rf "$docker_llvm_path"

echo "Creating standalone llvm-project clone at ${docker_llvm_path}"
git clone --reference "$llvm_repo" -n "file://${llvm_repo}" "$docker_llvm_path"

ensure_commit_available "$docker_llvm_path" "$base_ref_oid" "PR base commit" "$pr_fetch_url"

echo "Fetching PR head via ${pr_fetch_url}"
git -C "$docker_llvm_path" fetch "$pr_fetch_url" "pull/${pr_id}/head:${pr_head_ref}"

merge_base_oid="$(git -C "$docker_llvm_path" merge-base "$base_ref_oid" "$pr_head_ref")"
if [[ -z "$merge_base_oid" ]]; then
    echo "error: could not find merge-base between base and PR head for ${github_repo}#${pr_id}" >&2
    exit 1
fi

pr_head_oid="$(git -C "$docker_llvm_path" rev-parse "$pr_head_ref")"
pr_tree_oid="$(git -C "$docker_llvm_path" rev-parse "${pr_head_ref}^{tree}")"
merge_base_tree_oid="$(git -C "$docker_llvm_path" rev-parse "${merge_base_oid}^{tree}")"

echo "  merge-base: ${merge_base_oid}"
echo "  PR head: ${pr_head_oid}"

if [[ "$merge_base_tree_oid" == "$pr_tree_oid" ]]; then
    echo "error: PR has no changes vs merge-base ${merge_base_oid}: ${github_repo}#${pr_id}" >&2
    exit 1
fi

echo "Creating single squash commit (PR head tree, merge-base parent)"
squash_msg="Squash ${github_repo}#${pr_id} for fuzz-fill image build (${ts})"
squash_oid="$(git -C "$docker_llvm_path" commit-tree "$pr_tree_oid" -p "$merge_base_oid" -m "$squash_msg")"
if [[ -z "$squash_oid" ]]; then
    echo "error: failed to create squash commit for ${github_repo}#${pr_id}" >&2
    exit 1
fi

git -C "$docker_llvm_path" checkout -B "$branch" "$squash_oid"

echo "Exporting self-contained clone for Docker build (depth 2)"
export_self_contained_clone "$docker_llvm_path"
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

if [[ "$keep_clone" -eq 0 ]]; then
    echo "Removing llvm-project clone ${docker_llvm_path}"
    rm -rf "$docker_llvm_path"
fi

echo "Done: ${IMAGE_NAME:-fuzz-fill-test}:${image_tag} from ${github_repo}#${pr_id} (${branch})"
