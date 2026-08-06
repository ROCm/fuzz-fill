#!/usr/bin/env bash
# Prepare a squashed llvm-project worktree for an LLVM GitHub pull request.
# Source from entrypoints; do not execute directly.
#
# After prepare_pr_llvm_worktree succeeds:
#   PREPARE_PR_REPO_DIR   - path to the llvm-project checkout
#   PREPARE_PR_SQUASH_OID - squash commit hash
#   PREPARE_PR_BRANCH     - checked-out branch name

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"

PREPARE_PR_REPO_DIR=""
PREPARE_PR_SQUASH_OID=""
PREPARE_PR_BRANCH=""

prepare_pr_require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "error: required command not found: $1" >&2
        return 1
    fi
}

prepare_pr_commit_available() {
    local repo="$1"
    local sha="$2"
    git -C "$repo" rev-parse --verify "${sha}^{commit}" >/dev/null 2>&1
}

prepare_pr_ensure_commit_available() {
    local repo="$1"
    local sha="$2"
    local label="$3"
    local fetch_url="$4"

    if prepare_pr_commit_available "$repo" "$sha"; then
        return 0
    fi

    echo "${label} ${sha} not in local object store; fetching from ${fetch_url}"
    git -C "$repo" fetch "$fetch_url" "${sha}"
    if ! prepare_pr_commit_available "$repo" "$sha"; then
        echo "error: could not resolve ${label} ${sha}" >&2
        return 1
    fi
}

prepare_pr_export_self_contained_clone() {
    local repo="$1"
    local minimal_path="${repo}.minimal"

    # Reference clones use alternates; reclone depth 2 keeps squash + merge-base
    # parent for git show --first-parent in added_lines.
    rm -rf "$minimal_path"
    git clone --depth 2 --no-local "file://${repo}" "$minimal_path"
    rm -rf "$repo"
    mv "$minimal_path" "$repo"
}

prepare_pr_resolve_metadata() {
    local github_repo="$1"
    local pr_id="$2"

    PREPARE_PR_BASE_SHA=""
    PREPARE_PR_TITLE=""

    if command -v gh >/dev/null 2>&1; then
        PREPARE_PR_BASE_SHA="$(gh api "repos/${github_repo}/pulls/${pr_id}" --jq .base.sha 2>/dev/null || true)"
        PREPARE_PR_TITLE="$(gh pr view "$pr_id" --repo "$github_repo" --json title -q .title 2>/dev/null || true)"
    fi

    if [[ -z "$PREPARE_PR_BASE_SHA" || "$PREPARE_PR_BASE_SHA" == "null" ]]; then
        return 1
    fi
    return 0
}

prepare_pr_create_clone() {
    local dest="$1"
    local github_repo="$2"
    local clone_mode="$3"
    local reference_repo="${4:-}"

    local fetch_url="https://github.com/${github_repo}.git"

    rm -rf "$dest"
    mkdir -p "$(dirname "$dest")"

    case "$clone_mode" in
        reference)
            echo "Creating reference clone at ${dest}"
            git clone --reference "$reference_repo" -n "file://${reference_repo}" "$dest"
            ;;
        plain)
            echo "Cloning ${fetch_url} into ${dest}"
            git clone "$fetch_url" "$dest"
            ;;
        *)
            echo "error: prepare_pr_create_clone: unknown clone mode: ${clone_mode}" >&2
            return 1
            ;;
    esac
}

prepare_pr_squash_in_repo() {
    local repo="$1"
    local github_repo="$2"
    local pr_id="$3"
    local base_sha="$4"
    local branch="$5"
    local squash_msg="$6"

    local pr_head_ref="refs/fuzz-fill/pr-${pr_id}/head"
    local fetch_url="https://github.com/${github_repo}.git"

    prepare_pr_ensure_commit_available "$repo" "$base_sha" "PR base commit" "$fetch_url"

    echo "Fetching PR head via ${fetch_url}"
    git -C "$repo" fetch "$fetch_url" "pull/${pr_id}/head:${pr_head_ref}"

    local merge_base_oid pr_head_oid pr_tree_oid merge_base_tree_oid squash_oid
    merge_base_oid="$(git -C "$repo" merge-base "$base_sha" "$pr_head_ref")"
    if [[ -z "$merge_base_oid" ]]; then
        echo "error: could not find merge-base between base and PR head for ${github_repo}#${pr_id}" >&2
        return 1
    fi

    pr_head_oid="$(git -C "$repo" rev-parse "$pr_head_ref")"
    pr_tree_oid="$(git -C "$repo" rev-parse "${pr_head_ref}^{tree}")"
    merge_base_tree_oid="$(git -C "$repo" rev-parse "${merge_base_oid}^{tree}")"

    echo "  merge-base: ${merge_base_oid}"
    echo "  PR head: ${pr_head_oid}"

    if [[ "$merge_base_tree_oid" == "$pr_tree_oid" ]]; then
        echo "error: PR has no changes vs merge-base ${merge_base_oid}: ${github_repo}#${pr_id}" >&2
        return 1
    fi

    echo "Creating single squash commit (PR head tree, merge-base parent)"
    # Do not rely on the caller's git config (lit/CI may not expose ~/.gitconfig).
    squash_oid="$(
        git -C "$repo" \
            -c user.name=fuzz-fill \
            -c user.email=fuzz-fill@amd \
            commit-tree "$pr_tree_oid" -p "$merge_base_oid" -m "$squash_msg"
    )"
    if [[ -z "$squash_oid" ]]; then
        echo "error: failed to create squash commit for ${github_repo}#${pr_id}" >&2
        return 1
    fi

    git -C "$repo" checkout -B "$branch" "$squash_oid"
    PREPARE_PR_SQUASH_OID="$squash_oid"
    PREPARE_PR_BRANCH="$branch"
    return 0
}

