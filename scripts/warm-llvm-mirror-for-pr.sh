#!/usr/bin/env bash
# Warm a filtered (--filter=blob:none) llvm-project mirror for prepare-pr-llvm.
#
# Fetches the PR head and merge-base objects with full blobs so a subsequent
# --reference --partial-reference prepare is fast and does not lazy-fetch at
# checkout time.
#
# Usage: warm-llvm-mirror-for-pr.sh <mirror_dir> --pr-id <n> [options]

set -euo pipefail

mirror_dir=""
pr_id=""
github_repo="llvm/llvm-project"
base_sha=""

usage() {
    cat <<EOF
Usage: $(basename "$0") <mirror_dir> --pr-id <n> [options]

Warm a filtered llvm-project git mirror before prepare-pr-llvm --reference.

Required:
  <mirror_dir>              Path to the filtered llvm-project mirror
  --pr-id <n>               GitHub pull request number

Options:
  --github-repo <owner/repo>  Repo hosting the PR (default: llvm/llvm-project)
  --base-sha <sha>            PR base commit (default: resolve via gh api)
  --help, -h                  Show this help

Requires: git. Uses gh to resolve PR base when --base-sha is not set.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr-id)
            pr_id="$2"
            shift 2
            ;;
        --github-repo)
            github_repo="$2"
            shift 2
            ;;
        --base-sha)
            base_sha="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        -*)
            echo "error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            if [[ -z "$mirror_dir" ]]; then
                mirror_dir="$1"
                shift
            else
                echo "error: unexpected argument: $1" >&2
                usage >&2
                exit 2
            fi
            ;;
    esac
done

if [[ -z "$mirror_dir" || -z "$pr_id" ]]; then
    echo "error: mirror_dir and --pr-id are required" >&2
    usage >&2
    exit 1
fi

if [[ ! "$pr_id" =~ ^[0-9]+$ ]] || [[ "$pr_id" -eq 0 ]]; then
    echo "error: --pr-id must be a positive integer: ${pr_id}" >&2
    exit 1
fi

if [[ ! -d "$mirror_dir/.git" ]]; then
    echo "error: mirror_dir is not a git repository: ${mirror_dir}" >&2
    exit 1
fi

mirror_dir="$(realpath "$mirror_dir")"

if [[ -z "$base_sha" ]]; then
    if ! command -v gh >/dev/null 2>&1; then
        echo "error: gh is required to resolve PR base (or pass --base-sha)" >&2
        exit 1
    fi
    base_sha="$(gh api "repos/${github_repo}/pulls/${pr_id}" --jq .base.sha)"
    if [[ -z "$base_sha" || "$base_sha" == "null" ]]; then
        echo "error: could not resolve PR base for ${github_repo}#${pr_id}" >&2
        exit 1
    fi
fi

echo "Warming mirror ${mirror_dir} for ${github_repo}#${pr_id}"
echo "  base: ${base_sha}"

git -C "$mirror_dir" fetch origin "pull/${pr_id}/head"
pr_head_sha="$(git -C "$mirror_dir" rev-parse FETCH_HEAD)"
merge_base="$(git -C "$mirror_dir" merge-base "${base_sha}" "${pr_head_sha}")"

if [[ -z "$merge_base" ]]; then
    echo "error: could not find merge-base between base and PR head for ${github_repo}#${pr_id}" >&2
    exit 1
fi

echo "  PR head: ${pr_head_sha}"
echo "  merge-base: ${merge_base}"

git -C "$mirror_dir" fetch --no-filter origin "${merge_base}"

echo "Mirror warm complete."
