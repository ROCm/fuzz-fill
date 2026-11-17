#!/usr/bin/env bash
# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Download a PR gap-analysis run's artifacts, check out the analyzed commit,
# and write the paths fill-line needs. Stops if the pull request has moved.
#
# Usage:
#   setup-context.sh --pr <n> --out <dir> [--run <id>] [options]

set -euo pipefail

PR_ID=""
OUT_DIR=""
RUN_ID=""
LATEST_TOOLS=0
FUZZ_FILL_REPO="${FUZZ_FILL_GITHUB_REPO:-ROCm/fuzz-fill}"
LLVM_REPO="llvm/llvm-project"
REFERENCE=""
CONTAINER_BUILD_PREFIX="/work/pr-llvm/"
WORKFLOW_FILE="pr-gap-analysis.yml"

usage() {
    cat <<EOF
Usage: $(basename "$0") --pr <n> --out <dir> [--run <id>] [options]

Download gap-finding results and instrumented tools for a PR gap-analysis
run, check out the analyzed PR head, and write pr.diff / targets.txt /
context.env for fill-line.

Required:
  --pr <n>                      llvm-project pull request number
  --out <dir>                   Output directory (created if missing)

Optional:
  --run <id>                    Actions run id for gap-finding-results
                                (default: newest successful PR gap analysis
                                for --pr that has results)
  --latest-tools                Use the newest tools tarball for this PR
                                whose name matches the analyzed pr_head
                                (prefers build_only runs); may differ from
                                the results --run
  --fuzz-fill-repo <owner/name> Repo hosting the workflow
                                (default: ROCm/fuzz-fill or
                                FUZZ_FILL_GITHUB_REPO)
  --llvm-repo <owner/name>      Repo hosting the PR (default: llvm/llvm-project)
  --reference <path>            Local llvm-project for git clone --reference

Every run deletes <out>/artifacts and <out>/llvm and rebuilds them. If the
pull request head has moved since the analysis, the script exits. If the
instrumented-tools artifact is missing, pass --run for a run with
upload_tools=true, or --latest-tools to take the newest matching head.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr)
            [[ $# -ge 2 ]] || { echo "error: --pr requires a value" >&2; exit 2; }
            PR_ID="$2"
            shift 2
            ;;
        --out)
            [[ $# -ge 2 ]] || { echo "error: --out requires a value" >&2; exit 2; }
            OUT_DIR="$2"
            shift 2
            ;;
        --run)
            [[ $# -ge 2 ]] || { echo "error: --run requires a value" >&2; exit 2; }
            RUN_ID="$2"
            shift 2
            ;;
        --latest-tools)
            LATEST_TOOLS=1
            shift
            ;;
        --fuzz-fill-repo)
            [[ $# -ge 2 ]] || { echo "error: --fuzz-fill-repo requires a value" >&2; exit 2; }
            FUZZ_FILL_REPO="$2"
            shift 2
            ;;
        --llvm-repo)
            [[ $# -ge 2 ]] || { echo "error: --llvm-repo requires a value" >&2; exit 2; }
            LLVM_REPO="$2"
            shift 2
            ;;
        --reference)
            [[ $# -ge 2 ]] || { echo "error: --reference requires a value" >&2; exit 2; }
            REFERENCE="$2"
            shift 2
            ;;
        -h|--help)
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

if [[ -z "$PR_ID" || -z "$OUT_DIR" ]]; then
    echo "error: --pr and --out are required" >&2
    usage >&2
    exit 2
fi
if [[ ! "$PR_ID" =~ ^[0-9]+$ ]]; then
    echo "error: --pr must be a positive integer: ${PR_ID}" >&2
    exit 2
fi
if [[ -n "$RUN_ID" && ! "$RUN_ID" =~ ^[0-9]+$ ]]; then
    echo "error: --run must be a positive integer: ${RUN_ID}" >&2
    exit 2
fi
if [[ -n "$REFERENCE" && ! -d "$REFERENCE" ]]; then
    echo "error: --reference is not a directory: ${REFERENCE}" >&2
    exit 2
fi

for tool in gh git; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "error: ${tool} is required" >&2
        exit 1
    fi
done

RESULTS_NAME="gap-finding-results-pr${PR_ID}"
TOOLS_NAME_PREFIX="instrumented-tools-pr${PR_ID}"
# Marker matches the workflow run-name; trailing " by" avoids llvm#1 matching llvm#12.
TITLE_MARKER="llvm#${PR_ID} by"

list_pr_run_ids() {
    # Newest first. Avoid piping to head: the producer can die with SIGPIPE.
    gh api --paginate \
        "repos/${FUZZ_FILL_REPO}/actions/workflows/${WORKFLOW_FILE}/runs?event=workflow_dispatch&status=success&per_page=100" \
        --jq ".workflow_runs[] | select((.display_title // \"\") | contains(\"${TITLE_MARKER}\")) | .id"
}

resolve_run_id() {
    local ids id
    ids="$(list_pr_run_ids)"
    if [[ -z "$ids" ]]; then
        echo "error: no successful ${WORKFLOW_FILE} run found for PR #${PR_ID} in ${FUZZ_FILL_REPO}" >&2
        exit 1
    fi
    # Prefer a run that uploaded gap-finding-results (skip newer build_only runs).
    while IFS= read -r id; do
        [[ -n "$id" ]] || continue
        if run_has_results_artifact "$id"; then
            printf '%s' "$id"
            return 0
        fi
    done <<<"$ids"
    echo "error: no successful ${WORKFLOW_FILE} run with gap-finding-results for PR #${PR_ID}" >&2
    echo "hint: build_only runs have tools but no results; pass --run <analysis-id>." >&2
    exit 1
}

readme_get() {
    local key="$1" file="$2"
    awk -F': ' -v k="$key" '$1 == k { v=$2; for (i=3;i<=NF;i++) v=v FS $i; found=v }
         END { if (found != "") print found }' "$file"
}

# Print tools artifact name on a run for the given head, or empty.
# Only accepts instrumented-tools-pr<N>-<run>-<head_short>.tar.xz.
tools_artifact_on_run() {
    local run_id="$1" head_short="$2" names name expected
    if [[ -z "$head_short" ]]; then
        echo "error: tools_artifact_on_run requires head_short" >&2
        return 1
    fi
    expected="${TOOLS_NAME_PREFIX}-${run_id}-${head_short}.tar.xz"
    names="$(
        gh api --paginate \
            "repos/${FUZZ_FILL_REPO}/actions/runs/${run_id}/artifacts" \
            --jq '.artifacts[] | select(.expired == false) | .name'
    )"
    while IFS= read -r name; do
        [[ -n "$name" ]] || continue
        if [[ "$name" == "$expected" ]]; then
            printf '%s' "$name"
            return 0
        fi
    done <<<"$names"
    return 1
}

run_has_results_artifact() {
    local run_id="$1" names name
    names="$(
        gh api --paginate \
            "repos/${FUZZ_FILL_REPO}/actions/runs/${run_id}/artifacts" \
            --jq '.artifacts[] | select(.expired == false) | .name'
    )"
    while IFS= read -r name; do
        [[ "$name" == "${RESULTS_NAME}-${run_id}" ]] && return 0
    done <<<"$names"
    return 1
}

# Print "run_id<TAB>artifact_name" for the newest tools tarball matching head.
# Prefers runs without gap-finding-results (typical build_only), then any match.
find_tools_for_head() {
    local head_sha="$1" short="${1:0:12}" ids id name fallback_id="" fallback_name=""
    ids="$(list_pr_run_ids)"
    while IFS= read -r id; do
        [[ -n "$id" ]] || continue
        name="$(tools_artifact_on_run "$id" "$short" || true)"
        [[ -n "$name" ]] || continue
        if ! run_has_results_artifact "$id"; then
            printf '%s\t%s' "$id" "$name"
            return 0
        fi
        if [[ -z "$fallback_id" ]]; then
            fallback_id="$id"
            fallback_name="$name"
        fi
    done <<<"$ids"
    if [[ -n "$fallback_id" ]]; then
        printf '%s\t%s' "$fallback_id" "$fallback_name"
        return 0
    fi
    return 1
}

# archive:false uploads are raw files; gh run download still tries to unzip them
# (fails on older gh). Fetch via the artifacts API instead; the path is named
# /zip even when the body is the raw .tar.xz.
download_tools_tarball() {
    local run_id="$1" artifact_name="$2" dest_dir="$3"
    local artifact_id out ids
    ids="$(
        gh api --paginate \
            "repos/${FUZZ_FILL_REPO}/actions/runs/${run_id}/artifacts" \
            --jq ".artifacts[] | select(.expired == false and .name == \"${artifact_name}\") | .id"
    )"
    artifact_id="${ids%%$'\n'*}"
    if [[ -z "$artifact_id" ]]; then
        echo "error: artifact ${artifact_name} not found on run ${run_id}" >&2
        return 1
    fi
    out="${dest_dir}/${artifact_name}"
    echo "Downloading ${artifact_name} (artifact ${artifact_id})..."
    if ! gh api "repos/${FUZZ_FILL_REPO}/actions/artifacts/${artifact_id}/zip" > "$out"; then
        rm -f "$out"
        return 1
    fi
    if [[ ! -s "$out" ]]; then
        echo "error: downloaded empty tools artifact ${artifact_name}" >&2
        rm -f "$out"
        return 1
    fi
}

extract_tools_download() {
    local dl_dir="$1" artifact_name="$2"
    local tarball="" candidate
    shopt -s nullglob
    local tarballs=("$dl_dir"/*.tar.xz "$dl_dir"/"$artifact_name")
    shopt -u nullglob
    for candidate in "${tarballs[@]}"; do
        if [[ -f "$candidate" && "$candidate" == *.tar.xz ]]; then
            tarball="$candidate"
            break
        fi
    done
    if [[ -z "$tarball" ]]; then
        echo "error: downloaded tools artifact is not a .tar.xz: ${artifact_name}" >&2
        exit 1
    fi
    echo "Extracting ${tarball##*/}..."
    tar -xJf "$tarball" -C "$TOOLS_DIR"
}

OUT_DIR="$(mkdir -p "$OUT_DIR" && cd "$OUT_DIR" && pwd)"
ARTIFACTS_DIR="${OUT_DIR}/artifacts"
RESULTS_DIR="${ARTIFACTS_DIR}/gap-finding-results"
TOOLS_DIR="${ARTIFACTS_DIR}/instrumented-tools"
LLVM_DIR="${OUT_DIR}/llvm"
DIFF_PATH="${OUT_DIR}/pr.diff"
TARGETS_PATH="${OUT_DIR}/targets.txt"
ENV_PATH="${OUT_DIR}/context.env"

if [[ -z "$RUN_ID" ]]; then
    echo "Resolving newest successful PR gap analysis for #${PR_ID}..."
    RUN_ID="$(resolve_run_id)"
fi
echo "Using results run ${RUN_ID} in ${FUZZ_FILL_REPO}"

RESULTS_ARTIFACT="${RESULTS_NAME}-${RUN_ID}"

echo "Downloading gap-finding results..."
rm -rf "$ARTIFACTS_DIR"
mkdir -p "$RESULTS_DIR" "$TOOLS_DIR"

if ! gh run download "$RUN_ID" -R "$FUZZ_FILL_REPO" -n "$RESULTS_ARTIFACT" -D "$RESULTS_DIR"; then
    echo "error: failed to download ${RESULTS_ARTIFACT} from run ${RUN_ID}" >&2
    echo "hint: that run may be build_only (no results). Pass --run for an" >&2
    echo "      analysis run that uploaded gap-finding-results." >&2
    exit 1
fi

README="${RESULTS_DIR}/README-finding.txt"
CSV="${RESULTS_DIR}/out/commit_lines_report/target_lines_uncovered_pruned.csv"
if [[ ! -f "$README" ]]; then
    echo "error: missing ${README}" >&2
    exit 1
fi
if [[ ! -f "$CSV" ]]; then
    echo "error: missing ${CSV}" >&2
    exit 1
fi

analyzed_pr_id="$(readme_get pr_id "$README")"
analyzed_repo="$(readme_get github_repo "$README")"
pr_head="$(readme_get pr_head "$README")"

if [[ -z "$pr_head" ]]; then
    echo "error: README-finding.txt missing pr_head" >&2
    exit 1
fi
if [[ -n "$analyzed_pr_id" && "$analyzed_pr_id" != "$PR_ID" ]]; then
    echo "error: artifact pr_id ${analyzed_pr_id} does not match --pr ${PR_ID}" >&2
    exit 1
fi
if [[ -n "$analyzed_repo" && "$analyzed_repo" != "$LLVM_REPO" ]]; then
    echo "error: artifact github_repo ${analyzed_repo} does not match --llvm-repo ${LLVM_REPO}" >&2
    echo "hint: pass --llvm-repo ${analyzed_repo}" >&2
    exit 1
fi
if [[ -n "$analyzed_repo" ]]; then
    LLVM_REPO="$analyzed_repo"
fi

HEAD_SHORT="${pr_head:0:12}"
TOOLS_RUN_ID="$RUN_ID"
TOOLS_ARTIFACT=""
if [[ "$LATEST_TOOLS" -eq 1 ]]; then
    echo "Selecting newest tools tarball for head ${HEAD_SHORT}..."
    matched="$(find_tools_for_head "$pr_head" || true)"
    if [[ -z "$matched" ]]; then
        echo "error: no instrumented-tools-…-${HEAD_SHORT}.tar.xz for this PR" >&2
        echo "hint: dispatch pr-gap-analysis with build_only=true (or upload_tools=true)" >&2
        echo "      for this PR head, then re-run setup-context --latest-tools." >&2
        exit 1
    fi
    TOOLS_RUN_ID="${matched%%$'\t'*}"
    TOOLS_ARTIFACT="${matched#*$'\t'}"
    echo "Using tools from run ${TOOLS_RUN_ID} (${TOOLS_ARTIFACT})"
else
    TOOLS_ARTIFACT="$(tools_artifact_on_run "$RUN_ID" "$HEAD_SHORT" || true)"
    if [[ -z "$TOOLS_ARTIFACT" ]]; then
        echo "error: no ${TOOLS_NAME_PREFIX}-${RUN_ID}-${HEAD_SHORT}.tar.xz on run ${RUN_ID}" >&2
        echo "hint: that run may not have uploaded tools (upload_tools defaults to false," >&2
        echo "      scope may have been skip, or the artifact may have expired)." >&2
        echo "      Pass --run for a run with upload_tools=true, or --latest-tools" >&2
        echo "      to take the newest tools tarball for the analyzed head." >&2
        exit 1
    fi
fi

TOOLS_DL="$(mktemp -d "${ARTIFACTS_DIR}/tools-dl.XXXXXX")"
if ! download_tools_tarball "$TOOLS_RUN_ID" "$TOOLS_ARTIFACT" "$TOOLS_DL"; then
    echo "error: failed to download ${TOOLS_ARTIFACT} from run ${TOOLS_RUN_ID}" >&2
    rm -rf "$TOOLS_DL"
    exit 1
fi
extract_tools_download "$TOOLS_DL" "$TOOLS_ARTIFACT"
rm -rf "$TOOLS_DL"

TOOLS_BIN="${TOOLS_DIR}/bin"
TOOLS_ROOT="${TOOLS_DIR}"

for tool in opt llc sancov; do
    if [[ ! -x "${TOOLS_BIN}/${tool}" ]]; then
        echo "error: missing executable ${TOOLS_BIN}/${tool}" >&2
        exit 1
    fi
done
ARTIFACT_FILECHECK=""
if [[ -x "${TOOLS_BIN}/FileCheck" ]]; then
    ARTIFACT_FILECHECK="${TOOLS_BIN}/FileCheck"
fi

live_head="$(gh api "repos/${LLVM_REPO}/pulls/${PR_ID}" --jq '.head.sha')"
base_sha="$(gh api "repos/${LLVM_REPO}/pulls/${PR_ID}" --jq '.base.sha')"
if [[ -z "$live_head" || -z "$base_sha" ]]; then
    echo "error: could not resolve head/base for ${LLVM_REPO}#${PR_ID}" >&2
    exit 1
fi

if [[ "$live_head" != "$pr_head" ]]; then
    echo "error: pull request has moved since the analysis" >&2
    echo "  analyzed pr_head: ${pr_head}" >&2
    echo "  live head:        ${live_head}" >&2
    echo "hint: re-run PR gap analysis for the current head, or pick a run that" >&2
    echo "      matches today's tip." >&2
    exit 1
fi

echo "Checking out ${pr_head} from ${LLVM_REPO}..."
rm -rf "$LLVM_DIR"
clone_args=(--filter=blob:none "https://github.com/${LLVM_REPO}.git" "$LLVM_DIR")
if [[ -n "$REFERENCE" ]]; then
    clone_args=(--reference "$REFERENCE" "${clone_args[@]}")
fi
git clone "${clone_args[@]}"
git -C "$LLVM_DIR" fetch --filter=blob:none origin "$pr_head" "$base_sha"
git -C "$LLVM_DIR" checkout --detach "$pr_head"

merge_base="$(git -C "$LLVM_DIR" merge-base "$pr_head" "$base_sha")"
if [[ -z "$merge_base" ]]; then
    echo "error: could not find merge-base of ${pr_head} and ${base_sha}" >&2
    exit 1
fi
echo "Writing pr.diff (${merge_base:0:12}..${pr_head:0:12})..."
git -C "$LLVM_DIR" diff "$merge_base" "$pr_head" >"$DIFF_PATH"

echo "Writing targets.txt..."
awk -F',' -v prefix="$CONTAINER_BUILD_PREFIX" '
    NR == 1 { next }
    NF < 2 { next }
    {
        file = $1
        line = $2
        if (index(file, prefix) == 1)
            file = substr(file, length(prefix) + 1)
        key = file SUBSEP line
        if (!(key in seen)) {
            seen[key] = 1
            print file ":" line
        }
    }
' "$CSV" | LC_ALL=C sort >"$TARGETS_PATH"

target_count="$(wc -l <"$TARGETS_PATH" | tr -d ' ')"

{
    echo "LLVM_SRC=${LLVM_DIR}"
    echo "DIFF=${DIFF_PATH}"
    echo "INSTRUMENTED_BIN_DIR=${TOOLS_BIN}"
    echo "INSTRUMENTED_TOOLS_ROOT=${TOOLS_ROOT}"
    echo "PR_ID=${PR_ID}"
    echo "RUN_ID=${RUN_ID}"
    echo "TOOLS_RUN_ID=${TOOLS_RUN_ID}"
    echo "COMMIT=${pr_head}"
    echo "FUZZ_FILL_REPO=${FUZZ_FILL_REPO}"
    echo "LLVM_REPO=${LLVM_REPO}"
    if [[ -n "$ARTIFACT_FILECHECK" ]]; then
        echo "FILECHECK=${ARTIFACT_FILECHECK}"
    fi
} >"$ENV_PATH"

echo
echo "Context ready under ${OUT_DIR}"
echo "  targets: ${target_count} lines in ${TARGETS_PATH}"
echo "  results: run ${RUN_ID}"
echo "  tools:   run ${TOOLS_RUN_ID}"
echo "  env:     ${ENV_PATH}"
echo
echo "Example fill-line invocation (add --api-key / --base-url / --user-ntid):"
echo
if [[ "$target_count" -eq 0 ]]; then
    echo "  # targets.txt is empty; pass --target path:line explicitly"
    cat <<EOF
  ./venv/bin/fill-line \\
    --llvm-src "${LLVM_DIR}" \\
    --diff "${DIFF_PATH}" \\
    --instrumented-bin-dir "${TOOLS_BIN}" \\
    --tools-runner docker \\
    --out-dir "${OUT_DIR}/fill-line-out" \\
    --work-dir "${OUT_DIR}/fill-line-work" \\
    --target <path:line>
EOF
else
    first_target="$(head -n 1 "$TARGETS_PATH")"
    cat <<EOF
  ./venv/bin/fill-line \\
    --llvm-src "${LLVM_DIR}" \\
    --diff "${DIFF_PATH}" \\
    --instrumented-bin-dir "${TOOLS_BIN}" \\
    --tools-runner docker \\
    --out-dir "${OUT_DIR}/fill-line-out" \\
    --work-dir "${OUT_DIR}/fill-line-work" \\
    --target "${first_target}"
EOF
    if [[ "$target_count" -gt 1 ]]; then
        echo
        echo "  # or every uncovered line:"
        echo "  #   xargs -a ${TARGETS_PATH} -I{} echo --target {}"
    fi
fi
