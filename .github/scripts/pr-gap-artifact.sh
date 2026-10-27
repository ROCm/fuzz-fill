#!/usr/bin/env bash
# Stage, strip, and verify PR gap-analysis workflow artifacts.
# Usage: pr-gap-artifact.sh <finding-results|finding-raw> [options]
# "finding-results" is the user-facing report; "finding-raw" keeps all baseline CSVs.

set -euo pipefail

ARTIFACT_DIR="${ARTIFACT_DIR:-/work/artifact}"
WORK_ROOT="${WORK_ROOT:-/work}"

usage() {
    cat <<EOF
Usage:
  $(basename "$0") finding-results --out-dir <path> --squash-commit <path> [--readme <path>]
  $(basename "$0") finding-raw --out-dir <path> --squash-commit <path> [--readme <path>]
  $(basename "$0") finalize
EOF
}

_copy_finding_common() {
    local out_dir="$1" squash_commit="$2" readme="$3"

    mkdir -p \
        "${ARTIFACT_DIR}/out/baseline" \
        "${ARTIFACT_DIR}/out/added-lines" \
        "${ARTIFACT_DIR}/out/commit_lines_report"

    while IFS= read -r -d '' csv; do
        cp "${csv}" "${ARTIFACT_DIR}/out/added-lines/"
    done < <(find "${out_dir}/added-lines" -maxdepth 1 -type f -name '*.csv' -print0 2>/dev/null || true)

    while IFS= read -r -d '' csv; do
        cp "${csv}" "${ARTIFACT_DIR}/out/commit_lines_report/"
    done < <(find "${out_dir}/commit_lines_report" -maxdepth 1 -type f -name '*.csv' -print0 2>/dev/null || true)

    cp "${squash_commit}" "${ARTIFACT_DIR}/squash-commit"

    if [[ -n "$readme" ]]; then
        cp "${readme}" "${ARTIFACT_DIR}/README-finding.txt"
    fi

    if [[ -f "${out_dir}/README-WARNING" ]]; then
        cp "${out_dir}/README-WARNING" "${ARTIFACT_DIR}/README-WARNING"
    fi
    if [[ -f "${out_dir}/baseline/lit_failures.json" ]]; then
        cp "${out_dir}/baseline/lit_failures.json" "${ARTIFACT_DIR}/out/baseline/lit_failures.json"
    fi
    if [[ -f "${out_dir}/baseline/timings.csv" ]]; then
        cp "${out_dir}/baseline/timings.csv" "${ARTIFACT_DIR}/out/baseline/timings.csv"
    fi
}

# Metadata + coverage report only (no per-tool address/line-point maps).
stage_finding_results() {
    local out_dir="" squash_commit="" readme=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --out-dir) out_dir="$2"; shift 2 ;;
            --squash-commit) squash_commit="$2"; shift 2 ;;
            --readme) readme="$2"; shift 2 ;;
            *) echo "error: unknown option: $1" >&2; exit 2 ;;
        esac
    done

    [[ -n "$out_dir" && -n "$squash_commit" ]] || { usage >&2; exit 2; }

    rm -rf "${ARTIFACT_DIR}"
    _copy_finding_common "${out_dir}" "${squash_commit}" "${readme}"

    while IFS= read -r -d '' csv; do
        cp "${csv}" "${ARTIFACT_DIR}/out/baseline/"
    done < <(find "${out_dir}/baseline" -maxdepth 1 -type f -name 'line_coverage*.csv' -print0)
}

# All baseline CSVs (per-tool maps); for deep dives / debugging.
stage_finding_raw() {
    local out_dir="" squash_commit="" readme=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --out-dir) out_dir="$2"; shift 2 ;;
            --squash-commit) squash_commit="$2"; shift 2 ;;
            --readme) readme="$2"; shift 2 ;;
            *) echo "error: unknown option: $1" >&2; exit 2 ;;
        esac
    done

    [[ -n "$out_dir" && -n "$squash_commit" ]] || { usage >&2; exit 2; }

    rm -rf "${ARTIFACT_DIR}"
    _copy_finding_common "${out_dir}" "${squash_commit}" "${readme}"

    while IFS= read -r -d '' csv; do
        cp "${csv}" "${ARTIFACT_DIR}/out/baseline/"
    done < <(find "${out_dir}/baseline" -maxdepth 1 -type f -name '*.csv' -print0)
}

finalize() {
    find "${ARTIFACT_DIR}" -type f \( -name '*.sancov' -o -name '*.symcov' \) -print -delete

    local forbidden
    for forbidden in pr-llvm llvm-main llvm-project build-sancov build-sancov-main llvm-release candidate-tests-dataset; do
        if [[ -e "${ARTIFACT_DIR}/${forbidden}" ]]; then
            echo "error: artifact must not contain ${forbidden}" >&2
            exit 1
        fi
    done

    if find "${ARTIFACT_DIR}" -type f \( -name 'llc' -o -name 'opt' -o -name 'clang' -o -name 'clang++' \) | grep -q .; then
        echo "error: artifact must not contain LLVM binaries" >&2
        exit 1
    fi

    echo "Artifact staged at ${ARTIFACT_DIR}:"
    find "${ARTIFACT_DIR}" -type f | LC_ALL=C sort
}

cmd="${1:-}"
shift || true

case "$cmd" in
    finding-results) stage_finding_results "$@" ;;
    finding-raw) stage_finding_raw "$@" ;;
    finalize) finalize ;;
    *) usage >&2; exit 2 ;;
esac
