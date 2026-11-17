#!/usr/bin/env bash
# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Run setup-context → fill-line → usher-test for any llvm-project PR gap run.
#
# Usage:
#   export USER_NTID=...
#   export LLM_GATEWAY_BASE_URL=...
#   export FUZZ_FILL_API_KEY=...          # or --api-key / --key-file
#   scripts/fill-line/run-pr.sh all --pr <n> --out <dir> [options]
#   scripts/fill-line/run-pr.sh setup|fill|usher --pr <n> --out <dir> [options]

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SETUP_CONTEXT="${ROOT}/scripts/fill-line/setup-context.sh"

CMD=""
PR_ID=""
OUT_DIR=""
RUN_ID=""
REFERENCE=""
LATEST_TOOLS=0
TOOLS_RUNNER=""
API_KEY=""
KEY_FILE=""
BASE_URL="${LLM_GATEWAY_BASE_URL:-}"
USER_NTID_ARG=""
TARGETS=()
EXTRA_ARGS=()

usage() {
  cat <<EOF
Usage: $(basename "$0") <setup|fill|usher|all> --pr <n> --out <dir> [options]

Run setup-context, fill-line, and/or usher-test for a PR gap-analysis context.

Required:
  setup|fill|usher|all          Subcommand
  --pr <n>                      llvm-project pull request number
  --out <dir>                   Context directory (from setup-context)

Optional:
  --run <id>                    Actions run id (passed to setup-context)
  --latest-tools                Passed to setup-context: newest tools
                                tarball for the analyzed pr_head
  --reference <path>            Local llvm-project for git clone --reference
  --target <path:line>          Repeatable; fill uses these instead of targets.txt
  --tools-runner <host|docker>  Passed through to fill-line / usher-test when set
  --api-key <key>               Explicit raw gateway key
  --key-file <path>             Gateway key file
  --base-url <url>              Gateway base URL (or set LLM_GATEWAY_BASE_URL)
  --user-ntid <ntid>            Gateway user NTID (or set USER_NTID)
  -- <args...>                  Extra args forwarded to fill-line and usher-test

Gateway key: exactly one of --api-key, --key-file, or FUZZ_FILL_API_KEY.
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

resolve_bin() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    command -v "$name"
    return
  fi
  if [[ -x "${ROOT}/venv/bin/${name}" ]]; then
    echo "${ROOT}/venv/bin/${name}"
    return
  fi
  die "${name} not found on PATH or at ${ROOT}/venv/bin/${name}"
}

