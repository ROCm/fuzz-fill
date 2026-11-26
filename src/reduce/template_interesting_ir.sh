#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LLVM_BIN="${LLVM_BIN:-${REPO_ROOT}/../llvm-project/build-amdgpu-bb/bin}"

LLC=$LLVM_BIN/llc
SANCOV=$LLVM_BIN/sancov

# Space-separated 0x-prefixed instrumentation points for the target line.
# Interesting only if every point appears in sancov --print (full-line coverage).
COVERED="0x61d4b9a"

covdir=$(mktemp -d)
before_tmp=$(mktemp)
after_tmp=$(mktemp)
print_tmp=$(mktemp)
trap 'rm -f "$before_tmp" "$after_tmp" "$print_tmp"; rm -rf "$covdir"' EXIT
find "$covdir" -maxdepth 1 -name 'llc.*.sancov' -type f 2>/dev/null | sort >"$before_tmp"

UBSAN_OPTIONS="coverage=1:coverage_dir=$covdir:print_coverage_summary=0" $LLC "$1"

find "$covdir" -maxdepth 1 -name 'llc.*.sancov' -type f 2>/dev/null | sort >"$after_tmp"

sancov_file=$(comm -13 "$before_tmp" "$after_tmp" | head -n1)
if [[ -z "$sancov_file" ]]; then
  sancov_file=$(find "$covdir" -maxdepth 1 -name 'llc.*.sancov' -type f -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2-)
fi

if [[ -z "$sancov_file" || ! -f "$sancov_file" ]]; then
  echo "No llc.*.sancov found under $covdir after llc run." >&2
  exit 1
fi
if [[ ! -x "$SANCOV" ]]; then
  echo "sancov not executable at $SANCOV" >&2
  exit 1
fi

"$SANCOV" --print "$sancov_file" >"$print_tmp"

missing=0
for point in $COVERED; do
  if grep -qF "$point" "$print_tmp"; then
    echo "COVERED point $point is present in sancov --print ($sancov_file)." >&2
  else
    echo "COVERED point $point is NOT present in sancov --print ($sancov_file)." >&2
    missing=1
  fi
done

# Interesting: every COVERED point appears in sancov --print.
if [[ "$missing" -eq 0 ]]; then
  exit 0
fi

exit 1
