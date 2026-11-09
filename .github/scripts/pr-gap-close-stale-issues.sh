#!/usr/bin/env bash
# Close open pr-analysis-result issues whose tracked pull request is no
# longer open. The pull request may be in any repository. This script reads
# that pull request and writes only to the issue tracker given by --repo.
#
# Usage:
#   pr-gap-close-stale-issues.sh [--dry-run] [--repo OWNER/NAME]
#
# Env (optional; GITHUB_* set in Actions):
#   GITHUB_REPOSITORY, GH_TOKEN, GITHUB_STEP_SUMMARY

set -euo pipefail

DRY_RUN=0
REPO="${GITHUB_REPOSITORY:-}"
LABEL="pr-analysis-result"
PER_PAGE="${PR_GAP_ISSUES_PER_PAGE:-100}"
MAX_ATTEMPTS=3
RETRY_DELAY="${PR_GAP_RETRY_DELAY:-2}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--dry-run] [--repo OWNER/NAME]
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --repo) REPO="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "error: unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ -z "$REPO" ]]; then
    echo "error: --repo or GITHUB_REPOSITORY is required" >&2
    usage >&2
    exit 2
fi
if [[ ! "$REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
    echo "error: invalid repository: ${REPO}" >&2
    exit 2
fi
# Issues live in this repo. Never point the closer at llvm/llvm-project.
if [[ "$REPO" == "llvm/llvm-project" ]]; then
    echo "error: refusing to close issues in llvm/llvm-project" >&2
    exit 2
fi
if [[ ! "$PER_PAGE" =~ ^[1-9][0-9]*$ ]]; then
    echo "error: invalid PR_GAP_ISSUES_PER_PAGE: ${PER_PAGE}" >&2
    exit 2
fi

kept=0
closed=0
skipped=0
failed=0

gh_retry() {
    local attempt=1 delay="$RETRY_DELAY"
    local out status
    while true; do
        status=0
        out="$("$@" 2>&1)" || status=$?
        if [[ "$status" -eq 0 ]]; then
            printf '%s' "$out"
            return 0
        fi
        if [[ "$attempt" -ge "$MAX_ATTEMPTS" ]]; then
            printf '%s\n' "$out" >&2
            return "$status"
        fi
        if printf '%s' "$out" | grep -Eqi 'HTTP 5[0-9][0-9]|HTTP 429|rate.?limit|timed out|connection|EOF|temporary'; then
            echo "warning: attempt ${attempt}/${MAX_ATTEMPTS} failed; retrying in ${delay}s" >&2
            printf '%s\n' "$out" >&2
            if [[ "$delay" -gt 0 ]]; then
                sleep "$delay"
            fi
            attempt=$((attempt + 1))
            delay=$((delay * 2))
            continue
        fi
        printf '%s\n' "$out" >&2
        return "$status"
    done
}

# open, merged, closed, or missing. Non-zero when the lookup itself fails.
pr_disposition() {
    local upstream="$1" pr_id="$2"
    local attempt=1 delay="$RETRY_DELAY"
    local out status state merged
    while true; do
        status=0
        out="$(gh api "repos/${upstream}/pulls/${pr_id}" 2>&1)" || status=$?
        if [[ "$status" -eq 0 ]]; then
            # jq -e treats JSON false as failure, so do not use it for .merged.
            state="$(printf '%s' "$out" | jq -r '.state // empty')"
            merged="$(printf '%s' "$out" | jq -r 'if .merged == true then "true" elif .merged == false then "false" else empty end')"
            if [[ -z "$state" || -z "$merged" ]]; then
                echo "error: pull response for ${upstream} pull ${pr_id} missing state or merged" >&2
                return 1
            fi
            if [[ "$state" == "open" ]]; then
                printf 'open'
            elif [[ "$merged" == "true" ]]; then
                printf 'merged'
            elif [[ "$state" == "closed" ]]; then
                printf 'closed'
            else
                echo "error: unexpected state for ${upstream} pull ${pr_id}: ${state}" >&2
                return 1
            fi
            return 0
        fi
        if printf '%s' "$out" | grep -Eq 'HTTP 404|Not Found'; then
            printf 'missing'
            return 0
        fi
        if [[ "$attempt" -ge "$MAX_ATTEMPTS" ]] || ! printf '%s' "$out" | grep -Eqi 'HTTP 5[0-9][0-9]|HTTP 429|rate.?limit|timed out|connection|EOF|temporary'; then
            printf '%s\n' "$out" >&2
            return 1
        fi
        echo "warning: ${upstream} pull ${pr_id} lookup attempt ${attempt}/${MAX_ATTEMPTS} failed; retrying in ${delay}s" >&2
        printf '%s\n' "$out" >&2
        if [[ "$delay" -gt 0 ]]; then
            sleep "$delay"
        fi
        attempt=$((attempt + 1))
        delay=$((delay * 2))
    done
}

close_issue() {
    local number="$1" upstream="$2" pr_id="$3" disposition="$4"
    local comment="Closing: the tracked pull request is no longer open."
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "dry-run: would close ${REPO} issue #${number} (${disposition}, ${upstream} pull ${pr_id})"
        return 0
    fi
    # Close the tracking issue in $REPO. Do not close ${upstream} pull ${pr_id}.
    gh_retry gh issue close "$number" --repo "$REPO" \
        --reason completed \
        --comment "$comment" >/dev/null
    echo "closed ${REPO} issue #${number} (${disposition}, ${upstream} pull ${pr_id})"
}

process_issue() {
    local number="$1" body="$2"
    local upstream pr_id disposition
    if [[ ! "$body" =~ Tracking-PR:[[:space:]]*(https://(redirect\.)?github\.com/)?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/pull/([0-9]+) ]]; then
        echo "error: issue #${number} has no Tracking-PR" >&2
        failed=$((failed + 1))
        return 0
    fi
    upstream="${BASH_REMATCH[3]}"
    pr_id="${BASH_REMATCH[4]}"
    if ! disposition="$(pr_disposition "$upstream" "$pr_id")"; then
        echo "error: could not read ${upstream} pull ${pr_id} for issue #${number}" >&2
        failed=$((failed + 1))
        return 0
    fi
    case "$disposition" in
        open)
            echo "keep issue #${number}: ${upstream} pull ${pr_id} is open"
            kept=$((kept + 1))
            ;;
        merged|closed)
            if close_issue "$number" "$upstream" "$pr_id" "$disposition"; then
                closed=$((closed + 1))
            else
                echo "error: failed to close ${REPO} issue #${number}" >&2
                failed=$((failed + 1))
            fi
            ;;
        missing)
            echo "skip issue #${number}: ${upstream} pull ${pr_id} was not found"
            skipped=$((skipped + 1))
            ;;
        *)
            echo "error: unexpected disposition ${disposition} for issue #${number}" >&2
            failed=$((failed + 1))
            ;;
    esac
}

page=1
while true; do
    batch="$(
        gh_retry gh api \
            "repos/${REPO}/issues?state=open&labels=${LABEL}&per_page=${PER_PAGE}&page=${page}"
    )"
    len="$(printf '%s' "$batch" | jq 'length')"
    if [[ "$len" -eq 0 ]]; then
        break
    fi
    while IFS= read -r item; do
        [[ -n "$item" ]] || continue
        number="$(printf '%s' "$item" | jq -r '.number')"
        body="$(printf '%s' "$item" | jq -r '.body // ""')"
        process_issue "$number" "$body"
    done < <(printf '%s' "$batch" | jq -c '.[] | select(.pull_request == null)')
    if [[ "$len" -lt "$PER_PAGE" ]]; then
        break
    fi
    page=$((page + 1))
done

echo "kept=${kept} closed=${closed} skipped=${skipped} failed=${failed} dry_run=${DRY_RUN}"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
        echo "### PR analysis issue cleanup"
        echo
        echo "- Closed: ${closed}"
        echo "- Upstream still open: ${kept}"
        echo "- Skipped: ${skipped}"
        echo "- Failed: ${failed}"
        if [[ "$DRY_RUN" -eq 1 ]]; then
            echo
            echo "Dry run: no issues were closed."
        fi
    } >>"$GITHUB_STEP_SUMMARY"
fi

if [[ "$failed" -ne 0 ]]; then
    exit 1
fi
