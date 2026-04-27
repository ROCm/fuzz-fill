#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: test.sh --venv <venv-dir> --llvm-build <bin-dir> --llvm-sancov-build <bin-dir> [lit args...]

Required:
  --venv               Path to Python virtualenv directory.
  --llvm-build         Path to uninstrumented LLVM build bin (FileCheck, sancov).
  --llvm-sancov-build  Path to SanitizerCoverage-instrumented LLVM build bin (llc, opt).

Any additional arguments are forwarded to lit unchanged.
If no extra arguments are provided, lit runs on ".".
EOF
}

venv_dir=""
llvm_build=""
llvm_sancov_build=""
lit_args=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv)
            if [[ $# -lt 2 ]]; then
                echo "error: --venv requires a value" >&2
                usage
                exit 2
            fi
            venv_dir="$2"
            shift 2
            ;;
        --llvm-build)
            if [[ $# -lt 2 ]]; then
                echo "error: --llvm-build requires a value" >&2
                usage
                exit 2
            fi
            llvm_build="$2"
            shift 2
            ;;
        --llvm-sancov-build)
            if [[ $# -lt 2 ]]; then
                echo "error: --llvm-sancov-build requires a value" >&2
                usage
                exit 2
            fi
            llvm_sancov_build="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            lit_args+=("$1")
            shift
            ;;
    esac
done

if [[ -z "$venv_dir" ]]; then
    echo "error: --venv is required" >&2
    usage
    exit 2
fi

if [[ -z "$llvm_build" ]]; then
    echo "error: --llvm-build is required" >&2
    usage
    exit 2
fi

if [[ -z "$llvm_sancov_build" ]]; then
    echo "error: --llvm-sancov-build is required" >&2
    usage
    exit 2
fi

if [[ ! -d "$venv_dir" ]]; then
    echo "error: venv directory does not exist: $venv_dir" >&2
    exit 2
fi

if [[ ! -d "$llvm_build" ]]; then
    echo "error: LLVM bin directory does not exist: $llvm_build" >&2
    exit 2
fi

if [[ ! -d "$llvm_sancov_build" ]]; then
    echo "error: LLVM SanitizerCoverage bin directory does not exist: $llvm_sancov_build" >&2
    exit 2
fi

export FUZZ_FILL_VENV_DIR="$venv_dir"
export FUZZ_FILL_LLVM_BIN_DIR="$llvm_build"
export FUZZ_FILL_LLVM_SANCOV_BIN_DIR="$llvm_sancov_build"

if [[ ${#lit_args[@]} -eq 0 ]]; then
    lit_args=(.)
fi

exec lit "${lit_args[@]}"
