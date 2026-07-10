#!/usr/bin/env bash
# Run PR coverage-gap detection inside a one-shot Docker container:
#   coverage baseline (allow failures) -> added_lines -> target-lines
#
# Host output is bind-mounted at /mounted-output/ in the container.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

image_ref=""
pr_id=""
output_dir=""
lit_filter=""
image_name="${IMAGE_NAME:-fuzz-fill-test}"
commit_rev=""
jobs=""
build_image=0
llvm_repo=""
backend_tests=""
github_repo=""

usage() {
    cat <<EOF
Usage: $(basename "$0") (--image <ref> | --pr-id <n>) --output-dir <path> [options]

Run coverage baseline, added_lines, and target-lines in a temporary container.
Artifacts are written under --output-dir (mounted at /mounted-output/).

Required (one of):
  --image <ref>            Full Docker image ref (e.g. fuzz-fill-test:llvm-pr-203468)
  --pr-id <n>              Derive image as \${IMAGE_NAME:-fuzz-fill-test}:llvm-pr-<n>

Required:
  --output-dir <path>      Host output directory (created if missing)

Options:
  --build-image            Build PR image via build-image-pr.sh before detection
  --llvm-repo <path>       Local llvm-project clone (required with --build-image)
  --backend-tests <target> amdgpu or spirv (required with --build-image)
  --github-repo <owner/repo>
                           GitHub repo hosting the PR (default: llvm/llvm-project)
  --lit-filter <prefix>    LIT --filter= prefix (default: from image /work/.sancov-allowlist)
  --image-name <name>      Image name when using --pr-id (default: fuzz-fill-test)
  --commit <rev>           Revision for added_lines (default: HEAD in image llvm-project)
  -j <n>, --jobs <n>       Parallel jobs for llvm-lit; with --build-image, also for ninja
  --help, -h               Show this help

Examples:
  $(basename "$0") --build-image --llvm-repo /path/llvm-project --pr-id 203468 \\
      --backend-tests amdgpu --output-dir ./data/pr-cov-gaps-203468 -j "\$(nproc)"
  $(basename "$0") --pr-id 203468 --output-dir ./data/pr-cov-gaps-203468
  $(basename "$0") --pr-id 203468 --output-dir ./data/pr-cov-gaps-203468 \\
      --lit-filter 'CodeGen/AMDGPU/loop' -j "\$(nproc)"
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
        --build-image)
            build_image=1
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
        --lit-filter)
            [[ $# -ge 2 ]] || { echo "error: --lit-filter requires a value" >&2; exit 2; }
            lit_filter="$2"
            shift 2
            ;;
        --image-name)
            [[ $# -ge 2 ]] || { echo "error: --image-name requires a value" >&2; exit 2; }
            image_name="$2"
            shift 2
            ;;
        --commit)
            [[ $# -ge 2 ]] || { echo "error: --commit requires a value" >&2; exit 2; }
            commit_rev="$2"
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

if [[ -n "$image_ref" && -n "$pr_id" ]]; then
    echo "error: pass only one of --image or --pr-id" >&2
    exit 1
fi

if [[ -n "$image_ref" && "$build_image" -eq 1 ]]; then
    echo "error: --build-image cannot be used with --image" >&2
    exit 1
fi

if [[ -z "$image_ref" && -z "$pr_id" ]]; then
    echo "error: one of --image or --pr-id is required" >&2
    usage >&2
    exit 1
fi

if [[ -z "$output_dir" ]]; then
    echo "error: --output-dir is required" >&2
    usage >&2
    exit 1
fi

if [[ "$build_image" -eq 0 ]]; then
    if [[ -n "$llvm_repo" || -n "$backend_tests" || -n "$github_repo" ]]; then
        echo "error: --llvm-repo, --backend-tests, and --github-repo require --build-image" >&2
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

validate_jobs

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
        echo "hint: pass --build-image with --llvm-repo and --backend-tests to build it first" >&2
    fi
    exit 1
fi

if [[ -z "$lit_filter" ]]; then
    image_allowlist="$(read_image_allowlist)"
    lit_filter="$(lit_filter_for_allowlist "$image_allowlist")"
    echo "Image allowlist: ${image_allowlist} -> lit-filter: ${lit_filter}"
fi

mkdir -p "$output_dir"
output_dir="$(realpath "$output_dir")"

docker_env=(-e "LIT_FILTER=${lit_filter}")
if [[ -n "$commit_rev" ]]; then
    docker_env+=(-e "COMMIT_REV=${commit_rev}")
fi
if [[ -n "$jobs" ]]; then
    docker_env+=(-e "JOBS=${jobs}")
fi

docker run --rm \
    -v "${output_dir}:/mounted-output" \
    "${docker_env[@]}" \
    -w /work/fuzz-fill \
    "${image_ref}" \
    bash -lc '
set -euo pipefail

commit="${COMMIT_REV:-$(git -C /work/llvm-project rev-parse HEAD)}"

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

echo "=== added_lines (commit=${commit}) ==="
python -m added_lines \
    --commit "${commit}" \
    --output-dir /mounted-output/added-lines

echo "=== coverage target-lines ==="
python -m coverage target-lines \
    --output-dir /mounted-output/commit_lines_report \
    --baseline-output-dir /mounted-output/baseline \
    --target-lines-csv /mounted-output/added-lines/added-lines.csv
'

report="${output_dir}/commit_lines_report/target_lines_uncovered.csv"
echo "Wrote ${report}"
echo "Image: ${image_ref}"
echo "LIT filter: ${lit_filter}"
