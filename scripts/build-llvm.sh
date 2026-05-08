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
    echo "Usage: $0 -c|--compiler-path <path> <llvm_dir> <build_dir>"
    echo "  -c, --compiler-path:   Path to compiler bin directory (required)"
    echo "  llvm_dir:              Path to the LLVM source directory"
    echo "  build_dir:             Path to the build directory (will be created if it doesn't exist)"
    exit 1
fi

# Usage: ./build-llvm.sh -c|--compiler-path <path> <llvm_dir> <build_dir>
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 -c|--compiler-path <path> <llvm_dir> <build_dir>"
    echo "  -c, --compiler-path:   Path to compiler bin directory (required)"
    echo "  llvm_dir:              Path to the LLVM source directory"
    echo "  build_dir:             Path to the build directory (will be created if it doesn't exist)"
    exit 1
fi

LLVM_DIR="$1"
BUILD_DIR="$2"

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

echo "Building LLVM..."

cmake -G "Ninja" \
    -DCMAKE_C_COMPILER="$COMPILER_PATH/clang" \
    -DCMAKE_CXX_COMPILER="$COMPILER_PATH/clang++" \
    -DLLVM_TARGETS_TO_BUILD="X86;AMDGPU;SPIRV" \
    -DLLVM_ENABLE_PROJECTS="clang" \
    -DLLVM_OPTIMIZED_TABLEGEN=ON \
    -DLLVM_ENABLE_ASSERTIONS=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=OFF \
    "$LLVM_DIR/llvm"

# These are required to run LIT without problems
ninja FileCheck not sancov
