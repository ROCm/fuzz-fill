#!/usr/bin/env bash
# Stage coverage opt/llc (and clang/clang++ plus their resource headers when built).
# Usage:
#   stage-instrumented-tools.sh \
#     --bin-dir <build/bin> \
#     --llvm-dir <llvm-project checkout> \
#     --commit-file <path> \
#     --out-dir <staging dir> \
#     [--github-repo <owner/name>] \
#     [--targets <list>] \
#     [--enable-projects <list>] \
#     [--pr-id <n>] \
#     [--pr-head-file <path>]

set -euo pipefail

BIN_DIR=""
LLVM_DIR=""
COMMIT_FILE=""
OUT_DIR=""
GITHUB_REPO=""
TARGETS=""
ENABLE_PROJECTS=""
PR_ID=""
PR_HEAD_FILE=""

usage() {
    cat <<EOF
Usage:
  $(basename "$0") --bin-dir <path> --llvm-dir <path> --commit-file <path> --out-dir <path>
                 [--github-repo <owner/name>] [--targets <list>]
                 [--enable-projects <list>]
                 [--pr-id <n>] [--pr-head-file <path>]
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bin-dir) BIN_DIR="$2"; shift 2 ;;
        --llvm-dir) LLVM_DIR="$2"; shift 2 ;;
        --commit-file) COMMIT_FILE="$2"; shift 2 ;;
        --out-dir) OUT_DIR="$2"; shift 2 ;;
        --github-repo) GITHUB_REPO="$2"; shift 2 ;;
        --targets) TARGETS="$2"; shift 2 ;;
        --enable-projects) ENABLE_PROJECTS="$2"; shift 2 ;;
        --pr-id) PR_ID="$2"; shift 2 ;;
        --pr-head-file) PR_HEAD_FILE="$2"; shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *) echo "error: unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ -z "$BIN_DIR" || -z "$LLVM_DIR" || -z "$COMMIT_FILE" || -z "$OUT_DIR" ]]; then
    usage >&2
    exit 2
fi

if [[ -n "$PR_ID" && -z "$PR_HEAD_FILE" ]] || [[ -z "$PR_ID" && -n "$PR_HEAD_FILE" ]]; then
    echo "error: --pr-id and --pr-head-file must be passed together" >&2
    exit 2
fi

if [[ ! -d "$BIN_DIR" ]]; then
    echo "error: bin directory not found: $BIN_DIR" >&2
    exit 1
fi

if [[ ! -f "$LLVM_DIR/LICENSE.TXT" ]]; then
    echo "error: LICENSE.TXT not found under $LLVM_DIR" >&2
    exit 1
fi

if [[ ! -f "$COMMIT_FILE" ]]; then
    echo "error: commit file not found: $COMMIT_FILE" >&2
    exit 1
fi

commit="$(tr -d '[:space:]' < "$COMMIT_FILE")"
if [[ -z "$commit" ]]; then
    echo "error: commit file is empty: $COMMIT_FILE" >&2
    exit 1
fi

pr_head=""
if [[ -n "$PR_HEAD_FILE" ]]; then
    if [[ ! -f "$PR_HEAD_FILE" ]]; then
        echo "error: PR head file not found: $PR_HEAD_FILE" >&2
        exit 1
    fi
    pr_head="$(tr -d '[:space:]' < "$PR_HEAD_FILE")"
    if [[ -z "$pr_head" ]]; then
        echo "error: PR head file is empty: $PR_HEAD_FILE" >&2
        exit 1
    fi
fi

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/bin"

# Preserve symlinks (clang++ is often a symlink to clang).
for tool in opt llc; do
    if [[ ! -x "$BIN_DIR/$tool" ]]; then
        echo "error: missing executable: $BIN_DIR/$tool" >&2
        exit 1
    fi
    cp -a "$BIN_DIR/$tool" "$OUT_DIR/bin/$tool"
done

