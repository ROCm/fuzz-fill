#!/bin/bash

set -e

if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <c-compiler> <cxx-compiler> <llvm_dir> <build_dir>"
    exit 1
fi

C_COMPILER="$1"
CXX_COMPILER="$2"
LLVM_DIR="$(realpath "$3")"
BUILD_DIR="$(realpath -m "$4")"

mkdir -p "$BUILD_DIR"
BUILD_DIR="$(realpath "$BUILD_DIR")"
cd "$BUILD_DIR"

cmake -G "Ninja" \
    -DCMAKE_C_COMPILER="$C_COMPILER" \
    -DCMAKE_CXX_COMPILER="$CXX_COMPILER" \
    -DLLVM_TARGETS_TO_BUILD="X86" \
    -DLLVM_ENABLE_PROJECTS="clang" \
    -DLLVM_ENABLE_RUNTIMES="compiler-rt" \
    -DLLVM_OPTIMIZED_TABLEGEN=ON \
    -DLLVM_ENABLE_ASSERTIONS=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=OFF \
    "$LLVM_DIR/llvm"

ninja
