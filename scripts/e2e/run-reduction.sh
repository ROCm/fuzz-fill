#!/usr/bin/env bash
# Run batch reduction on gap-fill output and verify shrinkage.
#
# Usage:
#   scripts/e2e/run-reduction.sh \
#     --gap-fill-dir /path/to/gap-fill \
#     --candidate-corpus-dir /path/to/corpus \
#     --llvm-repo /path/llvm-project \
#     --llvm-bin /path/build-sancov/bin \
#     --instrumented-bin-dir /path/build-sancov/bin

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

gap_fill_dir=""
candidate_corpus_dir=""
llvm_repo=""
llvm_bin=""
instrumented_bin_dir=""

usage() {
    cat <<EOF
Usage: $(basename "$0") --gap-fill-dir <path> [options]

Run reduction on the first gap-fill hit and assert reduced.ll is smaller than input.

Required:
  --gap-fill-dir <path>           Gap-fill output (incremental/new_coverage.csv)
  --llvm-repo <path>              llvm-project checkout
  --llvm-bin <path>               LLVM bin dir (llvm-reduce, llvm-dis)
  --instrumented-bin-dir <path>   SanitizerCoverage bin dir (llc)

Options:
  --candidate-corpus-dir <path>   Fuzz corpus from gap filling (resolves test.sh inputs)
  --help, -h                      Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --gap-fill-dir)
            gap_fill_dir="$2"
            shift 2
            ;;
        --candidate-corpus-dir)
            candidate_corpus_dir="$2"
            shift 2
            ;;
        --llvm-repo)
            llvm_repo="$2"
            shift 2
            ;;
        --llvm-bin)
            llvm_bin="$2"
            shift 2
            ;;
        --instrumented-bin-dir)
            instrumented_bin_dir="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

missing=0
for var_name in gap_fill_dir llvm_repo llvm_bin instrumented_bin_dir; do
    if [[ -z "${!var_name}" ]]; then
        echo "error: --${var_name//_/-} is required" >&2
        missing=1
    fi
done
if [[ "$missing" -ne 0 ]]; then
    usage >&2
    exit 1
fi

if [[ ! -d "$gap_fill_dir" ]]; then
    echo "error: gap-fill dir not found: ${gap_fill_dir}" >&2
    exit 1
fi

reduce_args=(
    "${REPO_ROOT}/scripts/reduction.sh"
    --gap-fill-dir "$gap_fill_dir"
    --llvm-repo "$llvm_repo"
    --llvm-bin "$llvm_bin"
    --instrumented-bin-dir "$instrumented_bin_dir"
    -n 1
    --pipeline llvm_reduce_ir
)
if [[ -n "$candidate_corpus_dir" ]]; then
    reduce_args+=(--candidate-corpus-dir "$candidate_corpus_dir")
fi

echo "=== e2e reduction (first gap-fill hit) ==="
"${reduce_args[@]}"

reduced_root="${gap_fill_dir}/reduced"
mapfile -t case_dirs < <(find "$reduced_root" -maxdepth 1 -type d -name 't-00001-*' | LC_ALL=C sort)
if [[ "${#case_dirs[@]}" -eq 0 ]]; then
    echo "error: no t-00001-* case directory under ${reduced_root}" >&2
    exit 1
fi
case_dir="${case_dirs[0]}"

config_json="${case_dir}/config.json"
reduced_ll="${case_dir}/reduced/reduced.ll"
if [[ ! -f "$config_json" ]]; then
    echo "error: missing ${config_json}" >&2
    exit 1
fi
if [[ ! -f "$reduced_ll" ]]; then
    echo "error: missing ${reduced_ll}" >&2
    exit 1
fi

input_name="$(python3 - "$config_json" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["input"])
PY
)"
input_path="${case_dir}/${input_name}"
if [[ ! -f "$input_path" ]]; then
    echo "error: missing reduction input ${input_path}" >&2
    exit 1
fi

llvm_dis="${llvm_bin%/}/llvm-dis"
if [[ ! -x "$llvm_dis" ]]; then
    echo "error: llvm-dis not executable: ${llvm_dis}" >&2
    exit 1
fi

baseline_ll="$(mktemp "${TMPDIR:-/tmp}/e2e-reduce-baseline.XXXXXX.ll")"
cleanup() {
    rm -f "$baseline_ll"
}
trap cleanup EXIT

case "${input_path##*.}" in
    bc)
        "$llvm_dis" -o "$baseline_ll" "$input_path"
        baseline_path="$baseline_ll"
        ;;
    ll)
        baseline_path="$input_path"
        ;;
    *)
        echo "error: unsupported reduction input suffix: ${input_path}" >&2
        exit 1
        ;;
esac

baseline_size=$(stat -c%s "$baseline_path")
reduced_size=$(stat -c%s "$reduced_ll")
if [[ "$reduced_size" -ge "$baseline_size" ]]; then
    echo "error: reduced output (${reduced_size} bytes) is not smaller than baseline (${baseline_size} bytes)" >&2
    echo "  baseline: ${baseline_path}" >&2
    echo "  reduced:  ${reduced_ll}" >&2
    exit 1
fi

echo "e2e reduction OK: ${reduced_ll} (${reduced_size} bytes < ${baseline_size} bytes baseline)"
