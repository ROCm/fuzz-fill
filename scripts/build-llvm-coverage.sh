#!/bin/bash

set -euo pipefail

usage() {
    cat <<EOF
Usage: $0 <llvm_dir> <build_dir> --bootstrap-bin <dir> [ninja_jobs]

  llvm_dir          LLVM source tree (directory containing llvm/)
  build_dir         Output directory for the source-coverage-instrumented LLVM build
  --bootstrap-bin   Directory with clang and clang++. When --linker is lld (the
                    default), the same directory must also provide ld.lld.
  --build-type <type>
                    CMAKE_BUILD_TYPE (default: Release — no debug info; source
                    coverage does not need -g). One of: Debug, Release,
                    RelWithDebInfo, MinSizeRel.
  --targets <list>  Semicolon-separated LLVM_TARGETS_TO_BUILD (default: all).
  --enable-projects <list>
                    Semicolon-separated LLVM_ENABLE_PROJECTS (default: clang;mlir).
                    Pass an empty string to build LLVM only. When clang is enabled,
                    CLANG_ENABLE_CIR is ON by default (ClangIR; requires mlir in the
                    project list). Use --disable-clangir to turn it off.
  --disable-clangir Disable ClangIR (CLANG_ENABLE_CIR=OFF) even when clang is built.
  --linker <name>   LLVM_USE_LINKER (default: lld).
  --link-jobs <n>   Maximum concurrent link jobs (default: 8). Compile parallelism
                    stays at ninja_jobs.
  --assertions on|off
                    LLVM_ENABLE_ASSERTIONS (default: on).
  --enable-ccache   Route compilation through ccache (CMAKE_C/CXX_COMPILER_LAUNCHER=ccache).
                    Disabled by default. Fails if ccache is not installed.
  --ccache-compiler-check-version
                    With --enable-ccache, hash via '%compiler% --version' (off by default).
  ninja_jobs        Optional parallel jobs for ninja (-j); omit to leave ninja unconstrained

Configures one tree with LLVM_BUILD_INSTRUMENTED_COVERAGE=ON and builds ninja all.
Links tools statically against LLVM (LLVM_BUILD_LLVM_DYLIB/LINK_LLVM_DYLIB=OFF,
BUILD_SHARED_LIBS=OFF) so staged artifacts are self-contained binaries.
Coverage instrumentation applies to the whole build (no allowlist). Instrumented
processes write raw profiles under <build_dir>/profiles/ by default. Bootstrap
supplies clang/clang++ (and ld.lld when using lld); llvm-tblgen is built in-tree.
EOF
}

