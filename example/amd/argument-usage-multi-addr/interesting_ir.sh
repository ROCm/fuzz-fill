#!/bin/bash
# Interesting iff llc (on candidate "$1") produces sancov whose `sancov --print`
# output contains every address listed in COVERED_LIST (semicolon-separated, same
# shape as new_coverage.csv "covered-points"). Row source:
# data/coverage_output/bb_coverage_270426/incremental/new_coverage.csv (AMDGPUArgumentUsageInfo.cpp:56).

LLVM_BIN=/home/agorzyns/local/dev/llvm-project/build-amdgpu-bb/bin

LLC=$LLVM_BIN/llc
SANCOV=$LLVM_BIN/sancov

# All of these must appear as substrings in `sancov --print` for the new llc.*.sancov shard.
COVERED_LIST="0x598701b;0x598703f"

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

if [[ -z "$sancov_file" || ! -f "$sancov_file" ]]; then
  echo "No llc.*.sancov found under $covdir after llc run." >&2
  exit 1
fi
if [[ ! -x "$SANCOV" ]]; then
  echo "sancov not executable at $SANCOV" >&2
  exit 1
fi

print_output=$("$SANCOV" --print "$sancov_file" 2>/dev/null) || print_output=""

all_present=1
missing=()
IFS=';' read -ra ADDRS <<<"$COVERED_LIST"
for a in "${ADDRS[@]}"; do
  a="${a//[[:space:]]/}"
  [[ -z "$a" ]] && continue
  if ! grep -qF "$a" <<<"$print_output"; then
    all_present=0
    missing+=("$a")
  fi
done

if [[ "$all_present" -eq 1 ]]; then
  echo "All covered addresses present in sancov --print ($sancov_file): $COVERED_LIST" >&2
  exit 0
fi

echo "Not all covered addresses in sancov --print ($sancov_file); missing: ${missing[*]}" >&2
exit 1
