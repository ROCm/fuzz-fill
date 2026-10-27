#!/bin/bash

set -euo pipefail

usage() {
    cat <<EOF
Usage: $0 <allowlist> <llvm_dir> <sancov_build_dir> --bootstrap-bin <dir> [ninja_jobs]

  allowlist         Sanitizer coverage allowlist file
  llvm_dir          LLVM source tree (directory containing llvm/)
  sancov_build_dir  Output directory for the SanitizerCoverage-instrumented LLVM build
  --bootstrap-bin   Directory with clang, clang++, and ld.lld
  --ignorelist      Sanitizer coverage ignorelist file (optional)
  --instrumentation-mode func|bb|edge
                    SanitizerCoverage instrumentation granularity (default: bb).
                    fuzz-fill expects basic-block (bb) coverage; func or edge will likely break it.
  --targets <list>  Semicolon-separated LLVM_TARGETS_TO_BUILD (default: X86;AMDGPU;SPIRV)
  --enable-projects <list>
                    Semicolon-separated LLVM_ENABLE_PROJECTS (default: empty).
                    Pass clang to build an instrumented Clang and its lit suite.
  --link-jobs <n>   Maximum concurrent link jobs (default: 8). Compile parallelism
                    stays at ninja_jobs.
  --enable-ccache   Route compilation through ccache (CMAKE_C/CXX_COMPILER_LAUNCHER=ccache).
                    Disabled by default. Fails if ccache is not installed.
  --ccache-compiler-check-version
                    With --enable-ccache, hash via '%compiler% --version' (off by default).
  --allow-inline    Do not pass -fno-inline to the instrumented build (off by default).
  ninja_jobs        Optional parallel jobs for ninja (-j); omit to leave ninja unconstrained

Configures one RelWithDebInfo + SanitizerCoverage tree and builds ninja all.
The sancov tool and the lit helpers FileCheck, not, count, and split-file in
that tree are then replaced by a separate Release build with assertions and
SanitizerCoverage disabled, so those processes do not write .sancov dumps.
Bootstrap supplies clang, clang++, and ld.lld (apt.llvm.org snapshot or another
toolchain bin/); llvm-tblgen is built in-tree.
EOF
}

