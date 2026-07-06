#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
LLVM_BIN="${LLVM_BIN:-${REPO_ROOT}/../llvm-project/build-amdgpu-bb/bin}"

LLC=$LLVM_BIN/llc
SANCOV=$LLVM_BIN/sancov

COVERED="0x61d4b9a"

covdir=$(mktemp -d)
before_tmp=$(mktemp)
after_tmp=$(mktemp)
trap 'rm -f "$before_tmp" "$after_tmp"; rm -rf "$covdir"' EXIT
find "$covdir" -maxdepth 1 -name 'llc.*.sancov' -type f 2>/dev/null | sort >"$before_tmp"

UBSAN_OPTIONS="coverage=1:coverage_dir=$covdir" $LLC "$1"

find "$covdir" -maxdepth 1 -name 'llc.*.sancov' -type f 2>/dev/null | sort >"$after_tmp"

sancov_file=$(comm -13 "$before_tmp" "$after_tmp" | head -n1)
if [[ -z "$sancov_file" ]]; then
  sancov_file=$(find "$covdir" -maxdepth 1 -name 'llc.*.sancov' -type f -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2-)
fi

covered_present=0
if [[ -z "$sancov_file" || ! -f "$sancov_file" ]]; then
  echo "No llc.*.sancov found under $covdir after llc run." >&2
elif [[ ! -x "$SANCOV" ]]; then
  echo "sancov not executable at $SANCOV" >&2
elif "$SANCOV" --print "$sancov_file" | grep -qF "$COVERED"; then
  covered_present=1
  echo "COVERED ($COVERED) is present in sancov --print output ($sancov_file)." >&2
else
  echo "COVERED ($COVERED) is NOT present in sancov --print output ($sancov_file)." >&2
fi

# Interesting: COVERED appears in sancov --print.
if [[ "$covered_present" -eq 1 ]]; then
  exit 0
fi

# Not interesting: COVERED missing, or no .sancov / no sancov binary.
exit 1
