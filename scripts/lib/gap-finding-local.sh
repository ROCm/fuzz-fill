#!/usr/bin/env bash
# Shared CLI helpers for local (non-Docker) gap-finding entrypoints.
# Source after SCRIPT_DIR and REPO_ROOT are set.

: "${SCRIPT_DIR:?SCRIPT_DIR must be set before sourcing gap-finding-local.sh}"
: "${REPO_ROOT:?REPO_ROOT must be set before sourcing gap-finding-local.sh}"

gap_finding_local_source_libs() {
    # shellcheck source=scripts/lib/common.sh
    source "${SCRIPT_DIR}/lib/common.sh"
    # shellcheck source=scripts/lib/local-llvm-env.sh
    source "${SCRIPT_DIR}/lib/local-llvm-env.sh"
    # shellcheck source=scripts/lib/lit-filters.sh
    source "${SCRIPT_DIR}/lib/lit-filters.sh"
    # shellcheck source=scripts/lib/lit-failures.sh
    source "${SCRIPT_DIR}/lib/lit-failures.sh"

    output_dir=""
    lit_filters=()
    jobs=""
    llvm_repo=""
    llvm_bin=""
    instrumented_bin_dir=""
    backend_tests=""
}

# Override in entrypoints to parse workflow-specific flags (e.g. --commit).
gap_finding_local_try_parse_extra() {
    return 1
}

gap_finding_local_usage_llvm_options() {
    cat <<EOF
  --llvm-repo <path>            llvm-project checkout (required)
  --llvm-bin <path>               Uninstrumented LLVM bin dir with sancov (required)
  --instrumented-bin-dir <path>   SanitizerCoverage bin dir with llvm-lit, llc, opt (required)
EOF
}

gap_finding_local_usage_common_options() {
    cat <<EOF
  --lit-filter <prefix>           LIT directory prefix; repeat for multiple
  --backend-tests amdgpu|spirv    Default LIT filter(s) when --lit-filter is omitted
  -j <n>, --jobs <n>              Parallel jobs for llvm-lit
  --help, -h                      Show this help
EOF
}

# Parse shared local flags. Exits on --help or unknown options.
gap_finding_local_parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --output-dir)
                [[ $# -ge 2 ]] || { echo "error: --output-dir requires a value" >&2; exit 2; }
                output_dir="$2"
                shift 2
                ;;
            --lit-filter)
                [[ $# -ge 2 ]] || { echo "error: --lit-filter requires a value" >&2; exit 2; }
                lit_filters+=("$2")
                shift 2
                ;;
            --llvm-repo)
                [[ $# -ge 2 ]] || { echo "error: --llvm-repo requires a value" >&2; exit 2; }
                llvm_repo="$2"
                shift 2
                ;;
            --llvm-bin)
                [[ $# -ge 2 ]] || { echo "error: --llvm-bin requires a value" >&2; exit 2; }
                llvm_bin="$2"
                shift 2
                ;;
            --instrumented-bin-dir)
                [[ $# -ge 2 ]] || { echo "error: --instrumented-bin-dir requires a value" >&2; exit 2; }
                instrumented_bin_dir="$2"
                shift 2
                ;;
            --backend-tests)
                [[ $# -ge 2 ]] || { echo "error: --backend-tests requires a value" >&2; exit 2; }
                backend_tests="$2"
                shift 2
                ;;
            -j|--jobs)
                [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
                jobs="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            --)
                shift
                break
                ;;
            -*)
                if gap_finding_local_try_parse_extra "$1" "${2:-}"; then
                    shift "${GAP_FINDING_LOCAL_EXTRA_SHIFT:-1}"
                    continue
                fi
                echo "error: unknown option: $1" >&2
                usage >&2
                exit 2
                ;;
            *)
                echo "error: unexpected argument: $1" >&2
                usage >&2
                exit 2
                ;;
        esac
    done

    gap_finding_local_finish_arg_parse "$@"
}

gap_finding_local_finish_arg_parse() {
    if [[ $# -gt 0 ]]; then
        echo "error: unexpected argument: $1" >&2
        return 1
    fi
    return 0
}

gap_finding_local_validate_required_paths() {
    local missing=0

    if [[ -z "$output_dir" ]]; then
        echo "error: --output-dir is required" >&2
        missing=1
    fi
    if [[ -z "$llvm_repo" ]]; then
        echo "error: --llvm-repo is required" >&2
        missing=1
    fi
    if [[ -z "$llvm_bin" ]]; then
        echo "error: --llvm-bin is required" >&2
        missing=1
    fi
    if [[ -z "$instrumented_bin_dir" ]]; then
        echo "error: --instrumented-bin-dir is required" >&2
        missing=1
    fi

    if [[ "$missing" -ne 0 ]]; then
        return 1
    fi

    validate_jobs "$jobs"
    return 0
}

# mode: single (one prefix) or multi (full allowlist list).
gap_finding_local_default_lit_filters() {
    local mode="$1"

    if [[ ${#lit_filters[@]} -gt 0 ]]; then
        return 0
    fi

    if [[ -z "$backend_tests" ]]; then
        echo "error: pass --lit-filter or --backend-tests (amdgpu|spirv)" >&2
        return 1
    fi

    case "$mode" in
        single)
            lit_filters=("$(lit_filter_for_allowlist "$backend_tests")")
            echo "backend-tests: ${backend_tests} -> lit-filter: ${lit_filters[0]}"
            ;;
        multi)
            mapfile -t lit_filters < <(default_lit_filters_for_allowlist "$backend_tests")
            echo "backend-tests: ${backend_tests} -> ${#lit_filters[@]} lit-filter prefix(es)"
            ;;
        *)
            echo "error: gap_finding_local_default_lit_filters: unknown mode: ${mode}" >&2
            exit 1
            ;;
    esac
}

gap_finding_local_prepare_output_dir() {
    mkdir -p "$output_dir"
    output_dir="$(realpath "$output_dir")"
}

gap_finding_local_setup_llvm_env() {
    setup_local_llvm_env "$llvm_repo" "$llvm_bin" "$instrumented_bin_dir"
    export LIT_ALLOW_FAILURES=1
    if [[ -n "$jobs" ]]; then
        export JOBS="$jobs"
    fi
}
