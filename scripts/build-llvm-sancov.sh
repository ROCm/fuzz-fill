#!/bin/bash

set -euo pipefail

usage() {
    cat <<EOF
Usage: $0 <allowlist> <llvm_dir> <sancov_build_dir> --bootstrap-bin <dir> [ninja_jobs]

  allowlist         Sanitizer coverage allowlist file
  llvm_dir          LLVM source tree (directory containing llvm/)
  sancov_build_dir  Output directory for the SanitizerCoverage-instrumented LLVM build
  --bootstrap-bin   Directory with clang and clang++ (e.g. official LLVM release bin/)
  --ignorelist      Sanitizer coverage ignorelist file (optional)
  --instrumentation-mode func|bb|edge
                    SanitizerCoverage instrumentation granularity (default: bb).
                    fuzz-fill expects basic-block (bb) coverage; func or edge will likely break it.
  ninja_jobs        Optional parallel jobs for ninja (-j); omit to leave ninja unconstrained

Builds llvm-tblgen from the source tree, then instrumented llc/opt (Debug + SanitizerCoverage)
and Release LIT helpers. Target-linked helpers are built in the instrumented tree; other helpers
(and sancov) are Release-built in \${sancov_build_dir}-helpers and copied into bin/.
EOF
}

ALLOWLIST=""
LLVM_DIR=""
SANCOV_BUILD_DIR=""
BOOTSTRAP_BIN=""
IGNORELIST=""
INSTRUMENTATION_MODE="bb"
NINJA_JOBS=""

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
if [[ ! -x "$C_COMPILER" || ! -x "$CXX_COMPILER" ]]; then
    echo "Error: bootstrap bin must provide $C_COMPILER and $CXX_COMPILER" >&2
    exit 1
fi

# Instrumented targets (Debug + SanitizerCoverage): coverage tools plus helpers that link
# target disassemblers, asm parsers, or CodeGen (built in the same tree as llc/opt).
SANCOV_INSTRUMENTED_TARGETS=(
    llc
    opt
    llvm-debuginfo-analyzer
    llvm-dwarfdump
    llvm-lto
    llvm-lto2
    llvm-mc
    llvm-objdump
)

# Release helpers with no target backend linkage, plus sancov (disassemblers only in Release).
HELPER_RELEASE_TARGETS=(
    FileCheck
    count
    not
    sancov
    split-file
    llvm-as
    llvm-config
    llvm-dis
    llvm-objcopy
    llvm-readelf
    llvm-readobj
    llvm-reduce
    llvm-strip
    yaml2obj
)

mkdir -p "$SANCOV_BUILD_DIR"
SANCOV_BUILD_DIR="$(realpath "$SANCOV_BUILD_DIR")"
HELPERS_BUILD_DIR="${SANCOV_BUILD_DIR}-helpers"
SANCOV_BIN="$SANCOV_BUILD_DIR/bin"
HELPERS_BIN="$HELPERS_BUILD_DIR/bin"

SANCOV_FLAGS="-fno-inline -fsanitize-coverage-allowlist=$ALLOWLIST -fsanitize-coverage=${INSTRUMENTATION_MODE},trace-pc-guard"
if [[ -n "$IGNORELIST" ]]; then
    SANCOV_FLAGS+=" -fsanitize-coverage-ignorelist=$IGNORELIST"
fi

LLVM_CMAKE_BASE=(
    -G Ninja
    -DCMAKE_C_COMPILER="$C_COMPILER"
    -DCMAKE_CXX_COMPILER="$CXX_COMPILER"
    -DLLVM_TARGETS_TO_BUILD="X86;AMDGPU;SPIRV"
    -DLLVM_ENABLE_PROJECTS=""
    -DLLVM_ENABLE_ASSERTIONS=ON
    -DLLVM_USE_SPLIT_DWARF=ON
    -DLLVM_INCLUDE_EXAMPLES=OFF
    -DLLVM_INCLUDE_BENCHMARKS=OFF
    -DLLVM_TOOL_LTO_BUILD=OFF
    -DBUILD_SHARED_LIBS=OFF
)

