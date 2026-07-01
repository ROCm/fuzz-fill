#!/bin/bash

set -euo pipefail

usage() {
    cat <<EOF
Usage: $0 <allowlist> <llvm_dir> <uninstrumented_build_dir> <sancov_build_dir>

  allowlist                 Sanitizer coverage allowlist file
  llvm_dir                  LLVM source tree (directory containing llvm/)
  uninstrumented_build_dir  Prior build from build-llvm.sh; helper tools are symlinked from its bin/
  sancov_build_dir          Output directory for instrumented llc/opt and this tree's llvm-lit/llvm-config

Run build-llvm.sh first. The sancov build is compiled with clang/clang++ from the uninstrumented build's bin/.
Lit helpers that need AMDGPU (llvm-objdump, llvm-mc, llvm-lto2) are built in this tree; other helpers are symlinked from the uninstrumented bin/.
EOF
}

if [[ $# -ne 4 ]]; then
    usage >&2
    exit 1
fi

ALLOWLIST="$1"
LLVM_DIR="$2"
UNINSTRUMENTED_BUILD_DIR="$3"
SANCOV_BUILD_DIR="$4"

if [[ ! -f "$ALLOWLIST" ]]; then
    echo "Error: allowlist file not found: $ALLOWLIST" >&2
    exit 1
fi

if [[ ! -d "$LLVM_DIR/llvm" ]]; then
    echo "Error: LLVM source not found at $LLVM_DIR/llvm" >&2
    exit 1
fi

ALLOWLIST="$(realpath "$ALLOWLIST")"
LLVM_DIR="$(realpath "$LLVM_DIR")"
UNINSTRUMENTED_BUILD_DIR="$(realpath "$UNINSTRUMENTED_BUILD_DIR")"
HELPER_BIN="$UNINSTRUMENTED_BUILD_DIR/bin"

if [[ ! -d "$HELPER_BIN" ]]; then
    echo "Error: uninstrumented bin directory not found: $HELPER_BIN" >&2
    exit 1
fi

C_COMPILER="$HELPER_BIN/clang"
CXX_COMPILER="$HELPER_BIN/clang++"
if [[ ! -x "$C_COMPILER" || ! -x "$CXX_COMPILER" ]]; then
    echo "Error: uninstrumented build must provide $C_COMPILER and $CXX_COMPILER" >&2
    echo "Run build-llvm.sh with LLVM_ENABLE_PROJECTS=clang first." >&2
    exit 1
fi

for tool in llvm-tblgen llvm-min-tblgen; do
    if [[ ! -x "$HELPER_BIN/$tool" ]]; then
        echo "Error: uninstrumented build must provide $HELPER_BIN/$tool" >&2
        echo "Run build-llvm.sh first; TableGen tools are reused via LLVM_NATIVE_TOOL_DIR." >&2
        exit 1
    fi
done

mkdir -p "$SANCOV_BUILD_DIR"
SANCOV_BUILD_DIR="$(realpath "$SANCOV_BUILD_DIR")"
SANCOV_BIN="$SANCOV_BUILD_DIR/bin"
cd "$SANCOV_BUILD_DIR"

SANCOV_FLAGS="-O0 -fno-inline -fsanitize-coverage-allowlist=$ALLOWLIST -fsanitize-coverage=bb,trace-pc-guard"

# Built locally (not symlinked from the X86-only uninstrumented tree).
BUILT_TOOLS=(llc opt llvm-config llvm-objdump llvm-mc llvm-lto2)
# Symlink everything else from the uninstrumented build except these.
SKIP_TOOLS=(llc opt llvm-lit llvm-config llvm-objdump llvm-mc llvm-lto2)

echo "Building instrumented llc/opt and AMDGPU lit helpers..."
echo "  Allowlist:              $ALLOWLIST"
echo "  LLVM source:            $LLVM_DIR"
echo "  Uninstrumented build:   $UNINSTRUMENTED_BUILD_DIR"
echo "  Sancov build:           $SANCOV_BUILD_DIR"
echo "  C compiler:             $C_COMPILER"
echo "  C++ compiler:           $CXX_COMPILER"
echo "  Native tools:           $HELPER_BIN"
echo

cmake -G Ninja \
    -DCMAKE_C_COMPILER="$C_COMPILER" \
    -DCMAKE_CXX_COMPILER="$CXX_COMPILER" \
    -DCMAKE_C_FLAGS="$SANCOV_FLAGS" \
    -DCMAKE_CXX_FLAGS="$SANCOV_FLAGS" \
    -DLLVM_TARGETS_TO_BUILD="X86;AMDGPU;SPIRV" \
    -DLLVM_ENABLE_PROJECTS="" \
    -DLLVM_OPTIMIZED_TABLEGEN=ON \
    -DLLVM_NATIVE_TOOL_DIR="$HELPER_BIN" \
    -DLLVM_ENABLE_ASSERTIONS=OFF \
    -DCMAKE_BUILD_TYPE=Debug \
    -DBUILD_SHARED_LIBS=OFF \
    "$LLVM_DIR/llvm"

# llvm-lit is generated into bin/ during cmake; llvm-config must be built.
ninja "${BUILT_TOOLS[@]}"

for tool in "${BUILT_TOOLS[@]}"; do
    if [[ ! -x "$SANCOV_BIN/$tool" ]]; then
        echo "Error: $tool not found in $SANCOV_BIN after build" >&2
        exit 1
    fi
done

if [[ ! -x "$SANCOV_BIN/llvm-lit" ]]; then
    echo "Error: llvm-lit not found in $SANCOV_BIN after configure" >&2
    exit 1
fi

mkdir -p "$SANCOV_BIN"

should_skip() {
    local name="$1"
    local skip
    for skip in "${SKIP_TOOLS[@]}"; do
        if [[ "$name" == "$skip" ]]; then
            return 0
        fi
    done
    return 1
}

echo "Symlinking uninstrumented helper tools into $SANCOV_BIN..."
linked=0
for helper in "$HELPER_BIN"/*; do
    [[ -f "$helper" ]] || continue
    name="$(basename "$helper")"
    if should_skip "$name"; then
        continue
    fi
    ln -sf "$(realpath --relative-to="$SANCOV_BIN" "$helper")" "$SANCOV_BIN/$name"
    linked=$((linked + 1))
done

echo "Done. Built ${BUILT_TOOLS[*]}, local llvm-lit, and $linked symlinks."