staged_clang=0
for tool in clang clang++; do
    if [[ -e "$BIN_DIR/$tool" ]]; then
        cp -a "$BIN_DIR/$tool" "$OUT_DIR/bin/$tool"
        staged_clang=1
    fi
done

# In a build tree clang is a symlink to clang-<major>; stage the real binary so
# the links resolve inside bin/.
clang_real=""
if [[ "$staged_clang" -eq 1 ]]; then
    clang_real="$(readlink -f "$BIN_DIR/clang")"
    if [[ "$(dirname "$clang_real")" != "$(readlink -f "$BIN_DIR")" ]]; then
        echo "error: clang resolves outside the bin directory: $clang_real" >&2
        exit 1
    fi
    clang_real_name="$(basename "$clang_real")"
    if [[ ! -e "$OUT_DIR/bin/$clang_real_name" ]]; then
        cp -a "$clang_real" "$OUT_DIR/bin/$clang_real_name"
    fi
fi

# Clang looks up its builtin headers relative to its real executable:
# <bin>/../lib/clang/<major>/include. Keep the same layout in the artifact.
clang_resource_rel=""
if [[ "$staged_clang" -eq 1 ]]; then
    resource_dirs=("$BIN_DIR"/../lib/clang/*/include)
    if [[ ${#resource_dirs[@]} -ne 1 || ! -d "${resource_dirs[0]}" ]]; then
        echo "error: expected one clang resource include dir under $BIN_DIR/../lib/clang/*/include" >&2
        exit 1
    fi
    resource_major="$(basename "$(dirname "${resource_dirs[0]}")")"
    clang_resource_rel="lib/clang/$resource_major/include"
    mkdir -p "$OUT_DIR/lib/clang/$resource_major"
    cp -a "${resource_dirs[0]}" "$OUT_DIR/$clang_resource_rel"
fi

cp -f "$LLVM_DIR/LICENSE.TXT" "$OUT_DIR/LICENSE.TXT"

if [[ -n "$pr_head" ]]; then
    printf '%s\n' "$pr_head" > "$OUT_DIR/pr-head.txt"
fi

{
    echo "Coverage LLVM tools for fuzz-fill source-based coverage"
    echo
    echo "Contents:"
    echo "  bin/opt, bin/llc  Release, source coverage instrumentation"
    if [[ "$staged_clang" -eq 1 ]]; then
        echo "  bin/clang, bin/clang++  Release, source coverage instrumentation"
        echo "  $clang_resource_rel  Clang builtin headers (resource dir) for bin/clang"
    fi
    echo "  LICENSE.TXT       License of the llvm-project revision that produced these binaries"
    if [[ -n "$pr_head" ]]; then
        echo "  pr-head.txt       GitHub PR head SHA these binaries were built from"
    fi
    echo
    echo "These are not unmodified upstream release binaries. opt, llc, and (when present)"
    echo "clang/clang++ were compiled with LLVM source-based coverage instrumentation."
    echo "System libraries they link (libstdc++, zlib, zstd, lzma, …) are not included."
    echo
    if [[ -n "$GITHUB_REPO" ]]; then
        echo "github_repo: $GITHUB_REPO"
    fi
    if [[ -n "$PR_ID" ]]; then
        echo "pr_id: $PR_ID"
    fi
    if [[ -n "$pr_head" ]]; then
        echo "pr_head: $pr_head"
        echo "squash_commit: $commit"
    else
        echo "commit: $commit"
    fi
    if [[ -n "$TARGETS" ]]; then
        echo "targets: $TARGETS"
    fi
    echo "enable_projects: ${ENABLE_PROJECTS:-<none>}"
} > "$OUT_DIR/README.txt"

echo "Coverage tools staged at $OUT_DIR:"
find "$OUT_DIR" \( -type f -o -type l \) -not -path "$OUT_DIR/lib/clang/*" | LC_ALL=C sort
if [[ -n "$clang_resource_rel" ]]; then
    n_headers="$(find "$OUT_DIR/$clang_resource_rel" -type f | wc -l)"
    echo "$OUT_DIR/$clang_resource_rel ($n_headers files)"
fi
