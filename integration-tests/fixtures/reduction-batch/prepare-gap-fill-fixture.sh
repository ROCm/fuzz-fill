#!/usr/bin/env bash
# Build a minimal gap-fill output tree under DEST for reduction-batch lit tests.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $(basename "$0") <dest-gap-fill-dir>" >&2
    exit 2
fi

dest="$1"
fixture_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "${dest}/incremental" "${dest}/candidate_tests" "${dest}/fake-llvm/bin"
cp "${fixture_dir}/new_coverage.csv" "${dest}/incremental/"

fake_llc="${dest}/fake-llvm/bin/llc"
printf '#!/bin/sh\n' >"${fake_llc}"
chmod +x "${fake_llc}"

for name in test-a test-b test-c; do
    test_dir="${dest}/candidate_tests/${name}"
    mkdir -p "${test_dir}"
    cp "${fixture_dir}/sample.bc" "${test_dir}/sample.bc"
    cat >"${test_dir}/test.sh" <<EOF
#!/bin/bash
${fake_llc} -O1 -mtriple=amdgcn-amd-amdhsa ${test_dir}/sample.bc
EOF
    chmod +x "${test_dir}/test.sh"
done
