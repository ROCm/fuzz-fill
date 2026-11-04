#!/usr/bin/env bash
# Stage instrumented opt/llc and the Release sancov helper for upload.
# Usage:
#   stage-instrumented-tools.sh \
#     --bin-dir <build/bin> \
#     --llvm-dir <llvm-project checkout> \
#     --commit-file <path> \
#     --out-dir <staging dir> \
#     [--github-repo <owner/name>] \
#     [--allowlist <path or name>] \
#     [--targets <list>] \
#     [--enable-projects <list>] \
#     [--allow-inline true|false]

set -euo pipefail

BIN_DIR=""
LLVM_DIR=""
COMMIT_FILE=""
OUT_DIR=""
GITHUB_REPO=""
ALLOWLIST=""
TARGETS=""
ENABLE_PROJECTS=""
ALLOW_INLINE=""

usage() {
    cat <<EOF
Usage:
  $(basename "$0") --bin-dir <path> --llvm-dir <path> --commit-file <path> --out-dir <path>
                 [--github-repo <owner/name>] [--allowlist <path>] [--targets <list>]
                 [--enable-projects <list>] [--allow-inline true|false]
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bin-dir) BIN_DIR="$2"; shift 2 ;;
        --llvm-dir) LLVM_DIR="$2"; shift 2 ;;
        --commit-file) COMMIT_FILE="$2"; shift 2 ;;
        --out-dir) OUT_DIR="$2"; shift 2 ;;
        --github-repo) GITHUB_REPO="$2"; shift 2 ;;
        --allowlist) ALLOWLIST="$2"; shift 2 ;;
        --targets) TARGETS="$2"; shift 2 ;;
        --enable-projects) ENABLE_PROJECTS="$2"; shift 2 ;;
        --allow-inline) ALLOW_INLINE="$2"; shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *) echo "error: unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ -z "$BIN_DIR" || -z "$LLVM_DIR" || -z "$COMMIT_FILE" || -z "$OUT_DIR" ]]; then
    usage >&2
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

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/bin"

for tool in opt llc sancov; do
    if [[ ! -x "$BIN_DIR/$tool" ]]; then
        echo "error: missing executable: $BIN_DIR/$tool" >&2
        exit 1
    fi
    cp -f "$BIN_DIR/$tool" "$OUT_DIR/bin/$tool"
done

cp -f "$LLVM_DIR/LICENSE.TXT" "$OUT_DIR/LICENSE.TXT"

allowlist_name=""
if [[ -n "$ALLOWLIST" ]]; then
    allowlist_name="$(basename "$ALLOWLIST")"
fi

no_inline="enabled"
if [[ "$ALLOW_INLINE" == "true" ]]; then
    no_inline="omitted"
fi

{
    echo "Instrumented LLVM tools for fuzz-fill SanitizerCoverage"
    echo
    echo "Contents:"
    echo "  bin/opt, bin/llc  RelWithDebInfo, SanitizerCoverage (bb,trace-pc-guard)"
    echo "  bin/sancov        Release helper without SanitizerCoverage"
    echo "  LICENSE.TXT       License of the llvm-project revision that produced these binaries"
    echo
    echo "These are not unmodified upstream release binaries. opt and llc were compiled"
    echo "with SanitizerCoverage for coverage measurement. System libraries they link"
    echo "(libstdc++, zlib, zstd, lzma, …) are not included."
    echo
    if [[ -n "$GITHUB_REPO" ]]; then
        echo "github_repo: $GITHUB_REPO"
    fi
    echo "commit: $commit"
    if [[ -n "$allowlist_name" ]]; then
        echo "allowlist: $allowlist_name"
    fi
    if [[ -n "$TARGETS" ]]; then
        echo "targets: $TARGETS"
    fi
    echo "enable_projects: ${ENABLE_PROJECTS:-<none>}"
    if [[ -n "$ALLOW_INLINE" ]]; then
        echo "allow_inline: $ALLOW_INLINE"
        echo "-fno-inline: $no_inline"
    fi
} > "$OUT_DIR/README.txt"

echo "Instrumented tools staged at $OUT_DIR:"
find "$OUT_DIR" -type f | LC_ALL=C sort