LLVM_DIR=""
BUILD_DIR=""
BOOTSTRAP_BIN=""
BUILD_TYPE="Release"
TARGETS="all"
ENABLE_PROJECTS="clang;mlir"
LINKER="lld"
LINK_JOBS="8"
ASSERTIONS="on"
NINJA_JOBS=""
ENABLE_CCACHE=0
CCACHE_COMPILER_CHECK_VERSION=0
DISABLE_CLANGIR=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bootstrap-bin)
            if [[ $# -lt 2 ]]; then
                echo "Error: --bootstrap-bin requires a value" >&2
                usage >&2
                exit 1
            fi
            BOOTSTRAP_BIN="$2"
            shift 2
            ;;
        --build-type)
            if [[ $# -lt 2 ]]; then
                echo "Error: --build-type requires a value" >&2
                usage >&2
                exit 1
            fi
            BUILD_TYPE="$2"
            shift 2
            ;;
        --targets)
            if [[ $# -lt 2 ]]; then
                echo "Error: --targets requires a value" >&2
                usage >&2
                exit 1
            fi
            TARGETS="$2"
            shift 2
            ;;
        --enable-projects)
            if [[ $# -lt 2 ]]; then
                echo "Error: --enable-projects requires a value" >&2
                usage >&2
                exit 1
            fi
            ENABLE_PROJECTS="$2"
            shift 2
            ;;
        --linker)
            if [[ $# -lt 2 ]]; then
                echo "Error: --linker requires a value" >&2
                usage >&2
                exit 1
            fi
            LINKER="$2"
            shift 2
            ;;
        --link-jobs)
            if [[ $# -lt 2 ]]; then
                echo "Error: --link-jobs requires a value" >&2
                usage >&2
                exit 1
            fi
            LINK_JOBS="$2"
            shift 2
            ;;
        --assertions)
            if [[ $# -lt 2 ]]; then
                echo "Error: --assertions requires a value" >&2
                usage >&2
                exit 1
            fi
            ASSERTIONS="$2"
            shift 2
            ;;
        --enable-ccache)
            ENABLE_CCACHE=1
            shift
            ;;
        --ccache-compiler-check-version)
            CCACHE_COMPILER_CHECK_VERSION=1
            shift
            ;;
        --disable-clangir)
            DISABLE_CLANGIR=1
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        -*)
            echo "Error: unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
        *)
            if [[ -z "$LLVM_DIR" ]]; then
                LLVM_DIR="$1"
            elif [[ -z "$BUILD_DIR" ]]; then
                BUILD_DIR="$1"
            elif [[ -z "$NINJA_JOBS" ]]; then
                NINJA_JOBS="$1"
            else
                echo "Error: unexpected argument: $1" >&2
                usage >&2
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$LLVM_DIR" || -z "$BUILD_DIR" || -z "$BOOTSTRAP_BIN" ]]; then
    usage >&2
    exit 1
fi

case "$BUILD_TYPE" in
    Debug|Release|RelWithDebInfo|MinSizeRel) ;;
    *)
        echo "Error: --build-type must be Debug, Release, RelWithDebInfo, or MinSizeRel: ${BUILD_TYPE}" >&2
        exit 1
        ;;
esac

if [[ -z "$TARGETS" ]]; then
    echo "Error: --targets must not be empty" >&2
    exit 1
fi

if [[ -z "$LINKER" ]]; then
    echo "Error: --linker must not be empty" >&2
    exit 1
fi

if [[ ! "$LINK_JOBS" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: --link-jobs must be a positive integer: ${LINK_JOBS}" >&2
    exit 1
fi

case "$ASSERTIONS" in
    on|off) ;;
    *)
        echo "Error: --assertions must be on or off: ${ASSERTIONS}" >&2
        exit 1
        ;;
esac

if [[ ! -d "$LLVM_DIR/llvm" ]]; then
    echo "Error: LLVM source not found at $LLVM_DIR/llvm" >&2
    exit 1
fi

LLVM_DIR="$(realpath "$LLVM_DIR")"
BOOTSTRAP_BIN="$(realpath "$BOOTSTRAP_BIN")"

if [[ ! -d "$BOOTSTRAP_BIN" ]]; then
    echo "Error: bootstrap bin directory not found: $BOOTSTRAP_BIN" >&2
    exit 1
fi

C_COMPILER="$BOOTSTRAP_BIN/clang"
CXX_COMPILER="$BOOTSTRAP_BIN/clang++"
if [[ ! -x "$C_COMPILER" || ! -x "$CXX_COMPILER" ]]; then
    echo "Error: bootstrap bin must provide $C_COMPILER and $CXX_COMPILER" >&2
    exit 1
fi

LLD=""
if [[ "$LINKER" == "lld" ]]; then
    LLD="$BOOTSTRAP_BIN/ld.lld"
    if [[ ! -x "$LLD" ]]; then
        echo "Error: --linker lld requires $LLD in the bootstrap bin directory" >&2
        exit 1
    fi
fi

mkdir -p "$BUILD_DIR"
BUILD_DIR="$(realpath "$BUILD_DIR")"

CCACHE_LAUNCHER_ARGS=()
if [[ "$CCACHE_COMPILER_CHECK_VERSION" -eq 1 && "$ENABLE_CCACHE" -ne 1 ]]; then
    echo "Error: --ccache-compiler-check-version requires --enable-ccache" >&2
    exit 1
fi

if [[ "$ENABLE_CCACHE" -eq 1 ]]; then
    if ! command -v ccache >/dev/null 2>&1; then
        echo "Error: --enable-ccache was passed but ccache is not installed" >&2
        exit 1
    fi
    # LLVM builds with precompiled headers by default (LLVM_ENABLE_PCH). Without this
    # sloppiness, ccache cannot cache PCH-dependent compiles at all (nearly the entire
    # build), since it can't verify __DATE__/__TIME__ or #define usage across the PCH.
    # See ccache(1) PRECOMPILED HEADERS. Respect a caller-provided value if already set.
    export CCACHE_SLOPPINESS="${CCACHE_SLOPPINESS:-pch_defines,time_macros}"

    if [[ "$CCACHE_COMPILER_CHECK_VERSION" -eq 1 ]]; then
        # Prefer --version over mtime for apt.llvm.org nightlies. Keep a caller override.
        export CCACHE_COMPILERCHECK="${CCACHE_COMPILERCHECK:-%compiler% --version}"
    fi

    CCACHE_LAUNCHER_ARGS=(
        -DCMAKE_C_COMPILER_LAUNCHER=ccache
        -DCMAKE_CXX_COMPILER_LAUNCHER=ccache
    )
fi

# Split projects on ';' and detect clang.
enable_clang=0
IFS=';' read -r -a _projects <<< "$ENABLE_PROJECTS"
for _project in "${_projects[@]}"; do
    if [[ "$_project" == "clang" ]]; then
        enable_clang=1
        break
    fi
done

if [[ "$ASSERTIONS" == "on" ]]; then
    ASSERTIONS_CMAKE=ON
else
    ASSERTIONS_CMAKE=OFF
fi

LLVM_CMAKE_ARGS=(
    -G Ninja
    -DCMAKE_C_COMPILER="$C_COMPILER"
    -DCMAKE_CXX_COMPILER="$CXX_COMPILER"
    "${CCACHE_LAUNCHER_ARGS[@]}"
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE"
    -DLLVM_TARGETS_TO_BUILD="$TARGETS"
    -DLLVM_BUILD_INSTRUMENTED_COVERAGE=ON
    -DLLVM_PARALLEL_LINK_JOBS="$LINK_JOBS"
    -DLLVM_USE_LINKER="$LINKER"
    -DLLVM_ENABLE_PROJECTS="$ENABLE_PROJECTS"
    -DLLVM_ENABLE_ASSERTIONS="$ASSERTIONS_CMAKE"
    -DLLVM_INCLUDE_EXAMPLES=OFF
    -DLLVM_INCLUDE_BENCHMARKS=OFF
    -DLLVM_BUILD_TESTS=ON
    -DBUILD_SHARED_LIBS=OFF
    # Static tool binaries (easier to stage/upload than a dylib + closure).
    -DLLVM_BUILD_LLVM_DYLIB=OFF
    -DLLVM_LINK_LLVM_DYLIB=OFF
)

enable_clangir=0
if [[ "$enable_clang" -eq 1 && "$DISABLE_CLANGIR" -eq 0 ]]; then
    enable_clangir=1
    LLVM_CMAKE_ARGS+=(-DCLANG_ENABLE_CIR=ON)
elif [[ "$enable_clang" -eq 1 ]]; then
    LLVM_CMAKE_ARGS+=(-DCLANG_ENABLE_CIR=OFF)
fi

ninja_args=()
if [[ -n "$NINJA_JOBS" ]]; then
    ninja_args=(-j "$NINJA_JOBS")
fi

echo "Building LLVM for fuzz-fill (source-coverage tree, ninja all)..."
echo "  LLVM source:      $LLVM_DIR"
echo "  Build dir:        $BUILD_DIR"
echo "  Bootstrap bin:    $BOOTSTRAP_BIN"
echo "  C compiler:       $C_COMPILER"
echo "  C++ compiler:     $CXX_COMPILER"
echo "  Build type:       $BUILD_TYPE"
echo "  Targets:          $TARGETS"
echo "  Enable projects:  ${ENABLE_PROJECTS:-<none>}"
if [[ "$enable_clang" -eq 0 ]]; then
    echo "  ClangIR:          skipped (clang not enabled)"
elif [[ "$enable_clangir" -eq 1 ]]; then
    echo "  ClangIR:          ON"
else
    echo "  ClangIR:          OFF (--disable-clangir)"
fi
echo "  Linker:           $LINKER$([[ -n "$LLD" ]] && echo " ($LLD)")"
echo "  Assertions:       $ASSERTIONS"
if [[ -n "$NINJA_JOBS" ]]; then
    echo "  Ninja jobs:       $NINJA_JOBS"
fi
echo "  Link jobs:        $LINK_JOBS"
echo "  ccache:           $([[ "$ENABLE_CCACHE" -eq 1 ]] && echo enabled || echo disabled)"
echo "  Coverage:         LLVM_BUILD_INSTRUMENTED_COVERAGE=ON (whole tree)"
echo "  Linking:          static (LLVM_BUILD_LLVM_DYLIB=OFF, LLVM_LINK_LLVM_DYLIB=OFF)"
echo

echo "=== Instrumented tree ($BUILD_TYPE + source coverage, ninja all) ==="
(
    cd "$BUILD_DIR"
    cmake "${LLVM_CMAKE_ARGS[@]}" \
        "$LLVM_DIR/llvm"
    ninja "${ninja_args[@]}"
)

if [[ ! -f "$BUILD_DIR/test/lit.site.cfg.py" ]]; then
    echo "Error: test/lit.site.cfg.py not found under $BUILD_DIR" >&2
    exit 1
fi

if [[ "$enable_clang" -eq 1 ]]; then
    if [[ ! -f "$BUILD_DIR/tools/clang/test/lit.site.cfg.py" ]]; then
        echo "Error: tools/clang/test/lit.site.cfg.py not found under $BUILD_DIR" >&2
        exit 1
    fi
fi

if [[ "$ENABLE_CCACHE" -eq 1 ]]; then
    echo
    echo "=== ccache stats ==="
    ccache --show-stats
fi

echo "Done. Source-coverage build at $BUILD_DIR"
