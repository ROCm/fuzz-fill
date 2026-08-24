#!/usr/bin/env bash
# Host-side candidate corpus enumeration and staging for Docker gap-filling.
# Source from entrypoints or other scripts/lib modules; do not execute directly.

# Enumerate .ll/.bc under src (recursive), sorted — matches TestRunner.collect_llc_input_files().
collect_candidate_inputs() {
    local src="$1"
    find "$src" -type f \( -name '*.ll' -o -name '*.bc' \) | LC_ALL=C sort
}

# Copy candidate inputs into staging_dir, preserving relative paths.
# When n is empty, copies all .ll/.bc files; otherwise copies the first n (sorted).
stage_candidate_tests() {
    local src="$1"
    local n="$2"
    local staging_dir="$3"
    local src_real count rel dest_parent

    src_real="$(realpath "$src")"
    mapfile -t candidate_files < <(collect_candidate_inputs "$src_real")

    if [[ "${#candidate_files[@]}" -eq 0 ]]; then
        echo "error: no .ll or .bc files under --candidate-tests-dir: ${src_real}" >&2
        exit 1
    fi

    if [[ -z "$n" ]]; then
        count="${#candidate_files[@]}"
    else
        count="$n"
        if [[ "${#candidate_files[@]}" -lt "$count" ]]; then
            count="${#candidate_files[@]}"
            echo "note: corpus has ${#candidate_files[@]} file(s); staging all of them (requested ${n})"
        fi
    fi

    local i
    for (( i = 0; i < count; i++ )); do
        rel="${candidate_files[$i]#"${src_real}/"}"
        dest_parent="${staging_dir}/$(dirname "$rel")"
        mkdir -p "$dest_parent"
        cp -- "${candidate_files[$i]}" "${staging_dir}/${rel}"
    done

    echo "Staged ${count} candidate test file(s) under ${staging_dir}"
}
