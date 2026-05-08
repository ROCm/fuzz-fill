#!/bin/bash

set -e

# Parse flags (-c is required; must appear before positional args)
COMPILER_PATH=""
while [[ "$1" == -* ]]; do
    case "$1" in
        -c|--compiler-path)
            if [ -z "$2" ] || [[ "$2" == -* ]]; then
                echo "Error: --compiler-path requires a path argument"
                exit 1
            fi
            COMPILER_PATH="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ -z "$COMPILER_PATH" ]; then
    echo "Error: -c|--compiler-path is required (directory containing clang and clang++)"
    echo "Usage: $0 -c|--compiler-path <path> <allowlist_file> <llvm_dir> <build_dir>"
    echo "  -c, --compiler-path:   Path to compiler bin directory (required)"
    echo "  allowlist_file:        Path to the sanitizer coverage allowlist file"
    echo "  llvm_dir:              Path to the LLVM source directory"
    echo "  build_dir:             Path to the build directory (will be created if it doesn't exist)"
    exit 1
fi

# Usage: ./build-llvm-sancov.sh -c|--compiler-path <path> <allowlist_file> <llvm_dir> <build_dir>
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 -c|--compiler-path <path> <allowlist_file> <llvm_dir> <build_dir>"
    echo "  -c, --compiler-path:   Path to compiler bin directory (required)"
    echo "  allowlist_file:        Path to the sanitizer coverage allowlist file"
    echo "  llvm_dir:              Path to the LLVM source directory"
    echo "  build_dir:             Path to the build directory (will be created if it doesn't exist)"
    exit 1
fi

ALLOWLIST="$1"
LLVM_DIR="$2"
BUILD_DIR="$3"

# Validate that allowlist and llvm_dir exist
if [ ! -f "$ALLOWLIST" ]; then
    echo "Error: Allowlist file '$ALLOWLIST' does not exist"
    exit 1
fi

# Convert allowlist to absolute path (needed since we'll cd to build dir)
ALLOWLIST="$(realpath "$ALLOWLIST")"

if [ ! -d "$LLVM_DIR" ]; then
    echo "Error: LLVM directory '$LLVM_DIR' does not exist"
    exit 1
fi

# Convert LLVM_DIR to absolute path
LLVM_DIR="$(realpath "$LLVM_DIR")"

# Create build directory if it doesn't exist
mkdir -p "$BUILD_DIR"

# Convert BUILD_DIR to absolute path
BUILD_DIR="$(realpath "$BUILD_DIR")"

# Change to build directory
cd "$BUILD_DIR"

echo "Building LLVM with coverage allowlist..."
echo "  Allowlist:      $ALLOWLIST"
echo "  LLVM Dir:       $LLVM_DIR"
echo "  Build Dir:      $BUILD_DIR"
echo "  Compiler Path:  $COMPILER_PATH"
echo

cmake -G "Ninja" \
    -DCMAKE_C_COMPILER="$COMPILER_PATH/clang" \
    -DCMAKE_CXX_COMPILER="$COMPILER_PATH/clang++" \
    -DCMAKE_CXX_FLAGS="-O0 -fno-inline -fsanitize-coverage-allowlist=$ALLOWLIST -fsanitize-coverage=bb,trace-pc-guard" \
    -DCMAKE_C_FLAGS="-O0 -fno-inline -fsanitize-coverage-allowlist=$ALLOWLIST -fsanitize-coverage=bb,trace-pc-guard" \
    -DLLVM_TARGETS_TO_BUILD="X86;AMDGPU;SPIRV" \
    -DLLVM_ENABLE_PROJECTS="clang" \
    -DLLVM_OPTIMIZED_TABLEGEN=ON \
    -DLLVM_ENABLE_ASSERTIONS=OFF \
    -DCMAKE_BUILD_TYPE=Debug \
    -DBUILD_SHARED_LIBS=OFF \
    "$LLVM_DIR/llvm"

ninja llc opt 

# These are required to run LIT without problems
ninja FileCheck count not lli llvm-objcopy llvm-strip llvm-install-name-tool llvm-bitcode-strip split-file dsymutil lli-child-target llvm-ar llvm-as llvm-addr2line llvm-bcanalyzer llvm-cas llvm-cgdata llvm-config llvm-cov llvm-ctxprof-util llvm-cxxdump llvm-cvtres llvm-debuginfod-find llvm-debuginfo-analyzer llvm-diff llvm-dis llvm-dwarfdump llvm-dwarfutil llvm-dwp llvm-dlltool llvm-exegesis llvm-extract llvm-ir2vec llvm-isel-fuzzer llvm-ifs llvm-jitlink llvm-opt-fuzzer llvm-lib llvm-link llvm-lto llvm-lto2 llvm-mc llvm-mca llvm-modextract llvm-nm llvm-objdump llvm-otool llvm-pdbutil llvm-profdata llvm-profgen llvm-ranlib llvm-rc llvm-readelf llvm-readobj llvm-rtdyld llvm-sim llvm-size llvm-split llvm-stress llvm-strings llvm-readtapi llvm-undname llvm-windres llvm-c-test llvm-cxxfilt llvm-xray yaml2obj obj2yaml yaml-bench verify-uselistorder llvm-symbolizer sancov sanstats llvm-remarkutil