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
  --run <id>                    Actions run id (default: newest successful
                                PR gap analysis for --pr)
  --fuzz-fill-repo <owner/name> Repo hosting the workflow
                                (default: ROCm/fuzz-fill or
                                FUZZ_FILL_GITHUB_REPO)
  --llvm-repo <owner/name>      Repo hosting the PR (default: llvm/llvm-project)
  --reference <path>            Local llvm-project for git clone --reference

Every run deletes <out>/artifacts and <out>/llvm and rebuilds them. If the
pull request head has moved since the analysis, the script exits. If the
instrumented-tools artifact is missing (upload_tools off, skipped scope, or
expired), pass --run for a run dispatched with upload_tools=true.
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
TOOLS_NAME="instrumented-tools-pr${PR_ID}"
# Marker matches the workflow run-name; trailing " by" avoids llvm#1 matching llvm#12.
TITLE_MARKER="llvm#${PR_ID} by"

resolve_run_id() {
    local ids id
    ids="$(
        gh api --paginate \
            "repos/${FUZZ_FILL_REPO}/actions/workflows/${WORKFLOW_FILE}/runs?event=workflow_dispatch&status=success&per_page=100" \
            --jq ".workflow_runs[] | select((.display_title // \"\") | contains(\"${TITLE_MARKER}\")) | .id"
    )"
    # Newest first. Avoid piping to head: the producer can die with SIGPIPE.
    id="${ids%%$'\n'*}"
    if [[ -z "$id" ]]; then
        echo "error: no successful ${WORKFLOW_FILE} run found for PR #${PR_ID} in ${FUZZ_FILL_REPO}" >&2
        exit 1
    fi
    printf '%s' "$id"
}

readme_get() {
    local key="$1" file="$2"
    awk -F': ' -v k="$key" '$1 == k { v=$2; for (i=3;i<=NF;i++) v=v FS $i; found=v }
         END { if (found != "") print found }' "$file"
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
echo "Using run ${RUN_ID} in ${FUZZ_FILL_REPO}"

RESULTS_ARTIFACT="${RESULTS_NAME}-${RUN_ID}"
TOOLS_ARTIFACT="${TOOLS_NAME}-${RUN_ID}"

echo "Downloading artifacts..."
rm -rf "$ARTIFACTS_DIR"
mkdir -p "$RESULTS_DIR" "$TOOLS_DIR"

if ! gh run download "$RUN_ID" -R "$FUZZ_FILL_REPO" -n "$RESULTS_ARTIFACT" -D "$RESULTS_DIR"; then
    echo "error: failed to download ${RESULTS_ARTIFACT} from run ${RUN_ID}" >&2
    exit 1
fi

if ! gh run download "$RUN_ID" -R "$FUZZ_FILL_REPO" -n "$TOOLS_ARTIFACT" -D "$TOOLS_DIR"; then
    echo "error: failed to download ${TOOLS_ARTIFACT} from run ${RUN_ID}" >&2
    echo "hint: that run may not have uploaded tools (upload_tools defaults to false," >&2
    echo "      scope may have been skip, or the artifact may have expired)." >&2
    echo "      Pass --run <id> for a run dispatched with upload_tools=true." >&2
    exit 1
fi

README="${RESULTS_DIR}/README-finding.txt"
CSV="${RESULTS_DIR}/out/commit_lines_report/target_lines_uncovered_pruned.csv"
TOOLS_BIN="${TOOLS_DIR}/bin"

if [[ ! -f "$README" ]]; then
    echo "error: missing ${README}" >&2
    exit 1
fi
if [[ ! -f "$CSV" ]]; then
    echo "error: missing ${CSV}" >&2
    exit 1
fi
for tool in opt llc sancov; do
    if [[ ! -x "${TOOLS_BIN}/${tool}" ]]; then
        echo "error: missing executable ${TOOLS_BIN}/${tool}" >&2
        exit 1
    fi
done

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

cat >"$ENV_PATH" <<EOF
LLVM_SRC=${LLVM_DIR}
DIFF=${DIFF_PATH}
INSTRUMENTED_BIN_DIR=${TOOLS_BIN}
PR_ID=${PR_ID}
RUN_ID=${RUN_ID}
COMMIT=${pr_head}
FUZZ_FILL_REPO=${FUZZ_FILL_REPO}
LLVM_REPO=${LLVM_REPO}
EOF

echo
echo "Context ready under ${OUT_DIR}"
echo "  targets: ${target_count} lines in ${TARGETS_PATH}"
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
