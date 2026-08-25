#!/usr/bin/env bash
# Batch gap-fill from completed pr-check runs using candidate-tests-dataset.
#
# Runs one Docker gap-filling job per PR/backend pair (matching pr-check artifacts).
# See scripts/gap_fill_from_gaps_expanded.py for gap prep and aggregation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

GAPS_EXPANDED_CSV=""
PR_CHECK_RUNS_ROOT="${REPO_ROOT}/data/pr-check/runs"
INPUTS_ROOT="${REPO_ROOT}/data/gap-fill/inputs"
OUTPUTS_ROOT="${REPO_ROOT}/data/gap-fill/runs"
REPORT_CSV="${REPO_ROOT}/data/gap-fill/reports/gaps-filled.csv"
CANDIDATE_TESTS_ROOT="${REPO_ROOT}/candidate-tests-dataset"
MANIFEST_CSV="${INPUTS_ROOT}/manifest.csv"
JOBS="${JOBS:-$(nproc)}"
IMAGE_NAME="${IMAGE_NAME:-fuzz-fill-test}"

DO_PREPARE=1
DO_RUN=1
DO_AGGREGATE=1
PR_FILTER=""
RESUME=0
GLOBAL_SETTINGS_CSV=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Prepare per-PR gap lists from completed pr-check runs, run Docker gap-filling for each
PR/backend pair, and aggregate results.

Steps (all enabled by default):
  1. prepare  - scan data/pr-check/runs/, write gap-lines.csv + manifest.csv
  2. run      - invoke scripts/docker/gap-filling.sh --bind-repo for each manifest row
  3. aggregate - write data/gap-fill/reports/gaps-filled.csv

Options:
  --gaps-expanded-csv <path>     Optional legacy CSV input (default: read pr-check runs)
  --pr-check-runs-root <path>    pr-check run artifacts (default: data/pr-check/runs)
  --inputs-root <path>           Prepared gap-line CSVs (default: data/gap-fill/inputs)
  --outputs-root <path>          Gap-fill outputs (default: data/gap-fill/runs)
  --report-csv <path>            Aggregated report (default: data/gap-fill/reports/gaps-filled.csv)
  --candidate-tests-dir <path>   Corpus root (default: candidate-tests-dataset)
  -j, --jobs <n>                 Parallel jobs for candidate-test (default: nproc)
  --pr <number>                  Run only this PR number (repeatable)
  --resume                         Keep existing candidate_tests/; run only new flag variants
  --settings-csv <path>            Override per-PR settings from manifest (all PRs)
  --prepare-only                 Only write gap-lines.csv + manifest.csv
  --run-only                     Only run Docker gap-filling (manifest must exist)
  --aggregate-only               Only aggregate existing outputs
  --skip-prepare
  --skip-run
  --skip-aggregate
  -h, --help                     Show this help

Examples:
  cd ${REPO_ROOT}
  ./scripts/gap-fill-from-gaps-expanded.sh

  ./scripts/gap-fill-from-gaps-expanded.sh --prepare-only
  ./scripts/gap-fill-from-gaps-expanded.sh --run-only --resume -j "\$(nproc)"
  ./scripts/gap-fill-from-gaps-expanded.sh --aggregate-only

  ./scripts/gap-fill-from-gaps-expanded.sh --pr 214936 --pr 215572
EOF
}

resolve_pr_image() {
    local pr_number="$1"
    local backend="$2"
    local tagged="${IMAGE_NAME}:llvm-pr-${pr_number}-${backend}"
    local plain="${IMAGE_NAME}:llvm-pr-${pr_number}"

    if docker image inspect "$tagged" >/dev/null 2>&1; then
        printf '%s\n' "$tagged"
        return 0
    fi
    if docker image inspect "$plain" >/dev/null 2>&1; then
        printf '%s\n' "$plain"
        return 0
    fi

    echo "error: Docker image not found (tried ${tagged} and ${plain})" >&2
    echo "hint: build with scripts/docker/build-image-pr.sh --pr-id ${pr_number} --allowlist ${backend}" >&2
    return 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --gaps-expanded-csv)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            GAPS_EXPANDED_CSV="$2"
            shift 2
            ;;
        --pr-check-runs-root)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            PR_CHECK_RUNS_ROOT="$2"
            shift 2
            ;;
        --inputs-root)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            INPUTS_ROOT="$2"
            MANIFEST_CSV="${INPUTS_ROOT}/manifest.csv"
            shift 2
            ;;
        --outputs-root)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            OUTPUTS_ROOT="$2"
            shift 2
            ;;
        --report-csv)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            REPORT_CSV="$2"
            shift 2
            ;;
        --candidate-tests-dir)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            CANDIDATE_TESTS_ROOT="$2"
            shift 2
            ;;
        -j|--jobs)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            JOBS="$2"
            shift 2
            ;;
        --pr)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            if [[ -n "$PR_FILTER" ]]; then
                PR_FILTER="${PR_FILTER},${2}"
            else
                PR_FILTER="$2"
            fi
            shift 2
            ;;
        --resume)
            RESUME=1
            shift
            ;;
        --settings-csv)
            [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
            GLOBAL_SETTINGS_CSV="$2"
            shift 2
            ;;
        --prepare-only)
            DO_PREPARE=1
            DO_RUN=0
            DO_AGGREGATE=0
            shift
            ;;
        --run-only)
            DO_PREPARE=0
            DO_RUN=1
            DO_AGGREGATE=0
            shift
            ;;
        --aggregate-only)
            DO_PREPARE=0
            DO_RUN=0
            DO_AGGREGATE=1
            shift
            ;;
        --skip-prepare)
            DO_PREPARE=0
            shift
            ;;
        --skip-run)
            DO_RUN=0
            shift
            ;;
        --skip-aggregate)
            DO_AGGREGATE=0
            shift
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

