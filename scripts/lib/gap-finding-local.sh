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
    # shellcheck source=scripts/lib/gap-scope.sh
    source "${SCRIPT_DIR}/lib/gap-scope.sh"
    # shellcheck source=scripts/lib/lit-failures.sh
    source "${SCRIPT_DIR}/lib/lit-failures.sh"

    output_dir=""
    lit_filters=()
    tests=()
    jobs=""
    llvm_repo=""
    llvm_bin=""
    instrumented_bin_dir=""
    auto_scope=0
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
  --auto                          Choose lit suites from the commit (requires --commit or --pr-id)
  --tests <suite>                 Lit suite root or subdirectory (repeatable)
  --lit-filter <regex>            llvm-lit --filter= regex for every --tests suite; repeatable
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
            --tests)
                [[ $# -ge 2 ]] || { echo "error: --tests requires a value" >&2; exit 2; }
                case "$2" in
                    */test|*/test/*) ;;
                    *)
                        echo "error: --tests must be <project>/test or a subdirectory: $2" >&2
                        exit 1
                        ;;
                esac
                tests+=("$2")
                shift 2
                ;;
            --auto)
                auto_scope=1
                shift
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

# Choose lit suites. --auto reads them from the commit; otherwise use --tests
# or the full llvm/test + clang/test default.
# Returns 2 when classification says to skip the run.
# The binary is already built, so backends and allowlist are only printed.
gap_finding_local_resolve_scope() {
    if [[ "$auto_scope" -eq 1 ]]; then
        if [[ ${#tests[@]} -gt 0 ]]; then
            echo "error: --auto cannot be combined with --tests" >&2
            return 1
        fi
        if [[ -z "${commit_rev:-}" ]]; then
            echo "error: --auto requires --commit or --pr-id" >&2
            return 1
        fi
        gap_scope_classify_commit "$llvm_repo" "$commit_rev"
        if [[ "$gap_scope_action" == "skip" ]]; then
            echo "gap-scope: skip (rule ${gap_scope_rule}): ${gap_scope_reason}"
            return 2
        fi
        local projects
        IFS=',' read -r -a tests <<< "$gap_scope_tests"
        projects="$(gap_scope_enable_projects_for_allowlist "$gap_scope_allowlist")"
        echo "gap-scope: rule=${gap_scope_rule} tests=${tests[*]} (${gap_scope_reason})"
        echo "gap-scope: matching build is backends=${gap_scope_backends} allowlist=${gap_scope_allowlist} enable_projects=${projects:-<none>}"
        return 0
    fi

    if [[ ${#tests[@]} -eq 0 ]]; then
        tests=("${GAP_SCOPE_DEFAULT_TESTS[@]}")
    fi
    return 0
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
