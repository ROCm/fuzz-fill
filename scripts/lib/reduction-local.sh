#!/usr/bin/env bash
# Shared CLI helpers for local (non-Docker) reduction entrypoints.
# Source after SCRIPT_DIR and REPO_ROOT are set.

: "${SCRIPT_DIR:?SCRIPT_DIR must be set before sourcing reduction-local.sh}"
: "${REPO_ROOT:?REPO_ROOT must be set before sourcing reduction-local.sh}"

reduction_local_source_libs() {
    local scripts_lib="${REPO_ROOT}/scripts/lib"
    # shellcheck source=scripts/lib/common.sh
    source "${scripts_lib}/common.sh"
    # shellcheck source=scripts/lib/local-llvm-env.sh
    source "${scripts_lib}/local-llvm-env.sh"
    # shellcheck source=scripts/lib/gap-artifacts.sh
    source "${scripts_lib}/gap-artifacts.sh"

    gap_fill_dir=""
    new_coverage_csv=""
    candidate_tests_dir=""
    candidate_corpus_dir=""
    output_dir=""
    reduction_n=""
    scaffold_only=0
    pipeline=""
    with_creduce=0
    creduce_n=""
    pass_under_test=""
    mtriple=""
    mir_codegen_only=0
    extract_mir_output=""
    extract_ir_output=""
    template_dir=""
    llvm_repo=""
    llvm_bin=""
    instrumented_bin_dir=""
}

reduction_local_usage_llvm_options() {
    cat <<EOF
  --llvm-repo <path>              llvm-project checkout (required unless --scaffold-only)
  --llvm-bin <path>               LLVM bin dir with llvm-reduce (required unless --scaffold-only)
  --instrumented-bin-dir <path>   SanitizerCoverage bin dir with llc (required unless --scaffold-only)
EOF
}

reduction_local_usage_common_options() {
    cat <<EOF
  --gap-fill-dir <path>           Gap-fill output (derives new_coverage.csv + candidate_tests/)
  --new-coverage-csv <path>       Override incremental/new_coverage.csv path
  --candidate-tests-dir <path>    Override candidate_tests/ path
  --candidate-corpus-dir <path>     Fuzz corpus root from gap filling (resolves test.sh inputs)
  --output-dir <path>             Case output directory (default: <gap-fill-dir>/reduced/)
  -n <N>, --n <N>                 Reduce the first N gap-fill hits (required)
  --scaffold-only                 Create case dirs only; do not run llvm-reduce
  --template-dir <path>           interesting_ir.sh template (default: example/amd/new-test-1)
  --pipeline <pass-ids>           Comma-separated reduce pass ids (default: llvm_reduce_ir)
  --with-creduce                  Append creduce to --pipeline when missing
  --creduce-n <N>                 creduce parallelism for pipeline steps
  --pass-under-test <pass>        LLVM pass id for extract_* / interesting_mir.sh
  --mtriple <triple>              Target triple for extract_* / interesting_mir.sh
  --mir-codegen-only              Use interesting_mir_codegen.sh template
  --extract-mir-output <basename> Optional extract_mir_output basename
  --extract-ir-output <basename>  Optional extract_ir_before_output basename
  --help, -h                      Show this help
EOF
}

reduction_local_validate_n() {
    if [[ ! "$reduction_n" =~ ^[0-9]+$ ]] || [[ "$reduction_n" -eq 0 ]]; then
        echo "error: -n/--n must be a positive integer: ${reduction_n}" >&2
        exit 1
    fi
}