ALLOWLIST=""
LLVM_DIR=""
SANCOV_BUILD_DIR=""
BOOTSTRAP_BIN=""
IGNORELIST=""
INSTRUMENTATION_MODE="bb"
TARGETS="X86;AMDGPU;SPIRV"
ENABLE_PROJECTS=""
LINK_JOBS="8"
NINJA_JOBS=""
ENABLE_CCACHE=0
CCACHE_COMPILER_CHECK_VERSION=0
ALLOW_INLINE=0

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
        --ignorelist)
            if [[ $# -lt 2 ]]; then
                echo "Error: --ignorelist requires a value" >&2
                usage >&2
                exit 1
            fi
            IGNORELIST="$2"
            shift 2
            ;;
        --instrumentation-mode)
            if [[ $# -lt 2 ]]; then
                echo "Error: --instrumentation-mode requires a value" >&2
                usage >&2
                exit 1
            fi
            INSTRUMENTATION_MODE="$2"
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
        --link-jobs)
            if [[ $# -lt 2 ]]; then
                echo "Error: --link-jobs requires a value" >&2
                usage >&2
                exit 1
            fi
            LINK_JOBS="$2"
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
        --allow-inline)
            ALLOW_INLINE=1
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
            if [[ -z "$ALLOWLIST" ]]; then
                ALLOWLIST="$1"
            elif [[ -z "$LLVM_DIR" ]]; then
                LLVM_DIR="$1"
            elif [[ -z "$SANCOV_BUILD_DIR" ]]; then
                SANCOV_BUILD_DIR="$1"
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

if [[ -z "$ALLOWLIST" || -z "$LLVM_DIR" || -z "$SANCOV_BUILD_DIR" || -z "$BOOTSTRAP_BIN" ]]; then
    usage >&2
    exit 1
fi

INSTRUMENTATION_MODE="${INSTRUMENTATION_MODE:-bb}"

case "$INSTRUMENTATION_MODE" in
    func|bb|edge) ;;
    *)
        echo "Error: --instrumentation-mode must be func, bb, or edge: ${INSTRUMENTATION_MODE}" >&2
        exit 1
        ;;
esac

if [[ ! "$LINK_JOBS" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: --link-jobs must be a positive integer: ${LINK_JOBS}" >&2
    exit 1
fi

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
BOOTSTRAP_BIN="$(realpath "$BOOTSTRAP_BIN")"

if [[ -n "$IGNORELIST" ]]; then
    if [[ ! -f "$IGNORELIST" ]]; then
        echo "Error: ignorelist file not found: $IGNORELIST" >&2
        exit 1
    fi
    IGNORELIST="$(realpath "$IGNORELIST")"
fi

if [[ ! -d "$BOOTSTRAP_BIN" ]]; then
    echo "Error: bootstrap bin directory not found: $BOOTSTRAP_BIN" >&2
    exit 1
fi

C_COMPILER="$BOOTSTRAP_BIN/clang"
CXX_COMPILER="$BOOTSTRAP_BIN/clang++"
LLD="$BOOTSTRAP_BIN/ld.lld"
if [[ ! -x "$C_COMPILER" || ! -x "$CXX_COMPILER" || ! -x "$LLD" ]]; then
    echo "Error: bootstrap bin must provide $C_COMPILER, $CXX_COMPILER, and $LLD" >&2
    exit 1
fi

mkdir -p "$SANCOV_BUILD_DIR"
SANCOV_BUILD_DIR="$(realpath "$SANCOV_BUILD_DIR")"
SANCOV_TOOL_BUILD_DIR="${SANCOV_BUILD_DIR}.sancov-release"

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

SANCOV_FLAGS="-fsanitize-coverage-allowlist=$ALLOWLIST -fsanitize-coverage=${INSTRUMENTATION_MODE},trace-pc-guard"
if [[ "$ALLOW_INLINE" -ne 1 ]]; then
    SANCOV_FLAGS="-fno-inline ${SANCOV_FLAGS}"
fi
if [[ -n "$IGNORELIST" ]]; then
    SANCOV_FLAGS+=" -fsanitize-coverage-ignorelist=$IGNORELIST"
fi

if [[ -z "$TARGETS" ]]; then
    echo "Error: --targets must not be empty" >&2
    exit 1
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

LLVM_CMAKE_ARGS=(
    -G Ninja
    -DCMAKE_C_COMPILER="$C_COMPILER"
    -DCMAKE_CXX_COMPILER="$CXX_COMPILER"
    "${CCACHE_LAUNCHER_ARGS[@]}"
    -DCMAKE_C_FLAGS="$SANCOV_FLAGS"
    -DCMAKE_CXX_FLAGS="$SANCOV_FLAGS"
    -DCMAKE_BUILD_TYPE=RelWithDebInfo
    -DLLVM_TARGETS_TO_BUILD="$TARGETS"
    -DLLVM_PARALLEL_LINK_JOBS="$LINK_JOBS"
    -DLLVM_USE_LINKER=lld
    -DLLVM_ENABLE_PROJECTS="$ENABLE_PROJECTS"
    -DLLVM_ENABLE_ASSERTIONS=ON
    -DLLVM_USE_SPLIT_DWARF=ON
    -DLLVM_INCLUDE_EXAMPLES=OFF
    -DLLVM_INCLUDE_BENCHMARKS=OFF
    -DLLVM_BUILD_TESTS=ON
    -DBUILD_SHARED_LIBS=OFF
    # An instrumented Clang would otherwise link libclang.so, which pulls in
    # instrumented objects and fails on unresolved SanitizerCoverage symbols.
    # PIC off builds libclang static and, in CMake, skips libLTO and plugins.
    -DLLVM_ENABLE_PIC=OFF
)

SANCOV_TOOL_CMAKE_ARGS=(
    -G Ninja
    -DCMAKE_C_COMPILER="$C_COMPILER"
    -DCMAKE_CXX_COMPILER="$CXX_COMPILER"
    "${CCACHE_LAUNCHER_ARGS[@]}"
    -DCMAKE_BUILD_TYPE=Release
    -DLLVM_TARGETS_TO_BUILD="$TARGETS"
    -DLLVM_PARALLEL_LINK_JOBS="$LINK_JOBS"
    -DLLVM_USE_LINKER=lld
    -DLLVM_ENABLE_PROJECTS=""
    -DLLVM_ENABLE_ASSERTIONS=OFF
    -DLLVM_INCLUDE_EXAMPLES=OFF
    -DLLVM_INCLUDE_BENCHMARKS=OFF
    -DLLVM_INCLUDE_TESTS=OFF
    -DLLVM_BUILD_TESTS=OFF
    -DLLVM_TOOL_LTO_BUILD=OFF
    -DBUILD_SHARED_LIBS=OFF
)

ninja_args=()
if [[ -n "$NINJA_JOBS" ]]; then
    ninja_args=(-j "$NINJA_JOBS")
fi

echo "Building LLVM for fuzz-fill (instrumented tree, ninja all)..."
echo "  Allowlist:        $ALLOWLIST"
echo "  Instrumentation:  $INSTRUMENTATION_MODE (trace-pc-guard)"
if [[ -n "$IGNORELIST" ]]; then
    echo "  Ignorelist:       $IGNORELIST"
fi
echo "  Targets:          $TARGETS"
echo "  Enable projects:  ${ENABLE_PROJECTS:-<none>}"
echo "  LLVM source:      $LLVM_DIR"
echo "  Sancov build:     $SANCOV_BUILD_DIR"
echo "  Bootstrap bin:    $BOOTSTRAP_BIN (clang/clang++ and ld.lld)"
echo "  C compiler:       $C_COMPILER"
echo "  C++ compiler:     $CXX_COMPILER"
if [[ -n "$NINJA_JOBS" ]]; then
    echo "  Ninja jobs:       $NINJA_JOBS"
fi
echo "  Link jobs:        $LINK_JOBS"
echo "  Linker:           lld ($LLD)"
echo "  Release sancov:   $SANCOV_TOOL_BUILD_DIR"
echo "  ccache:           $([[ "$ENABLE_CCACHE" -eq 1 ]] && echo enabled || echo disabled)"
echo "  -fno-inline:      $([[ "$ALLOW_INLINE" -eq 1 ]] && echo omitted || echo enabled)"
echo

echo "=== Instrumented tree (RelWithDebInfo + SanitizerCoverage, ninja all) ==="
(
    # The allowlist/ignorelist are passed to clang as plain file paths, not #include'd
    # and not recorded in -MD dependency output, so ccache only hashes the path string
    # unless we list them in extra_files_to_hash (CCACHE_EXTRAFILES). See ccache(1).
    # Scope EXTRAFILES to this subshell so allowlist edits do not invalidate the
    # Release sancov/helper tree, which does not use those files.
    if [[ "$ENABLE_CCACHE" -eq 1 ]]; then
        _ccache_extra_files="${ALLOWLIST}"
        if [[ -n "$IGNORELIST" ]]; then
            _ccache_extra_files+=":${IGNORELIST}"
        fi
        if [[ -n "${CCACHE_EXTRAFILES:-}" ]]; then
            export CCACHE_EXTRAFILES="${CCACHE_EXTRAFILES}:${_ccache_extra_files}"
        else
            export CCACHE_EXTRAFILES="${_ccache_extra_files}"
        fi
    fi
    cd "$SANCOV_BUILD_DIR"
    cmake "${LLVM_CMAKE_ARGS[@]}" \
        "$LLVM_DIR/llvm"
    ninja "${ninja_args[@]}"
)

echo "=== Release sancov tool and lit helpers (no SanitizerCoverage) ==="
mkdir -p "$SANCOV_TOOL_BUILD_DIR"
# Lit helpers are invoked once per test. Built here so they do not link the
# coverage runtime and do not write a .sancov file on exit.
RELEASE_TOOLS=(sancov FileCheck not count split-file)
(
    cd "$SANCOV_TOOL_BUILD_DIR"
    cmake "${SANCOV_TOOL_CMAKE_ARGS[@]}" \
        "$LLVM_DIR/llvm"
    ninja "${ninja_args[@]}" "${RELEASE_TOOLS[@]}"
)
for tool in "${RELEASE_TOOLS[@]}"; do
    if [[ ! -x "$SANCOV_TOOL_BUILD_DIR/bin/$tool" ]]; then
        echo "Error: release $tool not found at $SANCOV_TOOL_BUILD_DIR/bin/$tool" >&2
        exit 1
    fi
    cp -f "$SANCOV_TOOL_BUILD_DIR/bin/$tool" "$SANCOV_BUILD_DIR/bin/$tool"
done

if [[ ! -f "$SANCOV_BUILD_DIR/test/lit.site.cfg.py" ]]; then
    echo "Error: test/lit.site.cfg.py not found under $SANCOV_BUILD_DIR" >&2
    exit 1
fi

if [[ "$enable_clang" -eq 1 ]]; then
    if [[ ! -f "$SANCOV_BUILD_DIR/tools/clang/test/lit.site.cfg.py" ]]; then
        echo "Error: tools/clang/test/lit.site.cfg.py not found under $SANCOV_BUILD_DIR" >&2
        exit 1
    fi
fi

if [[ "$ENABLE_CCACHE" -eq 1 ]]; then
    echo
    echo "=== ccache stats ==="
    ccache --show-stats
fi

echo "Done. Instrumented build at $SANCOV_BUILD_DIR"
