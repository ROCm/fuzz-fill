#!/usr/bin/env bash
# Daily cron entry point for AMDGPU-only LLVM PR coverage-gap checking.
#
# Uses flock to avoid overlapping runs, loads local config.env, and drains
# all pending AMDGPU PR checks opened within the last 14 days.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_FILE="${PR_CHECK_CONFIG:-${SCRIPT_DIR}/config.env}"
LOCK_FILE="${REPO_ROOT}/data/pr-check/.amdgpu-daily.lock"
LOG_FILE="${PR_CHECK_LOG_FILE:-${REPO_ROOT}/logs/pr-check/amdgpu-daily.log}"
ORCHESTRATOR="${SCRIPT_DIR}/check-llvm-prs.sh"

log() {
    printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >&2
}

usage() {
    cat <<EOF
Usage: $(basename "$0")

Run the daily AMDGPU PR coverage-gap check (intended for cron).

Configuration:
  Copy ${SCRIPT_DIR}/config.example.env to ${CONFIG_FILE} and set LLVM_REPO
  to an absolute path before scheduling this script.

Environment:
  PR_CHECK_CONFIG    Override config file path (default: ${CONFIG_FILE})
  PR_CHECK_LOG_FILE  Override log file path (default: ${LOG_FILE})

Logs append to logs/pr-check/amdgpu-daily.log under the repo (gitignored).

For a dry run without builds, use:
  ${ORCHESTRATOR} --config ${CONFIG_FILE} --backends amdgpu --plan-only
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi

if [[ $# -gt 0 ]]; then
    echo "error: unknown argument: $1" >&2
    usage >&2
    exit 2
fi

# Cron runs with a minimal PATH; include common install locations.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${HOME}/.local/bin:${PATH:-}"

mkdir -p "$(dirname "$LOG_FILE")"
exec > >(tee -a "$LOG_FILE") 2>&1

if [[ ! -x "$ORCHESTRATOR" ]]; then
    log "error: orchestrator not found or not executable: ${ORCHESTRATOR}"
    exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    log "error: config file not found: ${CONFIG_FILE}"
    log "Copy ${SCRIPT_DIR}/config.example.env to ${CONFIG_FILE} and set LLVM_REPO."
    exit 1
fi

# shellcheck source=/dev/null
source "$CONFIG_FILE"

if [[ -z "${LLVM_REPO:-}" ]]; then
    log "error: LLVM_REPO is not set in ${CONFIG_FILE}"
    exit 1
fi

if [[ "${LLVM_REPO}" != /* ]]; then
    LLVM_REPO="${REPO_ROOT}/${LLVM_REPO}"
    export LLVM_REPO
    log "Resolved relative LLVM_REPO to ${LLVM_REPO}"
fi

mkdir -p "$(dirname "$LOCK_FILE")"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "Another daily AMDGPU PR check is already running; exiting."
    exit 0
fi

log "Starting daily AMDGPU PR check (repo=${REPO_ROOT})"
cd "$REPO_ROOT"

"${ORCHESTRATOR}" \
    --config "$CONFIG_FILE" \
    --backends amdgpu \
    --max-age-days "${PR_CHECK_MAX_AGE_DAYS:-14}" \
    --drain-queue

log "Daily AMDGPU PR check finished."
