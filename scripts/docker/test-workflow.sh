#!/usr/bin/env bash
# End-to-end Docker smoke test: gap finding -> gap filling -> reduction (scaffold).
#
# Usage (from repo root):
#   ./scripts/docker/test-workflow.sh
#   LLVM=/path/to/llvm-project ./scripts/docker/test-workflow.sh --build-image
#   FULL_REDUCE=1 ./scripts/docker/test-workflow.sh
#
# Environment:
#   DATA          Output root (default: ./data/workflow-test)
#   LLVM          llvm-project checkout for --build-image (default: ../llvm-project)
#   J             Parallel jobs (default: nproc)
#   FULL_REDUCE   If 1, run reduction without --scaffold-only (slow)
#   REDUCE_N      Rows to reduce (default: 1)
#   GAP_FILL_N    Candidate tests to run (default: 1)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

DATA="${DATA:-${REPO_ROOT}/data/workflow-test}"
LLVM="${LLVM:-$(cd "${REPO_ROOT}/../llvm-project" 2>/dev/null && pwd || true)}"
J="${J:-$(nproc)}"
FULL_REDUCE="${FULL_REDUCE:-0}"
REDUCE_N="${REDUCE_N:-1}"
GAP_FILL_N="${GAP_FILL_N:-1}"
BUILD_IMAGE=0
BIND_REPO=(--bind-repo)

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run gap-finding-baseline, gap-filling, and reduction in Docker.

Options:
  --build-image    Build fuzz-fill-test:latest first (pass LLVM=... if not ../llvm-project)
  --no-bind-repo   Use fuzz-fill copy baked into the image
  --help, -h       Show this help

Environment:
  DATA=${DATA}
  LLVM=<llvm-project checkout>
  J=${J}
  FULL_REDUCE=${FULL_REDUCE}  (1 = run llvm-reduce, not just scaffold)
  REDUCE_N=${REDUCE_N}
  GAP_FILL_N=${GAP_FILL_N}

Example:
  ./scripts/docker/test-workflow.sh --build-image
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --build-image)
            BUILD_IMAGE=1
            shift
            ;;
        --no-bind-repo)
            BIND_REPO=()
            shift
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

if [[ "$BUILD_IMAGE" -eq 1 ]]; then
    if [[ -z "$LLVM" || ! -d "$LLVM/llvm" ]]; then
        echo "error: set LLVM to an llvm-project checkout for --build-image" >&2
        exit 1
    fi
    echo "=== build Docker image ==="
    "${SCRIPT_DIR}/build-image.sh" --llvm-dir "$LLVM" --allowlist amdgpu -j "$J"
fi

GAP_FINDING_OUT="${DATA}/gap-finding"
GAP_FILL_OUT="${DATA}/gap-fill"
CORPUS="${REPO_ROOT}/integration-tests/fixtures/coverage-new-tests"
UNCOVERED_CSV="${GAP_FINDING_OUT}/baseline/line_coverage_uncovered.csv"
LLC_MAP_CSV="${GAP_FINDING_OUT}/baseline/llc_address_line_map.csv"
NEW_COVERAGE_CSV="${GAP_FILL_OUT}/incremental/new_coverage.csv"

mkdir -p "$DATA"

echo "=== gap finding (baseline) ==="
"${SCRIPT_DIR}/gap-finding-baseline.sh" \
    "${BIND_REPO[@]}" \
    --output-dir "$GAP_FINDING_OUT" \
    --lit-filter CodeGen/AMDGPU/loop \
    -j "$J"

echo "=== gap filling ==="
"${SCRIPT_DIR}/gap-filling.sh" \
    "${BIND_REPO[@]}" \
    --output-dir "$GAP_FILL_OUT" \
    --line-coverage-uncovered-csv "$UNCOVERED_CSV" \
    --llc-address-line-map-csv "$LLC_MAP_CSV" \
    --candidate-tests-dir "$CORPUS" \
    -n "$GAP_FILL_N" \
    -j "$J"

if [[ ! -f "$NEW_COVERAGE_CSV" ]]; then
    echo "error: expected ${NEW_COVERAGE_CSV}" >&2
    exit 1
fi

row_count=$(($(wc -l <"$NEW_COVERAGE_CSV") - 1))
if [[ "$row_count" -lt 1 ]]; then
    echo "error: ${NEW_COVERAGE_CSV} has no data rows; cannot test reduction" >&2
    exit 1
fi
echo "gap-fill hits: ${row_count} row(s) in ${NEW_COVERAGE_CSV}"

reduce_args=(
    "${BIND_REPO[@]}"
    --gap-fill-dir "$GAP_FILL_OUT"
    --candidate-corpus-dir "$CORPUS"
    -n "$REDUCE_N"
)
if [[ "$FULL_REDUCE" -eq 0 ]]; then
    reduce_args+=(--scaffold-only)
else
    reduce_args+=(--pipeline llvm_reduce_ir)
fi

echo "=== reduction (n=${REDUCE_N}, full_reduce=${FULL_REDUCE}) ==="
"${SCRIPT_DIR}/reduction.sh" "${reduce_args[@]}"

REDUCED_DIR="${GAP_FILL_OUT}/reduced"
if ! compgen -G "${REDUCED_DIR}/t-*" >/dev/null; then
    echo "error: no case directories under ${REDUCED_DIR}/" >&2
    exit 1
fi

echo
echo "Workflow OK."
echo "  gap finding: ${GAP_FINDING_OUT}/baseline/"
echo "  gap filling: ${GAP_FILL_OUT}/incremental/new_coverage.csv"
echo "  reduction:   ${REDUCED_DIR}/"
