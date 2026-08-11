#!/usr/bin/env bash
# Gap-filling output paths and profile CSV validation.
# Source from entrypoints or other scripts/lib modules; do not execute directly.

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
# shellcheck source=scripts/lib/common.sh
source "${LIB_DIR}/common.sh"

gap_fill_coverage_csv() {
    printf '%s/incremental/new_coverage.csv' "$1"
}

gap_fill_candidate_tests_dir() {
    printf '%s/candidate_tests' "$1"
}

gap_fill_reduced_dir() {
    printf '%s/reduced' "$1"
}

# Resolve gap-fill output paths for batch reduction (names of caller variables).
# Sets *csv_var* and *candidate_var* from *gap_fill_dir_var* unless already set.
resolve_batch_reduction_inputs_from_gap_fill_dir() {
    local gap_fill_dir_var="$1"
    local csv_var="${2:-new_coverage_csv}"
    local candidate_var="${3:-candidate_tests_dir}"
    local gap_fill_dir="${!gap_fill_dir_var:-}"

    if [[ -z "$gap_fill_dir" ]]; then
        echo "error: --gap-fill-dir is required" >&2
        exit 1
    fi
    if [[ ! -d "$gap_fill_dir" ]]; then
        echo "error: --gap-fill-dir is not a directory: ${gap_fill_dir}" >&2
        exit 1
    fi

    gap_fill_dir="$(realpath "$gap_fill_dir")"
    printf -v "$gap_fill_dir_var" '%s' "$gap_fill_dir"

    if [[ -z "${!csv_var:-}" ]]; then
        printf -v "$csv_var" '%s' "$(gap_fill_coverage_csv "$gap_fill_dir")"
    fi
    if [[ -z "${!candidate_var:-}" ]]; then
        printf -v "$candidate_var" '%s' "$(gap_fill_candidate_tests_dir "$gap_fill_dir")"
    fi

    validate_gap_fill_artifacts "${!csv_var}" "${!candidate_var}"
    printf -v "$csv_var" '%s' "$(realpath "${!csv_var}")"
    printf -v "$candidate_var" '%s' "$(realpath "${!candidate_var}")"
}

validate_batch_reduction_inputs() {
    local csv="$1"
    local candidate_tests_dir="$2"

    if [[ -z "$csv" ]]; then
        echo "error: --new-coverage-csv is required (or pass --gap-fill-dir)" >&2
        exit 1
    fi
    if [[ -z "$candidate_tests_dir" ]]; then
        echo "error: --candidate-tests-dir is required (or pass --gap-fill-dir)" >&2
        exit 1
    fi
    validate_gap_fill_artifacts "$csv" "$candidate_tests_dir"
}

validate_gap_fill_artifacts() {
    local coverage_csv="$1"
    local candidate_tests_dir="$2"
    local fill_hint="${3:-run gap-filling first}"

    if [[ ! -f "$coverage_csv" ]]; then
        echo "error: gap-fill CSV not found: ${coverage_csv}" >&2
        echo "hint: ${fill_hint}" >&2
        exit 1
    fi
    if [[ ! -d "$candidate_tests_dir" ]]; then
        echo "error: candidate_tests directory not found: ${candidate_tests_dir}" >&2
        exit 1
    fi
}

validate_gap_profile_csv() {
    local flag_name="$1"
    local path="$2"
    if [[ ! -f "$path" ]]; then
        echo "error: ${flag_name} not found: ${path}" >&2
        exit 1
    fi
}

# Resolve and validate gap-list profile CSVs (names of caller variables).
resolve_gap_profile_csv_paths() {
    local uncovered_var="$1"
    local llc_map_var="$2"
    local uncovered llc_map

    uncovered="${!uncovered_var:-}"
    llc_map="${!llc_map_var:-}"

    if [[ -z "$uncovered" ]]; then
        echo "error: --line-coverage-uncovered-csv is required" >&2
        exit 1
    fi
    if [[ -z "$llc_map" ]]; then
        echo "error: --llc-address-line-map-csv is required" >&2
        exit 1
    fi

    validate_gap_profile_csv "--line-coverage-uncovered-csv" "$uncovered"
    validate_gap_profile_csv "--llc-address-line-map-csv" "$llc_map"

    printf -v "$uncovered_var" '%s' "$(realpath "$uncovered")"
    printf -v "$llc_map_var" '%s' "$(realpath "$llc_map")"
}
