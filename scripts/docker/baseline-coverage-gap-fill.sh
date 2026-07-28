#!/usr/bin/env bash
# Run Workflow 1 (baseline coverage gap fill) inside a one-shot Docker container:
#   baseline  ->  candidate-test  ->  incremental
#
# Host output is bind-mounted at /mounted-output/. Candidate tests are staged on
# the host at run time (first N .ll/.bc files only) and bind-mounted read-only
# at /mounted-candidate-tests — nothing is baked into the image.
#
# The coverage profile (line_coverage_uncovered.csv + llc_address_line_map.csv)
# can come from a baseline run in this invocation, from a prior Workflow 1 run,
# or from the baseline/ output of a Workflow 2 PR detection run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONTAINER_WORKDIR="/work/fuzz-fill"

image_name="${IMAGE_NAME:-fuzz-fill-test}"
image_tag="${IMAGE_TAG:-latest}"
image_ref=""
pr_id=""
output_dir=""
baseline_dir=""
line_coverage_uncovered_csv=""
lit_filter=""
jobs=""
baseline_only=0
bind_repo=0
candidate_tests_dir=""
candidate_n=""
build_image=0
keep_image=0
llvm_repo=""
backend_tests=""
github_repo=""

usage() {
    cat <<EOF
Usage: $(basename "$0") --output-dir <path> [options]

Run Workflow 1 coverage gap fill in a temporary container.
Artifacts are written under --output-dir (mounted at /mounted-output/).

Required:
  --output-dir <path>           Host output directory (created if missing)

Modes (pick one):
  --baseline-only               Run only coverage baseline (no candidate corpus)
  --candidate-tests-dir <path>  Host corpus root; with -n, runs candidate-test + incremental
  -n <N>, --n <N>               Stage and run only the first N candidate tests

Coverage profile (for candidate-test + incremental):
  By default, baseline runs in this invocation and writes to <output-dir>/baseline/.
  Re-use an existing profile instead (from Workflow 1 baseline-only or Workflow 2):
  --baseline-dir <path>         Host directory with line_coverage_uncovered.csv and
                                llc_address_line_map.csv (mounted read-only)
  --line-coverage-uncovered-csv <path>
                                Override uncovered-lines CSV (default:
                                <baseline-dir>/line_coverage_uncovered.csv or output baseline)

Image (one of):
  --image <ref>                 Docker image ref (default: \${IMAGE_NAME:-fuzz-fill-test}:\${IMAGE_TAG:-latest})
  --pr-id <n>                   Use \${IMAGE_NAME:-fuzz-fill-test}:llvm-pr-<n>

Image build (optional; reuses existing image when omitted):
  --build-image                 Build PR image via build-image-pr.sh before running
  --keep-image                  Keep PR image after run (default: remove when --build-image)
  --llvm-repo <path>            Local llvm-project clone (required with --build-image)
  --backend-tests <target>      amdgpu or spirv (required with --build-image)
  --github-repo <owner/repo>    GitHub repo hosting the PR (default: llvm/llvm-project)
  --image-name <name>           Image name when using --pr-id (default: fuzz-fill-test)

Options:
  --bind-repo                   Mount the local fuzz-fill checkout at ${CONTAINER_WORKDIR}
  --lit-filter <prefix>         LIT --filter= prefix (default: from image /work/.sancov-allowlist)
  -j <n>, --jobs <n>            Parallel jobs for llvm-lit, candidate-test, and ninja (build)
  --help, -h                    Show this help

Examples:
  $(basename "$0") --baseline-only --output-dir ./data/wf1-baseline -j "\$(nproc)"
  $(basename "$0") --pr-id 203468 --output-dir ./data/wf1-pr-baseline --baseline-only -j "\$(nproc)"
  $(basename "$0") --build-image --llvm-repo /path/llvm-project --pr-id 203468 \\
      --backend-tests amdgpu --baseline-only --output-dir ./data/wf1-pr-baseline -j "\$(nproc)"
  $(basename "$0") --output-dir ./data/wf1-100 \\
      --baseline-dir ./data/pr-cov-gaps-203468/baseline \\
      --candidate-tests-dir /path/to/irtests/bitcode/amdgpu/all -n 100 -j "\$(nproc)"
  $(basename "$0") --pr-id 203468 --output-dir ./data/wf1-pr-100 \\
      --baseline-dir ./data/pr-cov-gaps-203468/baseline \\
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

cleanup_built_image() {
    if [[ "${build_image:-0}" -eq 1 && "${keep_image:-0}" -eq 0 && -n "${image_ref:-}" ]]; then
        if docker image inspect "${image_ref}" >/dev/null 2>&1; then
            echo "Removing Docker image ${image_ref}"
            docker rmi "${image_ref}"
        fi
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

validate_baseline_profile_dir() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        echo "error: --baseline-dir is not a directory: ${dir}" >&2
        exit 1
    fi
    if [[ ! -f "${dir}/llc_address_line_map.csv" ]]; then
        echo "error: missing llc_address_line_map.csv under --baseline-dir: ${dir}" >&2
        exit 1
    fi
}

resolve_uncovered_csv_path() {
    local profile_dir="$1"
    if [[ -n "$line_coverage_uncovered_csv" ]]; then
        if [[ ! -f "$line_coverage_uncovered_csv" ]]; then
            echo "error: --line-coverage-uncovered-csv not found: ${line_coverage_uncovered_csv}" >&2
            exit 1
        fi
        realpath "$line_coverage_uncovered_csv"
    elif [[ -n "$profile_dir" ]]; then
        if [[ ! -f "${profile_dir}/line_coverage_uncovered.csv" ]]; then
            echo "error: missing line_coverage_uncovered.csv under --baseline-dir: ${profile_dir}" >&2
            exit 1
        fi
        realpath "${profile_dir}/line_coverage_uncovered.csv"
    else
        echo ""
    fi
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
        --pr-id)
            [[ $# -ge 2 ]] || { echo "error: --pr-id requires a value" >&2; exit 2; }
            pr_id="$2"
            shift 2
            ;;
        --output-dir)
            [[ $# -ge 2 ]] || { echo "error: --output-dir requires a value" >&2; exit 2; }
            output_dir="$2"
            shift 2
            ;;
        --baseline-dir)
            [[ $# -ge 2 ]] || { echo "error: --baseline-dir requires a value" >&2; exit 2; }
            baseline_dir="$2"
            shift 2
            ;;
        --line-coverage-uncovered-csv)
            [[ $# -ge 2 ]] || { echo "error: --line-coverage-uncovered-csv requires a value" >&2; exit 2; }
            line_coverage_uncovered_csv="$2"
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
        --build-image)
            build_image=1
            shift
            ;;
        --keep-image)
            keep_image=1
            shift
            ;;
        --llvm-repo)
            [[ $# -ge 2 ]] || { echo "error: --llvm-repo requires a value" >&2; exit 2; }
            llvm_repo="$2"
            shift 2
            ;;
        --backend-tests)
            [[ $# -ge 2 ]] || { echo "error: --backend-tests requires a value" >&2; exit 2; }
            backend_tests="$2"
            shift 2
            ;;
        --github-repo)
            [[ $# -ge 2 ]] || { echo "error: --github-repo requires a value" >&2; exit 2; }
            github_repo="$2"
            shift 2
            ;;
        --image-name)
            [[ $# -ge 2 ]] || { echo "error: --image-name requires a value" >&2; exit 2; }
            image_name="$2"
            shift 2
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

if [[ -n "$image_ref" && -n "$pr_id" ]]; then
    echo "error: pass only one of --image or --pr-id" >&2
    exit 1
fi

if [[ -n "$image_ref" && "$build_image" -eq 1 ]]; then
    echo "error: --build-image cannot be used with --image" >&2
    exit 1
fi

if [[ "$build_image" -eq 0 ]]; then
    if [[ -n "$llvm_repo" || -n "$backend_tests" || -n "$github_repo" || "$keep_image" -eq 1 ]]; then
        echo "error: --llvm-repo, --backend-tests, --github-repo, and --keep-image require --build-image" >&2
        exit 1
    fi
else
    if [[ -z "$llvm_repo" ]]; then
        echo "error: --llvm-repo is required with --build-image" >&2
        exit 1
    fi
    if [[ -z "$pr_id" ]]; then
        echo "error: --pr-id is required with --build-image" >&2
        exit 1
    fi
    if [[ -z "$backend_tests" ]]; then
        echo "error: --backend-tests is required with --build-image" >&2
        exit 1
    fi
fi

if [[ -n "$backend_tests" ]]; then
    backend_tests="$(printf '%s' "$backend_tests" | tr '[:upper:]' '[:lower:]')"
    case "$backend_tests" in
        amdgpu|spirv) ;;
        *)
            echo "error: --backend-tests must be amdgpu or spirv: ${backend_tests}" >&2
            exit 1
            ;;
    esac
fi

if [[ -n "$pr_id" ]]; then
    if [[ ! "$pr_id" =~ ^[0-9]+$ ]] || [[ "$pr_id" -eq 0 ]]; then
        echo "error: --pr-id must be a positive integer: ${pr_id}" >&2
        exit 1
    fi
    image_ref="${image_name}:llvm-pr-${pr_id}"
fi

if [[ "$baseline_only" -eq 1 ]]; then
    if [[ -n "$candidate_tests_dir" || -n "$candidate_n" ]]; then
        echo "error: --candidate-tests-dir and -n cannot be used with --baseline-only" >&2
        exit 1
    fi
    if [[ -n "$baseline_dir" || -n "$line_coverage_uncovered_csv" ]]; then
        echo "error: --baseline-dir and --line-coverage-uncovered-csv cannot be used with --baseline-only" >&2
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
    if [[ -n "$line_coverage_uncovered_csv" && -z "$baseline_dir" ]]; then
        echo "error: --line-coverage-uncovered-csv requires --baseline-dir (for llc_address_line_map.csv)" >&2
        exit 1
    fi
fi

validate_jobs

if [[ -z "$image_ref" ]]; then
    image_ref="${image_name}:${image_tag}"
fi

if [[ "$build_image" -eq 1 && "$keep_image" -eq 0 ]]; then
    trap cleanup_built_image EXIT
fi

if [[ "$build_image" -eq 1 ]]; then
    build_args=(
        --llvm-repo "$llvm_repo"
        --pr-id "$pr_id"
        --allowlist "$backend_tests"
    )
    if [[ -n "$github_repo" ]]; then
        build_args+=(--github-repo "$github_repo")
    fi
    if [[ -n "$jobs" ]]; then
        build_args+=(-j "$jobs")
    fi

    echo "=== build PR image ==="
    "${SCRIPT_DIR}/build-image-pr.sh" "${build_args[@]}"
fi

if ! docker image inspect "${image_ref}" >/dev/null 2>&1; then
    echo "error: image not found: ${image_ref}" >&2
    if [[ "$build_image" -eq 0 ]]; then
        echo "hint: build with ${SCRIPT_DIR}/build-image.sh, or pass --build-image with --llvm-repo and --backend-tests" >&2
    fi
    exit 1
fi

skip_baseline=0
baseline_profile_dir=""
uncovered_csv_host=""
llc_map_host=""
uncovered_mount=()
baseline_mount=()

if [[ -n "$baseline_dir" ]]; then
    skip_baseline=1
    validate_baseline_profile_dir "$baseline_dir"
    baseline_profile_dir="$(realpath "$baseline_dir")"
    uncovered_csv_host="$(resolve_uncovered_csv_path "$baseline_profile_dir")"
    llc_map_host="${baseline_profile_dir}/llc_address_line_map.csv"
    baseline_mount=(-v "${baseline_profile_dir}:/mounted-baseline:ro")

    baseline_dir_real="$(realpath "$(dirname "$uncovered_csv_host")")"
    if [[ "$baseline_dir_real" == "$baseline_profile_dir" ]]; then
        container_uncovered_csv="/mounted-baseline/$(basename "$uncovered_csv_host")"
        container_llc_map_csv="/mounted-baseline/llc_address_line_map.csv"
    else
        container_uncovered_csv="/mounted-uncovered-lines.csv"
        uncovered_mount=(-v "${uncovered_csv_host}:${container_uncovered_csv}:ro")
        container_llc_map_csv="/mounted-baseline/llc_address_line_map.csv"
    fi

    echo "Using external coverage profile: ${baseline_profile_dir}"
    echo "  uncovered lines: ${uncovered_csv_host}"
    echo "  address map:     ${llc_map_host}"
elif [[ "$baseline_only" -eq 0 ]]; then
    container_uncovered_csv="/mounted-output/baseline/line_coverage_uncovered.csv"
    container_llc_map_csv="/mounted-output/baseline/llc_address_line_map.csv"
fi

if [[ -z "$lit_filter" && "$skip_baseline" -eq 0 ]]; then
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

if [[ "$skip_baseline" -eq 0 ]]; then
    rm -rf "${output_dir}/baseline"
fi
if [[ "$baseline_only" -eq 0 ]]; then
    rm -rf "${output_dir}/candidate_tests" "${output_dir}/incremental"
fi

docker_env=(
    -e "BASELINE_ONLY=${baseline_only}"
    -e "SKIP_BASELINE=${skip_baseline}"
)
if [[ "$skip_baseline" -eq 0 ]]; then
    docker_env+=(-e "LIT_FILTER=${lit_filter}")
fi
if [[ -n "$jobs" ]]; then
    docker_env+=(-e "JOBS=${jobs}")
fi
if [[ "$baseline_only" -eq 0 ]]; then
    docker_env+=(
        -e "CANDIDATE_N=${candidate_n}"
        -e "UNCOVERED_CSV=${container_uncovered_csv}"
        -e "LLC_MAP_CSV=${container_llc_map_csv}"
    )
fi

repo_mount=()
if [[ "${bind_repo}" -eq 1 ]]; then
    repo_mount=(-v "${REPO_ROOT}:${CONTAINER_WORKDIR}")
    echo "Using local fuzz-fill checkout: ${REPO_ROOT}"
fi

docker run --rm \
    -v "${output_dir}:/mounted-output" \
    "${baseline_mount[@]}" \
    "${uncovered_mount[@]}" \
    "${candidate_mount[@]}" \
    "${repo_mount[@]}" \
    "${docker_env[@]}" \
    -w "${CONTAINER_WORKDIR}" \
    "${image_ref}" \
    bash -lc '
set -euo pipefail

if [[ "${SKIP_BASELINE}" -eq 0 ]]; then
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
else
    echo "=== coverage baseline (skipped; using mounted profile) ==="
fi

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
        --line-coverage-uncovered-csv "${UNCOVERED_CSV}" \
        --llc-address-line-map-csv "${LLC_MAP_CSV}" \
        --candidate-tests-output-dir /mounted-output/candidate_tests
fi
'

echo "Image: ${image_ref}"
if [[ "$skip_baseline" -eq 0 ]]; then
    echo "LIT filter: ${lit_filter}"
fi

if [[ "$baseline_only" -eq 1 ]]; then
    echo "Wrote ${output_dir}/baseline/"
else
    report="${output_dir}/incremental/new_coverage.csv"
    echo "Wrote ${report}"
fi

if [[ "$skip_baseline" -eq 1 ]]; then
    lit_failures_json="${baseline_profile_dir}/lit_failures.json"
else
    lit_failures_json="${output_dir}/baseline/lit_failures.json"
fi
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
