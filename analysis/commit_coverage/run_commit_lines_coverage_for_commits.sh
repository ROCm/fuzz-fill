#!/bin/bash
# For each LLVM base revision: cherry-pick lit-coverage helpers, rebuild amdgpu BB,
# then run fuzz-fill coverage + diff + commit-lines with a per-commit output tree.
#
# Requires a clean llvm-project working tree at the start of each iteration
# (the cherry-pick script enforces this).
#
# Usage:
#   COMMITS="sha1 sha2 sha3" ./run_commit_lines_coverage_for_commits.sh
#   COMMITS_FILE=/path/to/commits.txt ./run_commit_lines_coverage_for_commits.sh
#     (one revision per line; # starts a comment; blank lines ignored)
#
# Optional environment:
#   FUZZ_FILL_ROOT     — fuzz-fill repo root (default: ../.. from this script)
#   LLVM_REPO          — llvm-project path (default: sibling of fuzz-fill)
#   OUTPUT_ROOT_BASE   — under this, each run uses bb_coverage_commit_lines_<short_sha>/
#                        (default: $FUZZ_FILL_ROOT/data/coverage_output)
#   FILTER             — lit filter (default: CodeGen/AMDGPU)
#   LLVM_BIN           — dir with clang for LIT (default: $LLVM_REPO/build/bin)
#   INSTRUMENTED_BIN_DIR — sancov-instrumented tools (default: $LLVM_REPO/build-amdgpu-bb/bin)
#   SKIP_CHERRY_PICK   — if 1, only build + coverage (HEAD must already be set up)
#   SKIP_BUILD         — if 1, only run coverage steps
#
# Each commit output folder includes resource_stats.csv: wall/user/sys CPU and max RSS
# (from GNU /usr/bin/time) for ./build-amdgpu-bb.sh and `python -m coverage test-suite`,
# plus total wall time for the full iteration (cherry-pick through commit-lines).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHERRY_SCRIPT="${SCRIPT_DIR}/llvm_lit_coverage_cherry_pick.sh"
FUZZ_FILL_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LLVM_REPO="${LLVM_REPO:-$(cd "${FUZZ_FILL_ROOT}/../llvm-project" && pwd)}"
OUTPUT_ROOT_BASE="${OUTPUT_ROOT_BASE:-${FUZZ_FILL_ROOT}/data/coverage_output}"
FILTER="${FILTER:-CodeGen/AMDGPU}"
LLVM_BIN="${LLVM_BIN:-${LLVM_REPO}/build/bin}"
INSTRUMENTED_BIN_DIR="${INSTRUMENTED_BIN_DIR:-${LLVM_REPO}/build-amdgpu-bb/bin}"
SKIP_CHERRY_PICK="${SKIP_CHERRY_PICK:-0}"
SKIP_BUILD="${SKIP_BUILD:-0}"

COMMITS_FILE="${COMMITS_FILE:-${SCRIPT_DIR}/commits.txt}"

