#!/usr/bin/env bash
# Prepare a squashed, self-contained llvm-project worktree for a GitHub PR.
#
# Usage: prepare-pr-llvm.sh --pr-id <n> --dest <path> (--reference <path> | --plain-clone) [options]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/prepare-pr-llvm.sh
source "${SCRIPT_DIR}/lib/prepare-pr-llvm.sh"

pr_id=""
dest=""
github_repo=""
reference_repo=""
plain_clone=0
partial_reference=0
base_sha=""
branch=""
squash_msg=""
squash_commit_file=""
reuse=0
self_contained=1

usage() {
    cat <<EOF
Usage: $(basename "$0") --pr-id <n> --dest <path> (--reference <path> | --plain-clone) [options]

Fetch an LLVM pull request, squash it into a single commit, and export a
self-contained llvm-project clone (depth 2: squash + merge-base parent).

Required:
  --pr-id <n>                 GitHub pull request number
  --dest <path>               Output llvm-project directory (created/replaced)

Clone source (one required):
  --reference <path>          Local llvm-project used as clone reference
  --plain-clone               Full git clone from GitHub (no reference)

Options:
  --partial-reference         Reference repo is a --filter=blob:none partial
                               clone (e.g. a CI mirror); clone dest as a real
                               partial-clone client and fetch the PR head
                               with full blobs. Leave unset for full local
                               reference checkouts.
  --github-repo <owner/repo>  GitHub repo hosting the PR (default: llvm/llvm-project)
  --base-sha <sha>            PR base commit (default: resolve via gh)
  --branch <name>             Squash branch name (default: fuzz-fill/pr-<id>-squash)
  --squash-message <msg>      Squash commit message
  --squash-commit-file <path> Write squash OID to this file
  --reuse                     Reuse existing dest when squash-commit-file is valid
  --no-self-contained         Skip depth-2 self-contained export
  --help, -h                  Show this help

Requires: git. Uses gh to resolve PR base when available.

Examples:
  $(basename "$0") --pr-id 214457 --dest ./worktrees/pr-214457/llvm-project \\
      --reference ./llvm-project --squash-commit-file ./worktrees/pr-214457/squash-commit

  $(basename "$0") --pr-id 214457 --dest %t/llvm-project --plain-clone \\
      --squash-commit-file %t/squash-commit
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr-id)
            pr_id="$2"
            shift 2
            ;;
        --dest)
            dest="$2"
            shift 2
            ;;
        --github-repo)
            github_repo="$2"
            shift 2
            ;;
        --reference)
            reference_repo="$2"
            shift 2
            ;;
        --plain-clone)
            plain_clone=1
            shift
            ;;
        --partial-reference)
            partial_reference=1
            shift
            ;;
        --base-sha)
            base_sha="$2"
            shift 2
            ;;
        --branch)
            branch="$2"
            shift 2
            ;;
        --squash-message)
            squash_msg="$2"
            shift 2
            ;;
        --squash-commit-file)
            squash_commit_file="$2"
            shift 2
            ;;
        --reuse)
            reuse=1
            shift
            ;;
        --no-self-contained)
            self_contained=0
            shift
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

if [[ -z "$pr_id" || -z "$dest" ]]; then
    echo "error: --pr-id and --dest are required" >&2
    usage >&2
    exit 1
fi

args=(
    --pr-id "$pr_id"
    --dest "$dest"
)
[[ -n "$github_repo" ]] && args+=(--github-repo "$github_repo")
[[ -n "$reference_repo" ]] && args+=(--reference "$reference_repo")
[[ "$plain_clone" -eq 1 ]] && args+=(--plain-clone)
[[ "$partial_reference" -eq 1 ]] && args+=(--partial-reference)
[[ -n "$base_sha" ]] && args+=(--base-sha "$base_sha")
[[ -n "$branch" ]] && args+=(--branch "$branch")
[[ -n "$squash_msg" ]] && args+=(--squash-message "$squash_msg")
[[ -n "$squash_commit_file" ]] && args+=(--squash-commit-file "$squash_commit_file")
[[ "$reuse" -eq 1 ]] && args+=(--reuse)
[[ "$self_contained" -eq 0 ]] && args+=(--no-self-contained)

prepare_pr_llvm_worktree "${args[@]}"
