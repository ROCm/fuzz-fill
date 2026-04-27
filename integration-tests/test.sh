#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: test.sh --venv <venv-dir> --sancov-build <llvm-build-bin-dir> [lit args...]

Required:
  --venv          Path to Python virtualenv directory.
  --sancov-build  Path to LLVM build bin directory (contains llc/opt/clang).

Any additional arguments are forwarded to lit unchanged.
If no extra arguments are provided, lit runs on ".".
EOF
}

venv_dir=""
sancov_build=""
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
        --sancov-build)
            if [[ $# -lt 2 ]]; then
                echo "error: --sancov-build requires a value" >&2
                usage
                exit 2
            fi
            sancov_build="$2"
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

if [[ -z "$sancov_build" ]]; then
    echo "error: --sancov-build is required" >&2
    usage
    exit 2
fi

if [[ ! -d "$venv_dir" ]]; then
    echo "error: venv directory does not exist: $venv_dir" >&2
    exit 2
fi

if [[ ! -d "$sancov_build" ]]; then
    echo "error: sancov build directory does not exist: $sancov_build" >&2
    exit 2
fi

export FUZZ_FILL_VENV_DIR="$venv_dir"
export FUZZ_FILL_SANCOV_LLVM_BIN_DIR="$sancov_build"

if [[ ${#lit_args[@]} -eq 0 ]]; then
    lit_args=(.)
fi

exec lit "${lit_args[@]}"
