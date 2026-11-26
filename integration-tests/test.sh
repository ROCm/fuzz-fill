#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: test.sh --venv <venv-dir> --llvm-build <bin-dir> --llvm-src <src-dir> [--llvm-coverage-build <build-dir>] [--llvm-sancov-build <bin-dir>] [--host-bin <bin-dir>] [lit args...]

Required:
  --venv               Path to Python virtualenv directory.
  --llvm-build         Path to LLVM build bin (FileCheck, sancov for the main suite).
  --llvm-src           Path to llvm-project checkout root (directory containing llvm/).

Optional:
  --llvm-coverage-build
                       Path to source-coverage LLVM build dir for coverage baseline
                       (or its bin dir; defaults to FUZZ_FILL_LLVM_COVERAGE_BIN_DIR
                       / FUZZ_FILL_LLVM_COVERAGE_BUILD_DIR when set).
  --llvm-sancov-build  Path to SanitizerCoverage-instrumented LLVM build bin (llc, opt).
                       Required for the main suite under integration-tests/. Unused by
                       the e2e suite under integration-tests/e2e/.
  --host-bin           Host LLVM bin directory for llvm-profdata/llvm-cov.

Any additional arguments are forwarded to lit unchanged.
If no extra arguments are provided, lit runs on ".".
EOF
}

venv_dir=""
llvm_build=""
llvm_coverage_build=""
llvm_sancov_build=""
llvm_src=""
host_bin=""
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
        --llvm-coverage-build)
            if [[ $# -lt 2 ]]; then
                echo "error: --llvm-coverage-build requires a value" >&2
                usage
                exit 2
            fi
            llvm_coverage_build="$2"
            shift 2
            ;;
        --host-bin)
            if [[ $# -lt 2 ]]; then
                echo "error: --host-bin requires a value" >&2
                usage
                exit 2
            fi
            host_bin="$2"
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

if [[ -n "$llvm_sancov_build" && ! -d "$llvm_sancov_build" ]]; then
    echo "error: LLVM SanitizerCoverage bin directory does not exist: $llvm_sancov_build" >&2
    exit 2
fi

if [[ -z "$llvm_coverage_build" ]]; then
    llvm_coverage_build="${FUZZ_FILL_LLVM_COVERAGE_BUILD_DIR:-}"
fi
if [[ -z "$llvm_coverage_build" && -n "${FUZZ_FILL_LLVM_COVERAGE_BIN_DIR:-}" ]]; then
    llvm_coverage_build="$(dirname "$FUZZ_FILL_LLVM_COVERAGE_BIN_DIR")"
fi
if [[ -n "$llvm_coverage_build" && "$(basename "$llvm_coverage_build")" == "bin" ]]; then
    llvm_coverage_build="$(dirname "$llvm_coverage_build")"
fi
if [[ -n "$llvm_coverage_build" && ! -d "$llvm_coverage_build" ]]; then
    echo "error: LLVM coverage build directory does not exist: $llvm_coverage_build" >&2
    exit 2
fi

if [[ -z "$host_bin" ]]; then
    host_bin="${FUZZ_FILL_HOST_BIN:-$llvm_build}"
fi
if [[ ! -d "$host_bin" ]]; then
    echo "error: host bin directory does not exist: $host_bin" >&2
    exit 2
fi

if [[ ! -d "$llvm_src/llvm" ]]; then
    echo "error: llvm-project checkout not found at: $llvm_src/llvm" >&2
    exit 2
fi

export FUZZ_FILL_VENV_DIR="$venv_dir"
export FUZZ_FILL_LLVM_BIN_DIR="$llvm_build"
export FUZZ_FILL_LLVM_SRC_DIR="$llvm_src"
export FUZZ_FILL_HOST_BIN="$host_bin"
if [[ -n "$llvm_coverage_build" ]]; then
    export FUZZ_FILL_LLVM_COVERAGE_BUILD_DIR="$llvm_coverage_build"
    export FUZZ_FILL_LLVM_COVERAGE_BIN_DIR="$llvm_coverage_build/bin"
else
    unset FUZZ_FILL_LLVM_COVERAGE_BUILD_DIR FUZZ_FILL_LLVM_COVERAGE_BIN_DIR
fi

unset FUZZ_FILL_SANCOV FUZZ_FILL_LLVM_LIT FUZZ_FILL_LLC FUZZ_FILL_OPT \
      FUZZ_FILL_LLVM_REDUCE FUZZ_FILL_LLVM_DIS

if [[ ${#lit_args[@]} -eq 0 ]]; then
    lit_args=(.)
fi

if [[ -n "$llvm_sancov_build" ]]; then
    export FUZZ_FILL_LLVM_SANCOV_BIN_DIR="$llvm_sancov_build"
    # Patch once before lit schedules tests; parallel baseline RUN lines otherwise
    # race while appending to the shared LLVM build's lit.site.cfg.py.
    "$venv_dir/bin/python" - "$llvm_sancov_build/llvm-lit" <<'PY'
import sys
from pathlib import Path

from coverage.lit_config import ensure_lit_sancov_env_forwarding

ensure_lit_sancov_env_forwarding(Path(sys.argv[1]))
PY
else
    # Drop any inherited value so the main suite cannot accidentally succeed.
    unset FUZZ_FILL_LLVM_SANCOV_BIN_DIR
fi

exec lit "${lit_args[@]}"