# prepare_pr_llvm_worktree [options]
#
# Options:
#   --pr-id <n>                 (required)
#   --dest <path>               (required) llvm-project worktree path
#   --github-repo <owner/repo>  (default: llvm/llvm-project)
#   --reference <path>          reference clone source
#   --plain-clone               clone from GitHub instead of --reference
#   --base-sha <sha>            override PR base (default: gh api)
#   --branch <name>             squash branch (default: fuzz-fill/pr-<id>-squash)
#   --squash-message <msg>      squash commit message
#   --squash-commit-file <path> write squash OID; reuse when valid with --reuse
#   --reuse                     skip when dest + squash-commit-file are valid
#   --no-self-contained         skip depth-2 self-contained export (not recommended)
prepare_pr_llvm_worktree() {
    local pr_id=""
    local dest=""
    local github_repo="llvm/llvm-project"
    local reference_repo=""
    local plain_clone=0
    local base_sha=""
    local branch=""
    local squash_msg=""
    local squash_commit_file=""
    local reuse=0
    local self_contained=1

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
            *)
                echo "error: prepare_pr_llvm_worktree: unknown option: $1" >&2
                return 2
                ;;
        esac
    done

    if [[ -z "$pr_id" || -z "$dest" ]]; then
        echo "error: prepare_pr_llvm_worktree requires --pr-id and --dest" >&2
        return 2
    fi

    if [[ ! "$pr_id" =~ ^[0-9]+$ ]] || [[ "$pr_id" -eq 0 ]]; then
        echo "error: --pr-id must be a positive integer: ${pr_id}" >&2
        return 1
    fi

    if [[ "$plain_clone" -eq 1 && -n "$reference_repo" ]]; then
        echo "error: pass only one of --plain-clone or --reference" >&2
        return 1
    fi

    if [[ "$plain_clone" -eq 0 && -z "$reference_repo" ]]; then
        echo "error: --reference is required unless --plain-clone is set" >&2
        return 1
    fi

    dest="$(realpath -m "$dest")"
    PREPARE_PR_REPO_DIR="$dest"

    if [[ "$reuse" -eq 1 && -n "$squash_commit_file" && -f "$squash_commit_file" ]]; then
        local cached_oid
        cached_oid="$(tr -d '[:space:]' <"$squash_commit_file")"
        if [[ -n "$cached_oid" ]] && git -C "$dest" cat-file -e "${cached_oid}^{commit}" 2>/dev/null; then
            echo "Reusing PR worktree at ${dest} (commit ${cached_oid})"
            PREPARE_PR_SQUASH_OID="$cached_oid"
            PREPARE_PR_BRANCH="$(git -C "$dest" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
            return 0
        fi
    fi

    prepare_pr_require_command git || return 1

    if [[ -z "$base_sha" ]]; then
        if ! prepare_pr_resolve_metadata "$github_repo" "$pr_id"; then
            echo "error: could not resolve PR base for ${github_repo}#${pr_id} (need gh or --base-sha)" >&2
            return 1
        fi
        base_sha="$PREPARE_PR_BASE_SHA"
    fi

    if [[ -n "$PREPARE_PR_TITLE" ]]; then
        echo "Preparing ${github_repo}#${pr_id}: ${PREPARE_PR_TITLE}"
    else
        echo "Preparing ${github_repo}#${pr_id}"
    fi
    echo "  base (target branch tip): ${base_sha}"

    if [[ -z "$branch" ]]; then
        branch="fuzz-fill/pr-${pr_id}-squash"
    fi
    if [[ -z "$squash_msg" ]]; then
        squash_msg="Squash ${github_repo}#${pr_id} for fuzz-fill"
    fi

    local clone_mode="reference"
    if [[ "$plain_clone" -eq 1 ]]; then
        clone_mode="plain"
        reference_repo=""
    else
        reference_repo="$(realpath "$reference_repo")"
        if [[ ! -d "${reference_repo}/llvm" ]]; then
            echo "error: --reference must be an llvm-project checkout: ${reference_repo}" >&2
            return 1
        fi
    fi

    prepare_pr_create_clone "$dest" "$github_repo" "$clone_mode" "$reference_repo"

    prepare_pr_squash_in_repo "$dest" "$github_repo" "$pr_id" "$base_sha" "$branch" "$squash_msg"

    if [[ "$self_contained" -eq 1 ]]; then
        echo "Exporting self-contained clone (depth 2)"
        prepare_pr_export_self_contained_clone "$dest"
        if ! git -C "$dest" rev-parse HEAD >/dev/null 2>&1; then
            echo "error: failed to create self-contained llvm-project clone at ${dest}" >&2
            return 1
        fi
        PREPARE_PR_SQUASH_OID="$(git -C "$dest" rev-parse HEAD)"
    fi

    if [[ -n "$squash_commit_file" ]]; then
        mkdir -p "$(dirname "$squash_commit_file")"
        printf '%s\n' "$PREPARE_PR_SQUASH_OID" >"$squash_commit_file"
    fi

    echo "Squash commit: ${PREPARE_PR_SQUASH_OID}"
    return 0
}