validate_jobs "$JOBS"

if [[ "$DO_PREPARE" -eq 1 ]] && [[ -z "$GAPS_EXPANDED_CSV" ]] && [[ ! -d "$PR_CHECK_RUNS_ROOT" ]]; then
    echo "error: pr-check runs root not found: ${PR_CHECK_RUNS_ROOT}" >&2
    exit 1
fi

if [[ -n "$GAPS_EXPANDED_CSV" ]] && [[ "$DO_PREPARE" -eq 1 ]] && [[ ! -f "$GAPS_EXPANDED_CSV" ]]; then
    echo "error: gaps-expanded CSV not found: ${GAPS_EXPANDED_CSV}" >&2
    exit 1
fi

if [[ ! -d "$CANDIDATE_TESTS_ROOT" ]] && [[ "$DO_RUN" -eq 1 ]]; then
    echo "error: candidate tests directory not found: ${CANDIDATE_TESTS_ROOT}" >&2
    exit 1
fi

cd "$REPO_ROOT"

if [[ "$DO_PREPARE" -eq 1 ]]; then
    echo "=== prepare gap-line inputs ==="
    prepare_args=(
        --pr-check-runs-root "$PR_CHECK_RUNS_ROOT"
        --inputs-root "$INPUTS_ROOT"
        --outputs-root "$OUTPUTS_ROOT"
    )
    if [[ -n "$GAPS_EXPANDED_CSV" ]]; then
        prepare_args+=(--gaps-expanded-csv "$GAPS_EXPANDED_CSV")
    fi
    python3 "${SCRIPT_DIR}/gap_fill_from_gaps_expanded.py" prepare "${prepare_args[@]}"
fi

if [[ "$DO_RUN" -eq 1 ]]; then
    if [[ ! -f "$MANIFEST_CSV" ]]; then
        echo "error: manifest not found: ${MANIFEST_CSV} (run with --prepare-only first)" >&2
        exit 1
    fi

    echo "=== run Docker gap-filling ==="
    while IFS=$'\t' read -r pr_number backend gap_count gap_lines_csv llc_map_csv corpus_subdir settings_csv output_dir; do
        incremental_only=0
        if [[ -n "$PR_FILTER" ]] && ! echo ",${PR_FILTER}," | grep -q ",${pr_number},"; then
            continue
        fi

        if [[ -n "$GLOBAL_SETTINGS_CSV" ]]; then
            settings_csv="$GLOBAL_SETTINGS_CSV"
        fi

        candidate_dir="${CANDIDATE_TESTS_ROOT}/${corpus_subdir}"
        if [[ ! -d "$candidate_dir" ]]; then
            echo "error: candidate corpus subdir not found: ${candidate_dir}" >&2
            exit 1
        fi

        if [[ -z "$settings_csv" ]] || [[ ! -f "$settings_csv" ]]; then
            if [[ "$RESUME" -eq 1 ]] && [[ -d "${output_dir}/candidate_tests" ]]; then
                echo
                echo "--- PR ${pr_number} (${backend}): no new settings; incremental only ---"
                incremental_only=1
            else
                echo "warning: skipping PR ${pr_number} (${backend}): no settings CSV" >&2
                continue
            fi
        else
            incremental_only=0
        fi

        image_ref="$(resolve_pr_image "$pr_number" "$backend")"

        echo
        echo "--- PR ${pr_number} (${backend}): ${gap_count} gap line(s) ---"
        if [[ -n "$settings_csv" ]] && [[ -f "$settings_csv" ]]; then
            echo "Settings: ${settings_csv}"
        fi
        echo "Using image: ${image_ref}"

        gap_fill_args=(
            --bind-repo
            --image "$image_ref"
            --output-dir "$output_dir"
            --line-coverage-uncovered-csv "$gap_lines_csv"
            --llc-address-line-map-csv "$llc_map_csv"
            --candidate-tests-dir "$candidate_dir"
            -j "$JOBS"
        )
        if [[ "$RESUME" -eq 1 ]]; then
            gap_fill_args+=(--resume)
        fi
        if [[ "${incremental_only:-0}" -eq 1 ]]; then
            gap_fill_args+=(--incremental-only)
        fi
        if [[ -n "$settings_csv" ]] && [[ -f "$settings_csv" ]]; then
            gap_fill_args+=(--settings-csv "$settings_csv")
        fi
        "${SCRIPT_DIR}/docker/gap-filling.sh" "${gap_fill_args[@]}"
    done < <(
        PR_FILTER="$PR_FILTER" python3 - "$MANIFEST_CSV" <<'PY'
import csv
import os
import sys

manifest = sys.argv[1]
pr_filter = {
    value.strip()
    for value in os.environ.get("PR_FILTER", "").split(",")
    if value.strip()
}

with open(manifest, encoding="utf-8", newline="") as handle:
    for row in csv.DictReader(handle):
        if pr_filter and row["pr_number"] not in pr_filter:
            continue
        print(
            "\t".join(
                [
                    row["pr_number"],
                    row["backend"],
                    row["gap_count"],
                    row["gap_lines_csv"],
                    row["llc_address_line_map_csv"],
                    row["candidate_tests_subdir"],
                    row.get("settings_csv", ""),
                    row["output_dir"],
                ]
            )
        )
PY
    )
fi

if [[ "$DO_AGGREGATE" -eq 1 ]]; then
    echo
    echo "=== aggregate results ==="
    python3 "${SCRIPT_DIR}/gap_fill_from_gaps_expanded.py" aggregate \
        --manifest "$MANIFEST_CSV" \
        --outputs-root "$OUTPUTS_ROOT" \
        --report "$REPORT_CSV"
fi

echo
echo "Done."
