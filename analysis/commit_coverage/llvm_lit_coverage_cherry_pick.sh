#!/bin/bash
# Check out a given LLVM revision and cherry-pick the lit-coverage helper commits
# (UBSAN test env + script/data path updates) on top.
#
# Usage:
#   COMMIT=<sha> ./llvm_lit_coverage_cherry_pick.sh
#   ./llvm_lit_coverage_cherry_pick.sh <sha>
#
# Optional environment:
#   LLVM_REPO   — path to llvm-project (default: sibling of fuzz-fill)
#   BRANCH      — if set, create and checkout this branch at COMMIT before cherry-picking
#                 (otherwise detached HEAD at COMMIT)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# This file lives at fuzz-fill/analysis/commit_coverage/
FUZZ_FILL_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${FUZZ_FILL_ROOT}/../llvm-project" && pwd)}"

COMMIT="${COMMIT:-${1:-}}"

if [[ -z "${COMMIT}" ]]; then
	echo "Error: set COMMIT or pass the target revision as the first argument." >&2
	echo "Example: COMMIT=abc1234 ${0##*/}" >&2
	echo "Example: ${0##*/} abc1234" >&2
	exit 1
fi

# Oldest first — same pair as lit-coverage vs local main (adjust if those SHAs change).
CHERRY1="${CHERRY1:-c6e28fc17076}"
CHERRY2="${CHERRY2:-cfbb3c44c5fd}"

if [[ ! -d "${LLVM_REPO}/.git" ]]; then
	echo "Error: LLVM_REPO is not a git repo: ${LLVM_REPO}" >&2
	echo "Set LLVM_REPO to your llvm-project checkout." >&2
	exit 1
fi

git -C "${LLVM_REPO}" diff --quiet && git -C "${LLVM_REPO}" diff --cached --quiet || {
	echo "Error: working tree not clean in ${LLVM_REPO}. Commit or stash before running." >&2
	exit 1
}

echo "Using LLVM_REPO=${LLVM_REPO}"
if [[ -n "${BRANCH:-}" ]]; then
	echo "Creating branch ${BRANCH} at ${COMMIT}"
	git -C "${LLVM_REPO}" checkout -b "${BRANCH}" "${COMMIT}"
else
	echo "Checking out ${COMMIT} (detached HEAD)"
	git -C "${LLVM_REPO}" checkout "${COMMIT}"
fi

echo "Cherry-picking ${CHERRY1} then ${CHERRY2}"
git -C "${LLVM_REPO}" cherry-pick "${CHERRY1}" "${CHERRY2}"

echo "Done. HEAD is now:"
git -C "${LLVM_REPO}" log -1 --oneline