# Parse one reduction workflow flag. Returns 0 if consumed; sets REDUCTION_CLI_SHIFT.
reduction_cli_try_parse() {
    REDUCTION_CLI_SHIFT=0

    case "$1" in
        --gap-fill-dir)
            [[ $# -ge 2 ]] || { echo "error: --gap-fill-dir requires a value" >&2; exit 2; }
            gap_fill_dir="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --new-coverage-csv)
            [[ $# -ge 2 ]] || { echo "error: --new-coverage-csv requires a value" >&2; exit 2; }
            new_coverage_csv="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --candidate-tests-dir)
            [[ $# -ge 2 ]] || { echo "error: --candidate-tests-dir requires a value" >&2; exit 2; }
            candidate_tests_dir="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --candidate-corpus-dir)
            [[ $# -ge 2 ]] || { echo "error: --candidate-corpus-dir requires a value" >&2; exit 2; }
            candidate_corpus_dir="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --output-dir)
            [[ $# -ge 2 ]] || { echo "error: --output-dir requires a value" >&2; exit 2; }
            output_dir="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        -n|--n)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            reduction_n="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --scaffold-only)
            scaffold_only=1
            REDUCTION_CLI_SHIFT=1
            return 0
            ;;
        --template-dir)
            [[ $# -ge 2 ]] || { echo "error: --template-dir requires a value" >&2; exit 2; }
            template_dir="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --pipeline)
            [[ $# -ge 2 ]] || { echo "error: --pipeline requires a value" >&2; exit 2; }
            pipeline="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --with-creduce)
            with_creduce=1
            REDUCTION_CLI_SHIFT=1
            return 0
            ;;
        --creduce-n)
            [[ $# -ge 2 ]] || { echo "error: --creduce-n requires a value" >&2; exit 2; }
            creduce_n="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --pass-under-test)
            [[ $# -ge 2 ]] || { echo "error: --pass-under-test requires a value" >&2; exit 2; }
            pass_under_test="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --mtriple)
            [[ $# -ge 2 ]] || { echo "error: --mtriple requires a value" >&2; exit 2; }
            mtriple="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --mir-codegen-only)
            mir_codegen_only=1
            REDUCTION_CLI_SHIFT=1
            return 0
            ;;
        --extract-mir-output)
            [[ $# -ge 2 ]] || { echo "error: --extract-mir-output requires a value" >&2; exit 2; }
            extract_mir_output="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --extract-ir-output)
            [[ $# -ge 2 ]] || { echo "error: --extract-ir-output requires a value" >&2; exit 2; }
            extract_ir_output="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --llvm-repo)
            [[ $# -ge 2 ]] || { echo "error: --llvm-repo requires a value" >&2; exit 2; }
            llvm_repo="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --llvm-bin)
            [[ $# -ge 2 ]] || { echo "error: --llvm-bin requires a value" >&2; exit 2; }
            llvm_bin="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        --instrumented-bin-dir)
            [[ $# -ge 2 ]] || { echo "error: --instrumented-bin-dir requires a value" >&2; exit 2; }
            instrumented_bin_dir="$2"
            REDUCTION_CLI_SHIFT=2
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

reduction_local_parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                usage
                exit 0
                ;;
            --)
                shift
                break
                ;;
            *)
                if reduction_cli_try_parse "$1" "${2:-}"; then
                    shift "${REDUCTION_CLI_SHIFT}"
                    continue
                fi
                echo "error: unknown option: $1" >&2
                usage >&2
                exit 2
                ;;
        esac
    done

    reduction_local_finish_arg_parse "$@"
}

reduction_local_finish_arg_parse() {
    if [[ $# -gt 0 ]]; then
        echo "error: unexpected argument: $1" >&2
        return 1
    fi
    return 0
}

reduction_local_validate_required_paths() {
    local missing=0

    if [[ -z "$reduction_n" ]]; then
        echo "error: -n/--n is required" >&2
        missing=1
    fi

    if [[ -n "$gap_fill_dir" ]]; then
        resolve_batch_reduction_inputs_from_gap_fill_dir \
            gap_fill_dir new_coverage_csv candidate_tests_dir
        if [[ -z "$output_dir" ]]; then
            output_dir="$(gap_fill_reduced_dir "$gap_fill_dir")"
        fi
    else
        if [[ -z "$new_coverage_csv" || -z "$candidate_tests_dir" ]]; then
            echo "error: pass --gap-fill-dir or both --new-coverage-csv and --candidate-tests-dir" >&2
            missing=1
        fi
    fi

    if [[ "$missing" -ne 0 ]]; then
        return 1
    fi

    reduction_local_validate_n
    validate_batch_reduction_inputs "$new_coverage_csv" "$candidate_tests_dir"

    if [[ -z "$output_dir" ]]; then
        echo "error: --output-dir is required when --gap-fill-dir is omitted" >&2
        return 1
    fi

    if [[ "$scaffold_only" -eq 0 && "${REDUCTION_SKIP_HOST_LLVM:-0}" -eq 0 ]]; then
        if [[ -z "$llvm_repo" || -z "$llvm_bin" || -z "$instrumented_bin_dir" ]]; then
            echo "error: --llvm-repo, --llvm-bin, and --instrumented-bin-dir are required unless --scaffold-only" >&2
            return 1
        fi
    fi

    if [[ -n "$candidate_corpus_dir" && ! -d "$candidate_corpus_dir" ]]; then
        echo "error: --candidate-corpus-dir is not a directory: ${candidate_corpus_dir}" >&2
        return 1
    fi

    return 0
}

reduction_local_prepare_paths() {
    mkdir -p "$output_dir"
    output_dir="$(realpath "$output_dir")"
    new_coverage_csv="$(realpath "$new_coverage_csv")"
    candidate_tests_dir="$(realpath "$candidate_tests_dir")"
    if [[ -n "$candidate_corpus_dir" ]]; then
        candidate_corpus_dir="$(realpath "$candidate_corpus_dir")"
        export REDUCTION_CORPUS_DIR="$candidate_corpus_dir"
    fi
    if [[ -n "$template_dir" ]]; then
        template_dir="$(realpath "$template_dir")"
    fi
}

reduction_local_setup_llvm_env() {
    if [[ "$scaffold_only" -eq 1 ]]; then
        return 0
    fi
    setup_local_llvm_env "$llvm_repo" "$llvm_bin" "$instrumented_bin_dir"
    export_local_reduce_tools
    require_local_reduce_bins
}

reduction_local_batch_extra_args() {
    REDUCTION_BATCH_EXTRA_ARGS=()
    if [[ -n "$template_dir" ]]; then
        REDUCTION_BATCH_EXTRA_ARGS+=(--template-dir "$template_dir")
    fi
    if [[ -n "$pipeline" ]]; then
        REDUCTION_BATCH_EXTRA_ARGS+=(--pipeline "$pipeline")
    fi
    if [[ "$with_creduce" -eq 1 ]]; then
        REDUCTION_BATCH_EXTRA_ARGS+=(--with-creduce)
    fi
    if [[ -n "$creduce_n" ]]; then
        REDUCTION_BATCH_EXTRA_ARGS+=(--creduce-n "$creduce_n")
    fi
    if [[ -n "$pass_under_test" ]]; then
        REDUCTION_BATCH_EXTRA_ARGS+=(--pass-under-test "$pass_under_test")
    fi
    if [[ -n "$mtriple" ]]; then
        REDUCTION_BATCH_EXTRA_ARGS+=(--mtriple "$mtriple")
    fi
    if [[ "$mir_codegen_only" -eq 1 ]]; then
        REDUCTION_BATCH_EXTRA_ARGS+=(--mir-codegen-only)
    fi
    if [[ -n "$extract_mir_output" ]]; then
        REDUCTION_BATCH_EXTRA_ARGS+=(--extract-mir-output "$extract_mir_output")
    fi
    if [[ -n "$extract_ir_output" ]]; then
        REDUCTION_BATCH_EXTRA_ARGS+=(--extract-ir-output "$extract_ir_output")
    fi
}
