#!/usr/bin/env bash
# Compare SanitizerCoverage from a .bc corpus against the LLVM LIT test suite.
#
# Prerequisites (from fuzz-fill repo root):
#   pip install -e .
#   Download LLVM release and checkout llvm-project at the matching tag, then:
#   ./scripts/build-llvm-sancov.sh scripts/allowlist-amdgpu.txt llvm-project \
#       llvm-project/build-sancov --bootstrap-bin /path/to/LLVM-22.1.8/bin
#
# Usage:
#   ./scripts/corpus_vs_suite_coverage.sh
#   CORPUS_N=100 ./scripts/corpus_vs_suite_coverage.sh          # smoke: first 100 .bc files
#   FILTER='CodeGen/AMDGPU/loop' ./scripts/corpus_vs_suite_coverage.sh
#   FILTER='(^|/)AMDGPU/' ./scripts/corpus_vs_suite_coverage.sh
#   REFRESH=all ./scripts/corpus_vs_suite_coverage.sh           # wipe prior outputs under OUTPUT_DIR
#   SKIP_TEST_SUITE=1 ./scripts/corpus_vs_suite_coverage.sh     # reuse baseline, run corpus + diff only
#
# Main result:
#   $OUTPUT_DIR/diff/new_coverage.csv  — corpus tests that fully cover lines not covered by the suite
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FUZZ_FILL="$(cd "$SCRIPT_DIR/.." && pwd)"

LLVM="${LLVM:-$FUZZ_FILL/llvm-project}"
LLVM_BIN="${LLVM_BIN:-$LLVM/build-sancov/bin}"
INSTRUMENTED_BIN="${INSTRUMENTED_BIN:-$LLVM/build-sancov/bin}"
CORPUS="${CORPUS:-$FUZZ_FILL/amdgpu-tests}"
SOURCE_CODE_FILTER="${SOURCE_CODE_FILTER:-llvm/lib/Target/AMDGPU}"
FILTER="${FILTER:-(^|/)AMDGPU/}"
OUTPUT_DIR="${OUTPUT_DIR:-$FUZZ_FILL/data/coverage_output/corpus_vs_suite_$(date +%y%m%d_%H%M%S)}"

TEST_SUITE_OUTPUT_DIR="$OUTPUT_DIR/test_suite"
NEW_TESTS_OUTPUT_DIR="$OUTPUT_DIR/new_tests"
DIFF_OUTPUT_DIR="$OUTPUT_DIR/diff"
NEW_COVERAGE_CSV="$DIFF_OUTPUT_DIR/new_coverage.csv"

# How many corpus .bc files to run (sorted path order). Default: all under CORPUS.
if [[ -z "${CORPUS_N:-}" ]]; then
  CORPUS_N="$(find "$CORPUS" -type f \( -name '*.bc' -o -name '*.ll' \) | wc -l | tr -d ' ')"
fi

require_bin() {
  local dir="$1" tool="$2"
  if [[ ! -x "$dir/$tool" ]]; then
    echo "error: missing $dir/$tool" >&2
    exit 1
  fi
}

format_duration() {
  local secs=$1
  if (( secs >= 3600 )); then
    printf '%dh%02dm%02ds' $((secs / 3600)) $((secs % 3600 / 60)) $((secs % 60))
  elif (( secs >= 60 )); then
    printf '%dm%02ds' $((secs / 60)) $((secs % 60))
  else
    printf '%ds' "$secs"
  fi
}

if [[ -f "$FUZZ_FILL/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$FUZZ_FILL/venv/bin/activate"
fi

if ! command -v python >/dev/null 2>&1; then
  echo "error: python not found (create venv and pip install -e .)" >&2
  exit 1
fi

if [[ ! -d "$CORPUS" ]]; then
  echo "error: corpus directory not found: $CORPUS" >&2
  exit 1
fi

require_bin "$LLVM_BIN" sancov
require_bin "$INSTRUMENTED_BIN" llvm-lit
require_bin "$INSTRUMENTED_BIN" llc
require_bin "$INSTRUMENTED_BIN" opt

cd "$FUZZ_FILL"

case "${REFRESH:-}" in
  all)
    rm -rf "$TEST_SUITE_OUTPUT_DIR" "$NEW_TESTS_OUTPUT_DIR" "$DIFF_OUTPUT_DIR"
    ;;
  suite|test_suite)
    rm -rf "$TEST_SUITE_OUTPUT_DIR"
    ;;
  corpus|new_tests)
    rm -rf "$NEW_TESTS_OUTPUT_DIR"
    ;;
  diff)
    rm -rf "$DIFF_OUTPUT_DIR"
    ;;
  "")
    ;;
  *)
    echo "error: unknown REFRESH=$REFRESH (use all, suite, corpus, or diff)" >&2
    exit 1
    ;;
