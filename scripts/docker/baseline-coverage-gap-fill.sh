#!/usr/bin/env bash
# Run Workflow 1 (baseline coverage gap fill) inside a one-shot Docker container:
#   baseline  ->  candidate-test  ->  incremental
#
# Host output is bind-mounted at /mounted-output/. Candidate tests are staged on
# the host at run time (first N .ll/.bc files only) and bind-mounted read-only
# at /mounted-candidate-tests — nothing is baked into the image.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONTAINER_WORKDIR="/work/fuzz-fill"

image_name="${IMAGE_NAME:-fuzz-fill-test}"
image_tag="${IMAGE_TAG:-latest}"
image_ref=""
output_dir=""
lit_filter=""
jobs=""
baseline_only=0
bind_repo=0
candidate_tests_dir=""
candidate_n=""

usage() {
    cat <<EOF
Usage: $(basename "$0") --output-dir <path> [options]

Run Workflow 1 coverage gap fill in a temporary container.
Artifacts are written under --output-dir (mounted at /mounted-output/).

Required:
  --output-dir <path>           Host output directory (created if missing)

Modes (pick one):
  --baseline-only               Run only coverage baseline (no candidate corpus)
  --candidate-tests-dir <path>  Host corpus root; with -n, runs the full pipeline
  -n <N>, --n <N>               Stage and run only the first N candidate tests

Options:
  --image <ref>                 Docker image ref (default: \${IMAGE_NAME:-fuzz-fill-test}:\${IMAGE_TAG:-latest})
  --bind-repo                   Mount the local fuzz-fill checkout at ${CONTAINER_WORKDIR}
  --lit-filter <prefix>         LIT --filter= prefix (default: from image /work/.sancov-allowlist)
  -j <n>, --jobs <n>            Parallel jobs for llvm-lit and candidate-test
  --help, -h                    Show this help

Examples:
  $(basename "$0") --baseline-only --output-dir ./data/wf1-baseline -j "\$(nproc)"
  $(basename "$0") --bind-repo --baseline-only --output-dir ./data/wf1-baseline -j "\$(nproc)"
  $(basename "$0") --output-dir ./data/wf1-100 \\
      --candidate-tests-dir /path/to/irtests/bitcode/amdgpu/all -n 100 -j "\$(nproc)"
EOF
}

lit_filter_for_allowlist() {
    case "$1" in
        amdgpu) echo "CodeGen/AMDGPU" ;;
        spirv) echo "CodeGen/SPIRV" ;;
        *)
            echo "error: unsupported image allowlist: ${1} (expected amdgpu or spirv)" >&2
            exit 1
            ;;
    esac
}

validate_jobs() {
    if [[ -n "$jobs" ]] && { [[ ! "$jobs" =~ ^[0-9]+$ ]] || [[ "$jobs" -eq 0 ]]; }; then
        echo "error: -j/--jobs must be a positive integer: ${jobs}" >&2
        exit 1
    fi
}

validate_candidate_n() {
    if [[ ! "$candidate_n" =~ ^[0-9]+$ ]] || [[ "$candidate_n" -eq 0 ]]; then
        echo "error: -n/--n must be a positive integer: ${candidate_n}" >&2
        exit 1
    fi
}

read_image_allowlist() {
    local allowlist
    if ! allowlist="$(docker run --rm --entrypoint cat "${image_ref}" /work/.sancov-allowlist 2>/dev/null | tr -d '[:space:]')"; then
        echo "error: failed to read /work/.sancov-allowlist from image: ${image_ref}" >&2
        exit 1
    fi
    if [[ -z "$allowlist" ]]; then
        echo "error: /work/.sancov-allowlist is empty in image: ${image_ref}" >&2
        exit 1
    fi
    printf '%s' "$allowlist"
}

# Enumerate .ll/.bc under src (recursive), sorted — matches TestRunner.collect_llc_input_files().
collect_candidate_inputs() {
    local src="$1"
    find "$src" -type f \( -name '*.ll' -o -name '*.bc' \) | LC_ALL=C sort
}

