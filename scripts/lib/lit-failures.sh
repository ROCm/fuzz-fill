#!/usr/bin/env bash
# Post-run warning when LIT tests failed during a baseline coverage run.
# Source from entrypoints or other scripts/lib modules; do not execute directly.

: "${LIB_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
: "${SCRIPTS_DIR:=$(cd "${LIB_DIR}/.." && pwd)}"

emit_lit_failures_warning() {
    local output_dir="$1"
    local downstream_context="$2"

    local lit_failures_json="${output_dir}/baseline/lit_failures.json"
    local warning_file="${output_dir}/README-WARNING"
    local fail_count=0

    if [[ -f "$lit_failures_json" ]]; then
        fail_count="$(python3 "${SCRIPTS_DIR}/count_lit_failures.py" "$lit_failures_json")"
    fi

    if [[ "$fail_count" -gt 0 ]]; then
        local msg="WARNING: ${fail_count} LIT test(s) failed during the baseline run (e.g., failed a check, timed out, unresolved, or unexpectedly passed).
Failed tests may lead to an incomplete coverage profile. As a result,
${downstream_context} may report lines as uncovered even though they are
actually covered by a (failing) test.
Review baseline/lit_failures.json for the list of failing tests."

        if [[ -t 1 ]]; then
            printf '%b\n' "\033[1;31m${msg}\033[0m"
        else
            printf '%s\n' "$msg"
        fi

        printf '%s\n' "$msg" > "$warning_file"
        echo "Wrote ${warning_file}"
    fi
}
