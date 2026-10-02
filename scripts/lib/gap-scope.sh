#!/usr/bin/env bash
# Gap-analysis scope helpers (backends, tests, allowlist).
# Source from entrypoints; do not execute directly.

: "${REPO_ROOT:?REPO_ROOT must be set before sourcing gap-scope.sh}"

GAP_SCOPE_DEFAULT_ALLOWLIST="${REPO_ROOT}/scripts/allowlist-llvm-clang.txt"
GAP_SCOPE_DEFAULT_BACKENDS="all"
GAP_SCOPE_DEFAULT_TESTS=("llvm/test" "clang/test")

# Map an allowlist file path or preset name to a Docker SANCOV_ALLOWLIST preset.
gap_scope_allowlist_preset() {
    local value="$1"
    local base
    case "$value" in
        amdgpu|spirv|llvm|clang|llvm-clang)
            printf '%s' "$value"
            return 0
            ;;
    esac
    base="$(basename "$value")"
    case "$base" in
        allowlist-amdgpu.txt) printf 'amdgpu' ;;
        allowlist-spirv.txt) printf 'spirv' ;;
        allowlist-llvm.txt) printf 'llvm' ;;
        allowlist-clang.txt) printf 'clang' ;;
        allowlist-llvm-clang.txt) printf 'llvm-clang' ;;
        *)
            echo "error: cannot map allowlist to image preset: ${value}" >&2
            return 1
            ;;
    esac
}

# Resolve a user --allowlist value to an absolute file path.
gap_scope_resolve_allowlist_path() {
    local value="$1"
    case "$value" in
        amdgpu) printf '%s' "${REPO_ROOT}/scripts/allowlist-amdgpu.txt" ;;
        spirv) printf '%s' "${REPO_ROOT}/scripts/allowlist-spirv.txt" ;;
        llvm) printf '%s' "${REPO_ROOT}/scripts/allowlist-llvm.txt" ;;
        clang) printf '%s' "${REPO_ROOT}/scripts/allowlist-clang.txt" ;;
        llvm-clang) printf '%s' "${REPO_ROOT}/scripts/allowlist-llvm-clang.txt" ;;
        *)
            if [[ -f "$value" ]]; then
                realpath "$value"
            else
                echo "error: allowlist file not found: ${value}" >&2
                return 1
            fi
            ;;
    esac
}

# Clang is built when the allowlist instruments clang/lib.
gap_scope_enable_projects_for_allowlist() {
    local preset
    preset="$(gap_scope_allowlist_preset "$1")" || return 1
    case "$preset" in
        clang|llvm-clang) printf 'clang' ;;
        *) printf '' ;;
    esac
}

# Parse gap_scope CLI key=value lines into shell variables.
# Sets: gap_scope_action, gap_scope_rule, gap_scope_backends, gap_scope_tests
#        gap_scope_allowlist, gap_scope_reason
gap_scope_classify_commit() {
    local llvm_repo="$1"
    local commit="$2"
    local line key value

    gap_scope_action=""
    gap_scope_rule=""
    gap_scope_backends=""
    gap_scope_tests=""
    gap_scope_allowlist=""
    gap_scope_reason=""

    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        key="${line%%=*}"
        value="${line#*=}"
        case "$key" in
            action) gap_scope_action="$value" ;;
            rule) gap_scope_rule="$value" ;;
            backends) gap_scope_backends="$value" ;;
            tests) gap_scope_tests="$value" ;;
            allowlist) gap_scope_allowlist="$value" ;;
            reason) gap_scope_reason="$value" ;;
        esac
    done < <(PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:$PYTHONPATH}" \
        python -m gap_scope --llvm-repo "$llvm_repo" --commit "$commit")
}

# Copy a classification into backends, tests[], allowlist, and enable_projects.
# enable_projects comes from the allowlist preset, not from the classifier.
gap_scope_apply_classification() {
    backends="$gap_scope_backends"
    allowlist="$gap_scope_allowlist"
    tests=()
    if [[ -n "$gap_scope_tests" ]]; then
        IFS=',' read -r -a tests <<< "$gap_scope_tests"
    fi
    enable_projects="$(gap_scope_enable_projects_for_allowlist "$allowlist")"
}

# Fill omitted build flags. Allowlist defaults to llvm+clang; Clang follows that preset.
gap_scope_fill_build_scope() {
    if [[ -n "${allowlist:-}" ]]; then
        allowlist="$(gap_scope_resolve_allowlist_path "$allowlist")" || return 1
    else
        allowlist="$GAP_SCOPE_DEFAULT_ALLOWLIST"
    fi
    backends="${backends:-$GAP_SCOPE_DEFAULT_BACKENDS}"
    if [[ ${#tests[@]} -eq 0 ]]; then
        tests=("${GAP_SCOPE_DEFAULT_TESTS[@]}")
    fi
    enable_projects="$(gap_scope_enable_projects_for_allowlist "$allowlist")"
}
