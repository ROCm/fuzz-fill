#!/usr/bin/env bash
# Shared CLI helpers for local (non-Docker) gap-filling entrypoints.
# Source after SCRIPT_DIR and REPO_ROOT are set.

: "${SCRIPT_DIR:?SCRIPT_DIR must be set before sourcing gap-filling-local.sh}"
: "${REPO_ROOT:?REPO_ROOT must be set before sourcing gap-filling-local.sh}"

gap_filling_local_source_libs() {
    # shellcheck source=scripts/lib/common.sh
    source "${SCRIPT_DIR}/lib/common.sh"
    # shellcheck source=scripts/lib/local-llvm-env.sh
    source "${SCRIPT_DIR}/lib/local-llvm-env.sh"
    # shellcheck source=scripts/lib/gap-artifacts.sh
    source "${SCRIPT_DIR}/lib/gap-artifacts.sh"

    output_dir=""
    line_coverage_uncovered_csv=""
    llc_address_line_map_csv=""
    candidate_tests_dir=""
    candidate_n=""
    settings_csv=""
    jobs=""
    llvm_repo=""
    llvm_bin=""
    instrumented_bin_dir=""
}

gap_filling_local_usage_llvm_options() {
    cat <<EOF
  --llvm-repo <path>              llvm-project checkout (required)
  --llvm-bin <path>               Uninstrumented LLVM bin dir with sancov (required)
  --instrumented-bin-dir <path>   SanitizerCoverage bin dir with llc (required)
EOF
}

gap_filling_local_usage_common_options() {
    cat <<EOF
  --settings-csv <path>           Optional llc flag variants CSV for candidate-test
  -j <n>, --jobs <n>              Parallel jobs for candidate-test
  --help, -h                      Show this help
EOF
}

gap_filling_local_validate_candidate_n() {
    if [[ ! "$candidate_n" =~ ^[0-9]+$ ]] || [[ "$candidate_n" -eq 0 ]]; then
        echo "error: -n/--n must be a positive integer: ${candidate_n}" >&2
        exit 1
    fi
}

# Parse shared local flags. Exits on --help or unknown options.
gap_filling_local_parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --output-dir)
                [[ $# -ge 2 ]] || { echo "error: --output-dir requires a value" >&2; exit 2; }
                output_dir="$2"
                shift 2
                ;;
            --line-coverage-uncovered-csv)
                [[ $# -ge 2 ]] || { echo "error: --line-coverage-uncovered-csv requires a value" >&2; exit 2; }
                line_coverage_uncovered_csv="$2"
                shift 2
                ;;
            --llc-address-line-map-csv)
                [[ $# -ge 2 ]] || { echo "error: --llc-address-line-map-csv requires a value" >&2; exit 2; }
                llc_address_line_map_csv="$2"
                shift 2
                ;;
            --candidate-tests-dir)
                [[ $# -ge 2 ]] || { echo "error: --candidate-tests-dir requires a value" >&2; exit 2; }
                candidate_tests_dir="$2"
                shift 2
                ;;
            -n|--n)
                [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
                candidate_n="$2"
                shift 2
                ;;
            --settings-csv)
                [[ $# -ge 2 ]] || { echo "error: --settings-csv requires a value" >&2; exit 2; }
                settings_csv="$2"
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

    gap_filling_local_finish_arg_parse "$@"
}

gap_filling_local_finish_arg_parse() {
    if [[ $# -gt 0 ]]; then
        echo "error: unexpected argument: $1" >&2
        return 1
    fi
    return 0
}

gap_filling_local_validate_required_paths() {
    local missing=0

    if [[ -z "$output_dir" ]]; then
        echo "error: --output-dir is required" >&2
        missing=1
    fi
    if [[ -z "$line_coverage_uncovered_csv" ]]; then
        echo "error: --line-coverage-uncovered-csv is required" >&2
        missing=1
    fi
    if [[ -z "$llc_address_line_map_csv" ]]; then
        echo "error: --llc-address-line-map-csv is required" >&2
        missing=1
    fi
    if [[ -z "$candidate_tests_dir" ]]; then
        echo "error: --candidate-tests-dir is required" >&2
        missing=1
    fi
    if [[ -z "$candidate_n" ]]; then
        echo "error: -n/--n is required" >&2
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

    gap_filling_local_validate_candidate_n
    if [[ ! -d "$candidate_tests_dir" ]]; then
        echo "error: --candidate-tests-dir is not a directory: ${candidate_tests_dir}" >&2
        return 1
    fi
    if [[ -n "$settings_csv" ]] && [[ ! -f "$settings_csv" ]]; then
        echo "error: --settings-csv is not a file: ${settings_csv}" >&2
        return 1
    fi

    validate_jobs "$jobs"
    resolve_gap_profile_csv_paths line_coverage_uncovered_csv llc_address_line_map_csv
    return 0
}

gap_filling_local_prepare_output_dir() {
    mkdir -p "$output_dir"
    output_dir="$(realpath "$output_dir")"
    candidate_tests_dir="$(realpath "$candidate_tests_dir")"
    if [[ -n "$settings_csv" ]]; then
        settings_csv="$(realpath "$settings_csv")"
    fi
}

gap_filling_local_setup_llvm_env() {
    setup_local_llvm_env "$llvm_repo" "$llvm_bin" "$instrumented_bin_dir"
    if [[ -n "$jobs" ]]; then
        export JOBS="$jobs"
    fi
}