COMMIT_ARRAY=()
if [[ -n "${COMMITS_FILE:-}" ]]; then
	if [[ ! -f "${COMMITS_FILE}" ]]; then
		echo "Error: COMMITS_FILE not found: ${COMMITS_FILE}" >&2
		exit 1
	fi
	while IFS= read -r raw || [[ -n "${raw}" ]]; do
		line="${raw%%#*}"
		line="${line//$'\r'/}"
		line="${line#"${line%%[![:space:]]*}"}"
		line="${line%"${line##*[![:space:]]}"}"
		[[ -z "${line}" ]] && continue
		COMMIT_ARRAY+=("${line}")
	done <"${COMMITS_FILE}"
elif [[ -n "${COMMITS:-}" ]]; then
	read -ra COMMIT_ARRAY <<<"${COMMITS}"
else
	echo "Error: set COMMITS (space-separated) or COMMITS_FILE (one revision per line)." >&2
	echo "Example: COMMITS=\"abc123 def456\" ${0##*/}" >&2
	exit 1
fi

if [[ "${#COMMIT_ARRAY[@]}" -eq 0 ]]; then
	echo "Error: no commits to process." >&2
	exit 1
fi

if [[ ! -x "${CHERRY_SCRIPT}" && -f "${CHERRY_SCRIPT}" ]]; then
	chmod +x "${CHERRY_SCRIPT}" || true
fi
if [[ ! -f "${CHERRY_SCRIPT}" ]]; then
	echo "Error: missing ${CHERRY_SCRIPT}" >&2
	exit 1
fi

if [[ ! -f "${LLVM_REPO}/build-amdgpu-bb.sh" ]]; then
	echo "Error: expected ${LLVM_REPO}/build-amdgpu-bb.sh" >&2
	exit 1
fi

GNU_TIME=""
if [[ -x /usr/bin/time ]]; then
	GNU_TIME=/usr/bin/time
fi

# Run "$@" under GNU time; writes one line "wall,user,sys,max_rss_kb" to stat_out.
# Propagates the child exit status. If GNU time is missing, runs without stats.
run_gnu_timed() {
	local stat_out="$1"
	shift
	if [[ -n "${GNU_TIME}" ]]; then
		"${GNU_TIME}" -o "${stat_out}" -f '%e,%U,%S,%M' -- "$@"
	else
		"$@"
	fi
}

for COMMIT in "${COMMIT_ARRAY[@]}"; do
	echo ""
	echo "================================================================================"
	echo "LLVM base revision: ${COMMIT}"
	echo "================================================================================"

	RESOLVED="$(git -C "${LLVM_REPO}" rev-parse "${COMMIT}^{commit}" 2>/dev/null || true)"
	if [[ -z "${RESOLVED}" ]]; then
		echo "Error: unknown revision in ${LLVM_REPO}: ${COMMIT}" >&2
		exit 1
	fi
	SHORT="$(git -C "${LLVM_REPO}" rev-parse --short "${RESOLVED}")"
	OUT="${OUTPUT_ROOT_BASE}/bb_coverage_commit_lines_${SHORT}"
	TEST_SUITE_OUTPUT_DIR="${OUT}/test_suite"
	ADDED_LINES_DIR="${OUT}/diff_added_lines"
	COMMIT_LINES_REPORT_DIR="${OUT}/commit_lines_report"
	RESOURCE_CSV="${OUT}/resource_stats.csv"

	mkdir -p "${OUT}"

	if [[ -z "${GNU_TIME}" ]]; then
		echo "Warning: /usr/bin/time not executable; resource_stats.csv build/test-suite CPU and RSS columns will be empty." >&2
	fi

	ITER_START_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
	ITER_START_SEC="$(date +%s)"

	BUILD_STAT=""
	TS_STAT=""
	BUILD_WALL="" BUILD_USER="" BUILD_SYS="" BUILD_RSS=""
	TS_WALL="" TS_USER="" TS_SYS="" TS_RSS=""

	echo "Output directory: ${OUT}"

	if [[ "${SKIP_CHERRY_PICK}" != "1" ]]; then
		COMMIT="${COMMIT}" "${CHERRY_SCRIPT}" "${COMMIT}"
	else
		echo "SKIP_CHERRY_PICK=1 — not running llvm_lit_coverage_cherry_pick.sh"
	fi

	if [[ "${SKIP_BUILD}" != "1" ]]; then
		echo "Building in ${LLVM_REPO} (./build-amdgpu-bb.sh) ..."
		BUILD_STAT="$(mktemp "${OUT}/.build_stats.XXXXXX")"
		run_gnu_timed "${BUILD_STAT}" bash -lc "cd \"${LLVM_REPO}\" && exec ./build-amdgpu-bb.sh"
		if [[ -n "${BUILD_STAT}" && -s "${BUILD_STAT}" ]]; then
			IFS=',' read -r BUILD_WALL BUILD_USER BUILD_SYS BUILD_RSS <"${BUILD_STAT}" || true
		fi
		rm -f "${BUILD_STAT}"
		BUILD_STAT=""
	else
		echo "SKIP_BUILD=1 — not running build-amdgpu-bb.sh"
	fi

	mkdir -p "${ADDED_LINES_DIR}" "${COMMIT_LINES_REPORT_DIR}"

	cd "${FUZZ_FILL_ROOT}"

	echo "Running test-suite coverage (symcov) ..."
	TS_STAT="$(mktemp "${OUT}/.test_suite_stats.XXXXXX")"
	run_gnu_timed "${TS_STAT}" python -m coverage test-suite \
		--output-dir "${TEST_SUITE_OUTPUT_DIR}" \
		--llvm-bin "${LLVM_BIN}" \
		--instrumented-bin "${INSTRUMENTED_BIN_DIR}" \
		--lit-filter "${FILTER}"
	if [[ -n "${TS_STAT}" && -s "${TS_STAT}" ]]; then
		IFS=',' read -r TS_WALL TS_USER TS_SYS TS_RSS <"${TS_STAT}" || true
	fi
	rm -f "${TS_STAT}"
	TS_STAT=""

	echo "Computing added-lines for ${COMMIT} ..."
	python -m diff added-lines \
		--llvm-repo "${LLVM_REPO}" \
		--commit "${COMMIT}" \
		--output-dir "${ADDED_LINES_DIR}"

	echo "Computing commit-lines report ..."
	python -m coverage commit-lines \
		--output-dir "${COMMIT_LINES_REPORT_DIR}" \
		--test-suite-output-dir "${TEST_SUITE_OUTPUT_DIR}" \
		--llvm-repo "${LLVM_REPO}" \
		--added-lines-csv "${ADDED_LINES_DIR}/added_lines.csv"

	ITER_END_SEC="$(date +%s)"
	TOTAL_WALL_SEC="$((ITER_END_SEC - ITER_START_SEC))"

	{
		printf '%s\n' 'resolved_sha,short_sha,iter_start_utc,total_wall_sec,build_wall_sec,build_user_sec,build_sys_sec,build_max_rss_kb,test_suite_wall_sec,test_suite_user_sec,test_suite_sys_sec,test_suite_max_rss_kb'
		printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
			"${RESOLVED}" "${SHORT}" "${ITER_START_ISO}" "${TOTAL_WALL_SEC}" \
			"${BUILD_WALL}" "${BUILD_USER}" "${BUILD_SYS}" "${BUILD_RSS}" \
			"${TS_WALL}" "${TS_USER}" "${TS_SYS}" "${TS_RSS}"
	} >"${RESOURCE_CSV}"

	echo "Done ${SHORT}: ${COMMIT_LINES_REPORT_DIR}/commit_lines_uncovered.csv"
	echo "Resource stats: ${RESOURCE_CSV}"
done

echo ""
echo "All commits finished."