# Copy the first n candidate inputs into staging_dir, preserving relative paths.
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

    count="$n"
    if [[ "${#candidate_files[@]}" -lt "$count" ]]; then
        count="${#candidate_files[@]}"
        echo "note: corpus has ${#candidate_files[@]} file(s); staging all of them (requested ${n})"
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

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image)
            [[ $# -ge 2 ]] || { echo "error: --image requires a value" >&2; exit 2; }
            image_ref="$2"
            shift 2
            ;;
        --output-dir)
            [[ $# -ge 2 ]] || { echo "error: --output-dir requires a value" >&2; exit 2; }
            output_dir="$2"
            shift 2
            ;;
        --lit-filter)
            [[ $# -ge 2 ]] || { echo "error: --lit-filter requires a value" >&2; exit 2; }
            lit_filter="$2"
            shift 2
            ;;
        --baseline-only)
            baseline_only=1
            shift
            ;;
        --bind-repo)
            bind_repo=1
            shift
            ;;
        --candidate-tests-dir)
            [[ $# -ge 2 ]] || { echo "error: --candidate-tests-dir requires a value" >&2; exit 2; }
            candidate_tests_dir="$2"
            shift 2
            ;;
        -n|--n)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            candidate_n="$2"
            shift 2
            ;;
        -j|--jobs)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            jobs="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            echo "error: unexpected argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ $# -gt 0 ]]; then
    echo "error: unexpected argument: $1" >&2
    usage >&2
    exit 2
fi

if [[ -z "$output_dir" ]]; then
    echo "error: --output-dir is required" >&2
    usage >&2
    exit 1
fi

if [[ "$baseline_only" -eq 1 ]]; then
    if [[ -n "$candidate_tests_dir" || -n "$candidate_n" ]]; then
        echo "error: --candidate-tests-dir and -n cannot be used with --baseline-only" >&2
        exit 1
    fi
else
    if [[ -z "$candidate_tests_dir" || -z "$candidate_n" ]]; then
        echo "error: full pipeline requires --candidate-tests-dir and -n (or pass --baseline-only)" >&2
        usage >&2
        exit 1
    fi
    validate_candidate_n
    if [[ ! -d "$candidate_tests_dir" ]]; then
        echo "error: --candidate-tests-dir is not a directory: ${candidate_tests_dir}" >&2
        exit 1
    fi
fi

validate_jobs

if [[ -z "$image_ref" ]]; then
    image_ref="${image_name}:${image_tag}"
fi

if ! docker image inspect "${image_ref}" >/dev/null 2>&1; then
    echo "error: image not found: ${image_ref}" >&2
    echo "hint: build it with: ${SCRIPT_DIR}/build-image.sh" >&2
    exit 1
fi

if [[ -z "$lit_filter" ]]; then
    image_allowlist="$(read_image_allowlist)"
    lit_filter="$(lit_filter_for_allowlist "$image_allowlist")"
    echo "Image allowlist: ${image_allowlist} -> lit-filter: ${lit_filter}"
fi

mkdir -p "$output_dir"
output_dir="$(realpath "$output_dir")"

candidate_staging_dir=""
candidate_mount=()
if [[ "$baseline_only" -eq 0 ]]; then
    candidate_staging_dir="$(mktemp -d -t fuzz-fill-candidate-tests.XXXXXX)"
    cleanup_staging() {
        rm -rf "${candidate_staging_dir}"
    }
    trap cleanup_staging EXIT
    stage_candidate_tests "$candidate_tests_dir" "$candidate_n" "$candidate_staging_dir"
    candidate_mount=(-v "${candidate_staging_dir}:/mounted-candidate-tests:ro")
fi

rm -rf "${output_dir}/baseline"
if [[ "$baseline_only" -eq 0 ]]; then
    rm -rf "${output_dir}/candidate_tests" "${output_dir}/incremental"
fi

docker_env=(
    -e "LIT_FILTER=${lit_filter}"
    -e "BASELINE_ONLY=${baseline_only}"
)
if [[ -n "$jobs" ]]; then
    docker_env+=(-e "JOBS=${jobs}")
fi
if [[ "$baseline_only" -eq 0 ]]; then
    docker_env+=(-e "CANDIDATE_N=${candidate_n}")
fi

repo_mount=()
if [[ "${bind_repo}" -eq 1 ]]; then
    repo_mount=(-v "${REPO_ROOT}:${CONTAINER_WORKDIR}")
    echo "Using local fuzz-fill checkout: ${REPO_ROOT}"
fi

docker run --rm \
    -v "${output_dir}:/mounted-output" \
    "${candidate_mount[@]}" \
    "${repo_mount[@]}" \
    "${docker_env[@]}" \
    -w "${CONTAINER_WORKDIR}" \
    "${image_ref}" \
    bash -lc '
set -euo pipefail

baseline_args=(
    python -m coverage baseline
    --output-dir /mounted-output/baseline
    --lit-filter "${LIT_FILTER}"
    --lit-allow-failures
)
if [[ -n "${JOBS:-}" ]]; then
    baseline_args+=(-j "${JOBS}")
fi

echo "=== coverage baseline (lit-filter=${LIT_FILTER}) ==="
"${baseline_args[@]}"

if [[ "${BASELINE_ONLY}" -ne 1 ]]; then
    candidate_args=(
        python -m coverage candidate-test
        --output-dir /mounted-output/candidate_tests
        --candidate-tests-dir /mounted-candidate-tests
        --n "${CANDIDATE_N}"
    )
    if [[ -n "${JOBS:-}" ]]; then
        candidate_args+=(-j "${JOBS}")
    fi

    echo "=== coverage candidate-test (n=${CANDIDATE_N}) ==="
    "${candidate_args[@]}"

    echo "=== coverage incremental ==="
    python -m coverage incremental \
        --output-dir /mounted-output/incremental \
        --baseline-output-dir /mounted-output/baseline \
        --candidate-tests-output-dir /mounted-output/candidate_tests
fi
'

echo "Image: ${image_ref}"
echo "LIT filter: ${lit_filter}"

if [[ "$baseline_only" -eq 1 ]]; then
    echo "Wrote ${output_dir}/baseline/"
else
    report="${output_dir}/incremental/new_coverage.csv"
    echo "Wrote ${report}"
fi

lit_failures_json="${output_dir}/baseline/lit_failures.json"
warning_file="${output_dir}/README-WARNING"

fail_count=0
if [[ -f "$lit_failures_json" ]]; then
    fail_count="$(python3 -c '
import json, sys
FAILURE_CODES = {"FAIL", "TIMEOUT", "UNRESOLVED", "XPASS"}
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    print(sum(1 for t in data.get("tests", []) if t.get("code") in FAILURE_CODES))
except Exception:
    print(0)
' "$lit_failures_json")"
fi

if [[ "$fail_count" -gt 0 ]]; then
    msg="WARNING: ${fail_count} LIT test(s) failed during the baseline run (e.g., failed a check, timed out, unresolved, or unexpectedly passed).
Failed tests may lead to an incomplete coverage profile. As a result,
new_coverage.csv may report lines as uncovered even though they are
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