ninja_args=()
if [[ -n "$NINJA_JOBS" ]]; then
    ninja_args=(-j "$NINJA_JOBS")
fi

echo "Building LLVM for fuzz-fill (Release helpers + instrumented tree)..."
echo "  Allowlist:        $ALLOWLIST"
echo "  Instrumentation:  $INSTRUMENTATION_MODE (trace-pc-guard)"
if [[ -n "$IGNORELIST" ]]; then
    echo "  Ignorelist:       $IGNORELIST"
fi
echo "  LLVM source:      $LLVM_DIR"
echo "  Sancov build:     $SANCOV_BUILD_DIR"
echo "  Helpers build:    $HELPERS_BUILD_DIR"
echo "  Bootstrap bin:    $BOOTSTRAP_BIN (clang/clang++ only)"
echo "  C compiler:       $C_COMPILER"
echo "  C++ compiler:     $CXX_COMPILER"
if [[ -n "$NINJA_JOBS" ]]; then
    echo "  Ninja jobs:       $NINJA_JOBS"
fi
echo

echo "=== llvm-tblgen (Release, from source) ==="
mkdir -p "$HELPERS_BUILD_DIR"
(
    cd "$HELPERS_BUILD_DIR"
    cmake "${LLVM_CMAKE_BASE[@]}" \
        -DCMAKE_BUILD_TYPE=Release \
        "$LLVM_DIR/llvm"
    ninja "${ninja_args[@]}" llvm-tblgen
)

if [[ ! -x "$HELPERS_BIN/llvm-tblgen" ]]; then
    echo "Error: llvm-tblgen not found at $HELPERS_BIN/llvm-tblgen after build" >&2
    exit 1
fi

LLVM_CMAKE_CONFIGURED=(
    "${LLVM_CMAKE_BASE[@]}"
    -DLLVM_OPTIMIZED_TABLEGEN=ON
    -DLLVM_NATIVE_TOOL_DIR="$HELPERS_BIN"
)

echo
echo "=== Release helpers (${#HELPER_RELEASE_TARGETS[@]} targets) ==="
(
    cd "$HELPERS_BUILD_DIR"
    cmake "${LLVM_CMAKE_CONFIGURED[@]}" \
        -DCMAKE_BUILD_TYPE=Release \
        "$LLVM_DIR/llvm"
    ninja "${ninja_args[@]}" "${HELPER_RELEASE_TARGETS[@]}"
)

echo
echo "=== Instrumented tree (RelWithDebInfo + SanitizerCoverage, ${#SANCOV_INSTRUMENTED_TARGETS[@]} targets) ==="
(
    cd "$SANCOV_BUILD_DIR"
    cmake "${LLVM_CMAKE_CONFIGURED[@]}" \
        -DCMAKE_C_FLAGS="$SANCOV_FLAGS" \
        -DCMAKE_CXX_FLAGS="$SANCOV_FLAGS" \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        "$LLVM_DIR/llvm"
    ninja "${ninja_args[@]}" "${SANCOV_INSTRUMENTED_TARGETS[@]}"
)

if [[ ! -f "$SANCOV_BUILD_DIR/test/lit.site.cfg.py" ]]; then
    echo "Error: test/lit.site.cfg.py not found under $SANCOV_BUILD_DIR" >&2
    exit 1
fi

echo
echo "=== Installing Release helpers into $SANCOV_BIN ==="
mkdir -p "$SANCOV_BIN"
for tool in "${HELPER_RELEASE_TARGETS[@]}"; do
    src="$HELPERS_BIN/$tool"
    if [[ ! -e "$src" ]]; then
        echo "Error: helper tool not found after Release build: $src" >&2
        exit 1
    fi
    cp -L "$src" "$SANCOV_BIN/$tool"
done

echo "Done. Unified build at $SANCOV_BUILD_DIR (instrumented llc/opt + target helpers; Release helpers installed)"
