#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: test.sh --venv <venv-dir> --llvm-build <bin-dir> --llvm-sancov-build <bin-dir> --llvm-src <src-dir> [lit args...]

Required:
  --venv               Path to Python virtualenv directory.
  --llvm-build         Path to uninstrumented LLVM build bin (FileCheck, sancov).
  --llvm-sancov-build  Path to SanitizerCoverage-instrumented LLVM build bin (llc, opt).
  --llvm-src           Path to llvm-project checkout root (directory containing llvm/).

Any additional arguments are forwarded to lit unchanged.
If no extra arguments are provided, lit runs on ".".
EOF
}

venv_dir=""
llvm_build=""
llvm_sancov_build=""
llvm_src=""
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
        --llvm-src)
            if [[ $# -lt 2 ]]; then
                echo "error: --llvm-src requires a value" >&2
                usage
                exit 2
            fi
            llvm_src="$2"
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

if [[ -z "$llvm_src" ]]; then
    echo "error: --llvm-src is required" >&2
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

if [[ ! -d "$llvm_src/llvm" ]]; then
    echo "error: llvm-project checkout not found at: $llvm_src/llvm" >&2
    exit 2
fi

export FUZZ_FILL_VENV_DIR="$venv_dir"
export FUZZ_FILL_LLVM_BIN_DIR="$llvm_build"
export FUZZ_FILL_LLVM_SANCOV_BIN_DIR="$llvm_sancov_build"
export FUZZ_FILL_LLVM_SRC_DIR="$llvm_src"

unset FUZZ_FILL_SANCOV FUZZ_FILL_LLVM_LIT FUZZ_FILL_LLC FUZZ_FILL_OPT \
      FUZZ_FILL_LLVM_REDUCE FUZZ_FILL_LLVM_DIS

if [[ ${#lit_args[@]} -eq 0 ]]; then
    lit_args=(.)
fi

# Patch once before lit schedules tests; parallel baseline RUN lines otherwise
# race while appending to the shared LLVM build's lit.site.cfg.py.
"$venv_dir/bin/python" - "$llvm_sancov_build/llvm-lit" <<'PY'
import sys
from pathlib import Path

from coverage.lit_config import ensure_lit_sancov_env_forwarding

ensure_lit_sancov_env_forwarding(Path(sys.argv[1]))
PY

exec lit "${lit_args[@]}"