esac

mkdir -p "$OUTPUT_DIR"

echo "=== corpus vs LLVM test suite coverage ==="
echo "fuzz-fill:      $FUZZ_FILL"
echo "llvm-bin:       $LLVM_BIN"
echo "instrumented:   $INSTRUMENTED_BIN"
echo "corpus:         $CORPUS"
echo "corpus tests:   $CORPUS_N"
echo "lit filter:     $FILTER"
echo "source code filter: $SOURCE_CODE_FILTER"
echo "output:         $OUTPUT_DIR"
echo

TOTAL_START=$SECONDS
STEP1_ELAPSED="skipped"
STEP2_ELAPSED="skipped"
STEP3_ELAPSED="skipped"

if [[ -z "${SKIP_TEST_SUITE:-}" ]]; then
  echo ">>> Step 1/3: LIT test-suite baseline"
  step_start=$SECONDS
  python -m coverage baseline \
    --output-dir "$TEST_SUITE_OUTPUT_DIR" \
    --sancov "$LLVM_BIN/sancov" \
    --llvm-lit "$INSTRUMENTED_BIN/llvm-lit" \
    --llc "$INSTRUMENTED_BIN/llc" \
    --opt "$INSTRUMENTED_BIN/opt" \
    --lit-filter "$FILTER" \
    --source-code-filter "$SOURCE_CODE_FILTER"
  STEP1_ELAPSED="$(format_duration $((SECONDS - step_start)))"
  echo "    finished in $STEP1_ELAPSED"
else
  echo ">>> Step 1/3: skipped (SKIP_TEST_SUITE=1)"
fi

if [[ -z "${SKIP_NEW_TESTS:-}" ]]; then
  echo ">>> Step 2/3: corpus candidate-test"
  step_start=$SECONDS
  python -m coverage candidate-test \
    --output-dir "$NEW_TESTS_OUTPUT_DIR" \
    --llc "$INSTRUMENTED_BIN/llc" \
    --candidate-tests-dir "$CORPUS" \
    --n "$CORPUS_N"
  STEP2_ELAPSED="$(format_duration $((SECONDS - step_start)))"
  echo "    finished in $STEP2_ELAPSED"
else
  echo ">>> Step 2/3: skipped (SKIP_NEW_TESTS=1)"
fi

if [[ -z "${SKIP_DIFF:-}" ]]; then
  echo ">>> Step 3/3: incremental coverage"
  step_start=$SECONDS
  python -m coverage incremental \
    --output-dir "$DIFF_OUTPUT_DIR" \
    --sancov "$LLVM_BIN/sancov" \
    --line-coverage-uncovered-csv "$TEST_SUITE_OUTPUT_DIR/line_coverage_uncovered.csv" \
    --llc-address-line-map-csv "$TEST_SUITE_OUTPUT_DIR/llc_address_line_map.csv" \
    --candidate-tests-output-dir "$NEW_TESTS_OUTPUT_DIR"
  STEP3_ELAPSED="$(format_duration $((SECONDS - step_start)))"
  echo "    finished in $STEP3_ELAPSED"
else
  echo ">>> Step 3/3: skipped (SKIP_DIFF=1)"
fi

TOTAL_ELAPSED="$(format_duration $((SECONDS - TOTAL_START)))"
echo
echo "Timing:"
echo "  step 1 (test-suite): $STEP1_ELAPSED"
echo "  step 2 (new-tests):  $STEP2_ELAPSED"
echo "  step 3 (diff):       $STEP3_ELAPSED"
echo "  total:               $TOTAL_ELAPSED"

echo
if [[ -f "$NEW_COVERAGE_CSV" ]]; then
  rows="$(($(wc -l < "$NEW_COVERAGE_CSV") - 1))"
  echo "Incremental coverage rows: $rows"
  echo "Result CSV: $NEW_COVERAGE_CSV"
  if [[ "$rows" -gt 0 ]]; then
    echo
    echo "First 10 rows:"
    head -11 "$NEW_COVERAGE_CSV"
  fi
else
  echo "warning: expected result not found: $NEW_COVERAGE_CSV" >&2
fi
