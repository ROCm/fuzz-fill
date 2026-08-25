#!/usr/bin/env bash
# Run one agent candidate through instrumented llc and check sancov gap point hits.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

pr_id=""
file=""
line=""
llc_map_csv=""
test_path=""
llc_flags=""
mode="docker"
sancov_bin=""
llc_bin=""

usage() {
    cat <<EOF
Usage: $(basename "$0") \\
  --pr-id <n> --file <abs-path> --line <n> \\
  --llc-map-csv <path> --test <path> --llc-flags "<flags>" \\
  [--local --llc <path> --sancov <path>] [--bind-repo]

Exit codes: 0=HIT, 1=MISS/invalid llc run, 2=error

llc must exit 0 (no crash, parse error, or timeout) before coverage is
checked. A gap hit from a crashing llc is not accepted.

Default mode runs llc inside fuzz-fill-test:llvm-pr-<n> Docker image.
EOF
}

bind_repo=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr-id)
            pr_id="$2"
            shift 2
            ;;
        --file)
            file="$2"
            shift 2
            ;;
        --line)
            line="$2"
            shift 2
            ;;
        --llc-map-csv)
            llc_map_csv="$2"
            shift 2
            ;;
        --test)
            test_path="$2"
            shift 2
            ;;
        --llc-flags)
            llc_flags="$2"
            shift 2
            ;;
        --local)
            mode="local"
            shift
            ;;
        --llc)
            llc_bin="$2"
            shift 2
            ;;
        --sancov)
            sancov_bin="$2"
            shift 2
            ;;
        --bind-repo)
            bind_repo=1
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

for req in pr_id file line llc_map_csv test_path llc_flags; do
    if [[ -z "${!req}" ]]; then
        echo "error: --${req//_/-} is required" >&2
        usage >&2
        exit 2
    fi
done

if [[ ! -f "$test_path" ]]; then
    echo "error: test file not found: ${test_path}" >&2
    exit 2
fi
if [[ ! -f "$llc_map_csv" ]]; then
    echo "error: llc map not found: ${llc_map_csv}" >&2
    exit 2
fi

test_path="$(realpath "$test_path")"
llc_map_csv="$(realpath "$llc_map_csv")"
work_dir="$(mktemp -d -t fuzz-fill-agent-verify.XXXXXX)"
cleanup() {
    rm -rf "$work_dir"
}
trap cleanup EXIT

LLC_TIMEOUT_SEC="${LLC_TIMEOUT_SEC:-30}"

report_llc_failure() {
    local status="$1"
    if [[ "$status" -eq 124 ]]; then
        echo "INVALID: llc timed out after ${LLC_TIMEOUT_SEC}s" >&2
    elif [[ "$status" -ge 128 ]]; then
        echo "INVALID: llc crashed (signal $((status - 128)), exit ${status})" >&2
    else
        echo "INVALID: llc exited ${status} (IR rejected or compile error)" >&2
    fi
}

run_local() {
    if [[ -z "$llc_bin" || -z "$sancov_bin" ]]; then
        echo "error: --local requires --llc and --sancov" >&2
        exit 2
    fi
    export UBSAN_OPTIONS="coverage=1:coverage_dir=${work_dir}"
    set +e
    # shellcheck disable=SC2086
    timeout "$LLC_TIMEOUT_SEC" "$llc_bin" $llc_flags "$test_path" -o /dev/null
    llc_status=$?
    set -e
    if [[ "$llc_status" -ne 0 ]]; then
        report_llc_failure "$llc_status"
        exit 1
    fi
    shopt -s nullglob
    sancov_files=("$work_dir"/*.sancov)
    if [[ ${#sancov_files[@]} -eq 0 ]]; then
        echo "MISS: llc produced no sancov files" >&2
        exit 1
    fi
    cd "$REPO_ROOT"
    PYTHONPATH=src python3 "${SCRIPT_DIR}/gap_fill_agent.py" check-hit \
        --llc-map-csv "$llc_map_csv" \
        --file "$file" \
        --line "$line" \
        --sancov-file "${sancov_files[0]}" \
        --sancov "$sancov_bin"
}

run_docker() {
    image="fuzz-fill-test:llvm-pr-${pr_id}"
    if ! docker image inspect "$image" >/dev/null 2>&1; then
        echo "error: Docker image not found: ${image}" >&2
        echo "Build via pr-check or scripts/docker/build-image-pr.sh" >&2
        exit 2
    fi

    mount_args=(
        -v "${test_path}:/mounted/test/input.ll:ro"
        -v "${llc_map_csv}:/mounted/map.csv:ro"
        -v "${work_dir}:/mounted/out"
        -v "${REPO_ROOT}:/work/fuzz-fill"
    )

    docker run --rm "${mount_args[@]}" -w /work/fuzz-fill "$image" bash -lc "
set -euo pipefail
OUT=/mounted/out
export UBSAN_OPTIONS=\"coverage=1:coverage_dir=\${OUT}\"
export LLC_FLAGS=$(printf '%q' "$llc_flags")
export LLC_TIMEOUT_SEC=${LLC_TIMEOUT_SEC}
set +e
timeout \"\${LLC_TIMEOUT_SEC}\" /work/llvm-build-sancov/bin/llc \${LLC_FLAGS} /mounted/test/input.ll -o /dev/null
llc_status=\$?
set -e
if [[ \"\${llc_status}\" -ne 0 ]]; then
  if [[ \"\${llc_status}\" -eq 124 ]]; then
    echo \"INVALID: llc timed out after \${LLC_TIMEOUT_SEC}s\" >&2
  elif [[ \"\${llc_status}\" -ge 128 ]]; then
    echo \"INVALID: llc crashed (signal \$((llc_status - 128)), exit \${llc_status})\" >&2
  else
    echo \"INVALID: llc exited \${llc_status} (IR rejected or compile error)\" >&2
  fi
  exit 1
fi
SANCOV=\$(find /mounted/out -name '*.sancov' | head -1 || true)
if [[ -z \"\${SANCOV}\" ]]; then
  echo 'MISS: llc produced no sancov files' >&2
  exit 1
fi
python3 scripts/gap_fill_agent.py check-hit \\
  --llc-map-csv /mounted/map.csv \\
  --file $(printf '%q' "$file") \\
  --line ${line} \\
  --sancov-file \"\${SANCOV}\" \\
  --sancov /work/llvm-build-sancov/bin/sancov
"
}

if [[ "$mode" == "local" ]]; then
    run_local
else
    run_docker
fi
