#!/bin/bash

set -e

if [ "$#" -lt 4 ] || [ "$#" -gt 5 ]; then
    echo "Usage: $0 <c-compiler> <cxx-compiler> <llvm_dir> <build_dir> [ninja_jobs]"
    exit 1
fi

C_COMPILER="$1"
CXX_COMPILER="$2"
LLVM_DIR="$(realpath "$3")"
BUILD_DIR="$(realpath -m "$4")"
NINJA_JOBS="${5:-}"

mkdir -p "$BUILD_DIR"
BUILD_DIR="$(realpath "$BUILD_DIR")"
cd "$BUILD_DIR"

# compiler-rt minimal build for -fsanitize-coverage=bb,trace-pc-guard (with
# allowlist). Clang links libclang_rt.ubsan_standalone for any coverage build;
# that archive pulls in sanitizer_common (coverage + symbolizer) and
# interception. COMPILER_RT_BUILD_SANITIZERS must stay ON, but an empty
# SANITIZERS_TO_BUILD skips asan/tsan/hwasan/… while still building the ubsan
# object libs above. stats/lsan subdirs also build (CMake always adds them when
# BUILD_SANITIZERS is on) but are not linked for coverage-only use.
cmake -G "Ninja" \
    -DCMAKE_C_COMPILER="$C_COMPILER" \
    -DCMAKE_CXX_COMPILER="$CXX_COMPILER" \
    -DLLVM_TARGETS_TO_BUILD="X86" \
    -DLLVM_ENABLE_PROJECTS="clang" \
    -DLLVM_ENABLE_RUNTIMES="compiler-rt" \
    -DCOMPILER_RT_SANITIZERS_TO_BUILD="" \
    -DCOMPILER_RT_INCLUDE_TESTS=OFF \
    -DCOMPILER_RT_BUILD_BUILTINS=OFF \
    -DCOMPILER_RT_BUILD_LIBFUZZER=OFF \
    -DCOMPILER_RT_BUILD_MEMPROF=OFF \
    -DCOMPILER_RT_BUILD_ORC=OFF \
    -DCOMPILER_RT_BUILD_XRAY=OFF \
    -DCOMPILER_RT_BUILD_PROFILE=OFF \
    -DCOMPILER_RT_BUILD_PROFILE_ROCM=OFF \
    -DCOMPILER_RT_BUILD_CTX_PROFILE=OFF \
    -DCOMPILER_RT_BUILD_GWP_ASAN=OFF \
    -DLLVM_OPTIMIZED_TABLEGEN=ON \
    -DLLVM_ENABLE_ASSERTIONS=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=OFF \
    "$LLVM_DIR/llvm"

ninja_args=()
if [ -n "$NINJA_JOBS" ]; then
    ninja_args=(-j "$NINJA_JOBS")
fi
ninja "${ninja_args[@]}"