# Parse: first positional is subcommand; then flags; -- starts EXTRA_ARGS.
if [[ $# -lt 1 ]]; then
  usage >&2
  exit 2
fi
CMD="$1"
shift
case "$CMD" in
  setup|fill|usher|all) ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    echo "error: unknown subcommand: ${CMD}" >&2
    usage >&2
    exit 2
    ;;
esac

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pr)
      [[ $# -ge 2 ]] || die "--pr requires a value"
      PR_ID="$2"
      shift 2
      ;;
    --out)
      [[ $# -ge 2 ]] || die "--out requires a value"
      OUT_DIR="$2"
      shift 2
      ;;
    --run)
      [[ $# -ge 2 ]] || die "--run requires a value"
      RUN_ID="$2"
      shift 2
      ;;
    --latest-tools)
      LATEST_TOOLS=1
      shift
      ;;
    --reference)
      [[ $# -ge 2 ]] || die "--reference requires a value"
      REFERENCE="$2"
      shift 2
      ;;
    --target)
      [[ $# -ge 2 ]] || die "--target requires a value"
      TARGETS+=("$2")
      shift 2
      ;;
    --tools-runner)
      [[ $# -ge 2 ]] || die "--tools-runner requires a value"
      TOOLS_RUNNER="$2"
      shift 2
      ;;
    --api-key)
      [[ $# -ge 2 ]] || die "--api-key requires a value"
      API_KEY="$2"
      shift 2
      ;;
    --key-file)
      [[ $# -ge 2 ]] || die "--key-file requires a value"
      KEY_FILE="$2"
      shift 2
      ;;
    --base-url)
      [[ $# -ge 2 ]] || die "--base-url requires a value"
      BASE_URL="$2"
      shift 2
      ;;
    --user-ntid)
      [[ $# -ge 2 ]] || die "--user-ntid requires a value"
      USER_NTID_ARG="$2"
      shift 2
      ;;
    --)
      shift
      EXTRA_ARGS=("$@")
      break
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

[[ -n "$PR_ID" ]] || die "--pr is required"
[[ -n "$OUT_DIR" ]] || die "--out is required"
if [[ ! "$PR_ID" =~ ^[0-9]+$ ]]; then
  die "--pr must be a positive integer: ${PR_ID}"
fi

# Resolve OUT_DIR to absolute for stable paths after cd.
if [[ "$OUT_DIR" != /* ]]; then
  OUT_DIR="$(pwd)/${OUT_DIR}"
fi
FILL_OUT="${OUT_DIR}/fill-line-out"
FILL_WORK="${OUT_DIR}/fill-line-work"
CONTEXT_ENV="${OUT_DIR}/context.env"
TARGETS_FILE="${OUT_DIR}/targets.txt"

NTID="${USER_NTID_ARG:-${USER_NTID:-}}"

gateway_key_args() {
  local n=0
  [[ -n "$API_KEY" ]] && n=$((n + 1))
  [[ -n "$KEY_FILE" ]] && n=$((n + 1))
  [[ -n "${FUZZ_FILL_API_KEY:-}" ]] && n=$((n + 1))
  if [[ "$n" -eq 0 ]]; then
    die "pass --api-key, --key-file, or set FUZZ_FILL_API_KEY"
  fi
  if [[ "$n" -gt 1 ]]; then
    die "pass only one of --api-key, --key-file, or FUZZ_FILL_API_KEY"
  fi
  if [[ -n "$API_KEY" ]]; then
    printf '%s\0%s\0' --api-key "$API_KEY"
  elif [[ -n "$KEY_FILE" ]]; then
    [[ -f "$KEY_FILE" ]] || die "key file not found: ${KEY_FILE}"
    printf '%s\0%s\0' --key-file "$KEY_FILE"
  else
    printf '%s\0%s\0' --api-key "${FUZZ_FILL_API_KEY}"
  fi
}

need_gateway() {
  [[ -n "$BASE_URL" ]] || die "pass --base-url or set LLM_GATEWAY_BASE_URL"
  [[ -n "$NTID" ]] || die "pass --user-ntid or set USER_NTID"
  # Validate key selection early (also used when building argv).
  gateway_key_args >/dev/null
}

# Append gateway flags to the named array via nameref.
append_gateway_args() {
  local -n _arr=$1
  local key_args
  # Read NUL-separated pairs from gateway_key_args.
  while IFS= read -r -d '' flag && IFS= read -r -d '' val; do
    _arr+=("$flag" "$val")
  done < <(gateway_key_args)
  _arr+=(--base-url "$BASE_URL" --user-ntid "$NTID")
}

has_covering_results() {
  if [[ -f "${FILL_OUT}/result.json" ]]; then
    python3 -c '
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))
sys.exit(0 if r.get("status") == "covered" else 1)
' "${FILL_OUT}/result.json" 2>/dev/null && return 0
  fi
  if [[ -f "${FILL_OUT}/summary.json" ]]; then
    python3 -c '
import json, sys
s = json.load(open(sys.argv[1], encoding="utf-8"))
targets = s.get("targets") or s.get("cases") or []
sys.exit(0 if any(t.get("status") == "covered" for t in targets) else 1)
' "${FILL_OUT}/summary.json" 2>/dev/null && return 0
  fi
  # Multi-target layout: lines/*/result.json
  local f
  for f in "${FILL_OUT}"/lines/*/result.json; do
    [[ -f "$f" ]] || continue
    python3 -c '
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))
sys.exit(0 if r.get("status") == "covered" else 1)
' "$f" 2>/dev/null && return 0
  done
  return 1
}

cmd_setup() {
  [[ -x "$SETUP_CONTEXT" ]] || die "setup-context not found: ${SETUP_CONTEXT}"
  local args=(--pr "$PR_ID" --out "$OUT_DIR")
  [[ -n "$RUN_ID" ]] && args+=(--run "$RUN_ID")
  [[ "$LATEST_TOOLS" -eq 1 ]] && args+=(--latest-tools)
  [[ -n "$REFERENCE" ]] && args+=(--reference "$REFERENCE")
  "$SETUP_CONTEXT" "${args[@]}"
}

build_target_args() {
  local -n _out=$1
  _out=()
  local t
  if [[ ${#TARGETS[@]} -gt 0 ]]; then
    for t in "${TARGETS[@]}"; do
      _out+=(--target "$t")
    done
    return
  fi
  [[ -f "$TARGETS_FILE" ]] || die "no --target and missing ${TARGETS_FILE} (run setup first)"
  local count=0
  while IFS= read -r t || [[ -n "$t" ]]; do
    [[ -z "$t" || "$t" =~ ^# ]] && continue
    _out+=(--target "$t")
    count=$((count + 1))
  done <"$TARGETS_FILE"
  [[ "$count" -gt 0 ]] || die "targets.txt is empty; pass --target path:line"
}

cmd_fill() {
  need_gateway
  [[ -f "$CONTEXT_ENV" ]] || die "missing ${CONTEXT_ENV} (run setup first)"
  # shellcheck disable=SC1090
  source "$CONTEXT_ENV"
  [[ -n "${LLVM_SRC:-}" && -n "${DIFF:-}" && -n "${INSTRUMENTED_BIN_DIR:-}" ]] \
    || die "context.env missing LLVM_SRC / DIFF / INSTRUMENTED_BIN_DIR"

  local fill_bin
  fill_bin="$(resolve_bin fill-line)"
  mkdir -p "$FILL_OUT" "$FILL_WORK"

  local target_args=()
  build_target_args target_args

  local args=(
    --llvm-src "${LLVM_SRC}"
    --diff "${DIFF}"
    --instrumented-bin-dir "${INSTRUMENTED_BIN_DIR}"
    --out-dir "${FILL_OUT}"
    --work-dir "${FILL_WORK}"
  )
  [[ -n "$TOOLS_RUNNER" ]] && args+=(--tools-runner "$TOOLS_RUNNER")
  args+=("${target_args[@]}")
  append_gateway_args args
  args+=("${EXTRA_ARGS[@]}")

  "$fill_bin" "${args[@]}"
}

cmd_usher() {
  need_gateway
  if [[ ! -f "${FILL_OUT}/result.json" && ! -f "${FILL_OUT}/summary.json" ]]; then
    die "missing fill-line results under ${FILL_OUT} (run fill first)"
  fi
  local filecheck=""
  if [[ -f "$CONTEXT_ENV" ]]; then
    # FileCheck from the instrumented-tools artifact (written by setup-context).
    # shellcheck disable=SC1090
    source "$CONTEXT_ENV"
    filecheck="${FILECHECK:-}"
  fi
  [[ -n "$filecheck" ]] || die "FILECHECK missing in ${CONTEXT_ENV}; re-run setup"
  [[ -x "$filecheck" ]] || die "FileCheck not executable: ${filecheck}"

  local usher_bin
  usher_bin="$(resolve_bin usher-test)"

  local args=(
    --from "${FILL_OUT}"
    --filecheck "${filecheck}"
  )
  [[ -n "$TOOLS_RUNNER" ]] && args+=(--tools-runner "$TOOLS_RUNNER")
  append_gateway_args args
  args+=("${EXTRA_ARGS[@]}")

  "$usher_bin" "${args[@]}"
}

cmd_all() {
  local fill_rc=0
  local usher_rc=0

  cmd_setup

  set +e
  cmd_fill
  fill_rc=$?
  set -e

  if has_covering_results; then
    set +e
    cmd_usher
    usher_rc=$?
    set -e
  elif [[ "$fill_rc" -ne 0 ]]; then
    echo "warning: fill-line exited ${fill_rc} and no covering results; skipping usher" >&2
  else
    echo "warning: no covering results; skipping usher" >&2
  fi

  if [[ "$fill_rc" -ne 0 ]]; then
    exit "$fill_rc"
  fi
  exit "$usher_rc"
}

cd "$ROOT"

case "$CMD" in
  setup) cmd_setup ;;
  fill) cmd_fill ;;
  usher) cmd_usher ;;
  all) cmd_all ;;
esac
