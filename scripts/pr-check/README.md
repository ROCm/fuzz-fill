# Periodic LLVM PR coverage gap checking

Automatically discover open AMDGPU and SPIR-V PRs on `llvm/llvm-project`, run [Workflow 2](../docker/pr-cov-gaps-detection.sh) coverage-gap detection when a PR's head SHA changes, and write local reports under `data/pr-check/reports/`.

## Prerequisites

- [Docker](https://docs.docker.com/) with BuildKit
- [GitHub CLI](https://cli.github.com/) (`gh auth login`)
- `git`
- A local `llvm-project` clone (used as a reference for faster PR fetches; PR content is fetched from GitHub)
- Python 3.10+ with fuzz-fill dependencies installed (`pip install -e .`)

## One-time setup

```bash
cp scripts/pr-check/config.example.env scripts/pr-check/config.env
# Edit config.env and set LLVM_REPO
```

`config.env` is local-only (not committed). Paths in the example are relative to the fuzz-fill repo root.

## Usage

Run from the fuzz-fill repo root:

```bash
# List open PRs touching AMDGPU or SPIR-V target paths
./scripts/pr-check/check-llvm-prs.sh --discover-only

# Show planned work (PR/backend pairs needing a fresh check)
./scripts/pr-check/check-llvm-prs.sh --plan-only

# Refresh latest.json / latest.md from state (no checks, no LLVM_REPO needed)
./scripts/pr-check/get-latest.sh

# Same as get-latest.sh, via the main orchestrator flag
./scripts/pr-check/check-llvm-prs.sh --report-only

# Discover, plan, run up to PR_CHECK_MAX_PER_RUN checks, and write reports
./scripts/pr-check/check-llvm-prs.sh

# AMDGPU only, or drain all pending checks in one run
./scripts/pr-check/check-llvm-prs.sh --backends amdgpu
./scripts/pr-check/check-llvm-prs.sh --backends amdgpu --drain-queue
```

Override config path:

```bash
./scripts/pr-check/check-llvm-prs.sh --config /path/to/my-config.env
```

Daily cron entry point (AMDGPU only, drains the full queue):

```bash
./scripts/pr-check/run-daily-amdgpu.sh
```

## What each run does

1. **Discover** — `gh search prs` for open PRs with label `backend:AMDGPU` and/or `backend:SPIRV`, then keep only those with changed files under `llvm/lib/Target/AMDGPU/` or `llvm/lib/Target/SPIRV/`
2. **Plan** — compare against `state.json`; queue entries that are new or have a changed head SHA
3. **Check** — for each planned `(PR, backend)` pair (up to `PR_CHECK_MAX_PER_RUN`):
   - Build Docker image `fuzz-fill-test:llvm-pr-<n>-<backend>` via [`build-image-pr.sh`](../docker/build-image-pr.sh)
   - Run [`pr-cov-gaps-detection.sh`](../docker/pr-cov-gaps-detection.sh)
   - Record `gaps`, `clean`, or `failed` in state
4. **Report** — write `data/pr-check/reports/latest.json`, `latest.md`, and `new-prs.md`

### CLI options

| Flag / env var | Default | Purpose |
|----------------|---------|---------|
| `--backends` / `PR_CHECK_BACKENDS` | amdgpu, spirv | Limit discovery to specific backends |
| `--max-age-days` / `PR_CHECK_MAX_AGE_DAYS` | 14 | Only PRs opened within the last N days |
| `--max-per-run` / `PR_CHECK_MAX_PER_RUN` | 1 | Max checks per invocation (ignored with `--drain-queue`) |
| `--drain-queue` | off | Process all pending checks one at a time until empty |
| `--keep-raw-sancov` / `PR_CHECK_KEEP_RAW_SANCOV` | off | Keep `baseline/raw_sancov` after each check (removed by default) |

## Output layout

| Path | Description |
|------|-------------|
| `data/pr-check/state.json` | Persistent check history keyed by `"<pr>:<backend>"` |
| `data/pr-check/runs/<pr>-<backend>/` | Per-check artifacts (`baseline/`, `commit_lines_report/`, …) |
| `data/pr-check/reports/latest.json` | Machine-readable summary of all checked PRs |
| `data/pr-check/reports/latest.md` | Human-readable gap report with PR links |
| `data/pr-check/reports/new-prs.md` | PRs new or updated since the previous report (diff vs prior `latest.json`) |
| `data/pr-check/reports/runs/<timestamp>.json` | Snapshot from each report generation |

A PR has **coverage gaps** when `target_lines_uncovered.csv` is non-empty (added lines not covered by the regression suite).

## Refreshing reports

Reports are built from `state.json`, not by scanning `runs/`. After a failed or interrupted check run, or anytime you want the summary synced to current state:

```bash
./scripts/pr-check/get-latest.sh
```

Use this when `latest.md` looks stale (e.g. fewer entries than `state.json`, or checks finished but the orchestrator exited early). The markdown body lists only PRs **with gaps**; clean PRs appear in the summary line and in `latest.json`. The same refresh also updates `new-prs.md` by diffing the current state against the previous `latest.json` — useful after an interrupted run where checks completed but report generation did not.

### Rebuilding `state.json` from run artifacts

If `state.json` is missing or corrupted (for example after a disk-full write), rebuild it from completed directories under `data/pr-check/runs/` without re-running coverage checks:

```bash
# Preview what would be written
./scripts/pr-check/rebuild-state.sh --dry-run

# Rebuild state, then refresh reports
./scripts/pr-check/rebuild-state.sh
./scripts/pr-check/get-latest.sh
```

The rebuild:

1. Scans `data/pr-check/runs/<pr>-<backend>/` and skips incomplete directories (no `commit_lines_report/target_lines_uncovered.csv`).
2. Recomputes `gap_count`, `lit_failure_count`, and `status` from on-disk artifacts.
3. Fills `title`, `head_sha`, and `checked_at` from `reports/latest.json` and `reports/runs/*.json` when available.
4. Falls back to `gh pr view` for any remaining runs (uses the **current** PR head SHA — if a PR was updated after the run, `--plan-only` may queue a re-check).

Incomplete or empty run directories (for example a check interrupted before detection finished) are skipped and are not added to state.

The main orchestrator also refreshes reports at normal exit. An EXIT trap regenerates the report if at least one check ran but the process did not finish cleanly (Ctrl+C, OOM, or unexpected early exit during `--drain-queue`).

## Daily AMDGPU cron

For a once-daily job that checks all pending AMDGPU PRs opened within the last 14 days:

### One-time setup

```bash
cp scripts/pr-check/config.example.env scripts/pr-check/config.env
# Set LLVM_REPO to an absolute path (required for cron)
# Ensure gh auth login and Docker work for the cron user
pip install -e .
```

`config.env` is local-only (not committed). Use absolute paths in cron configs.

### Test before scheduling

```bash
# See what would run (no LLVM builds)
./scripts/pr-check/check-llvm-prs.sh \
  --config scripts/pr-check/config.env \
  --backends amdgpu \
  --plan-only

# Full daily run (builds LLVM Docker images — can take hours on first backfill)
./scripts/pr-check/run-daily-amdgpu.sh
```

### Install cron

See [`cron/amdgpu-daily.example`](cron/amdgpu-daily.example) for a ready-to-edit crontab snippet. Typical install:

```bash
crontab -e
# Add the line from cron/amdgpu-daily.example (with your paths)
```

The wrapper [`run-daily-amdgpu.sh`](run-daily-amdgpu.sh) appends logs to `logs/pr-check/amdgpu-daily.log` (gitignored, no sudo required) and uses `flock` to skip if a prior run is still going.

### Expected behavior

| Run | What happens |
|-----|--------------|
| **First daily run** | Discovers all open AMDGPU PRs from the last 14 days; checks every PR not yet in `state.json` (or with a changed head SHA). May take many hours. |
| **Subsequent days** | Same 14-day discovery window, but most PRs are skipped (unchanged SHA). Only new or updated PRs are checked. |

Results land in `data/pr-check/reports/latest.md`.

## Lightweight polling cron

For frequent runs that process one PR at a time (both backends):

```cron
# Every 6 hours: run at most one PR/backend check, then refresh reports
0 */6 * * * cd /path/to/fuzz-fill && ./scripts/pr-check/check-llvm-prs.sh >> logs/pr-check/polling.log 2>&1
```

Keep `PR_CHECK_MAX_PER_RUN=1` unless you have enough CPU/time for multiple LLVM Docker builds per invocation.

## systemd timer example

`/etc/systemd/system/fuzz-fill-pr-check.service`:

```ini
[Unit]
Description=fuzz-fill periodic LLVM PR coverage gap check

[Service]
Type=oneshot
WorkingDirectory=/path/to/fuzz-fill
ExecStart=/path/to/fuzz-fill/scripts/pr-check/check-llvm-prs.sh
User=your-user
```

`/etc/systemd/system/fuzz-fill-pr-check.timer`:

```ini
[Unit]
Description=Run fuzz-fill PR coverage checks every 6 hours

[Timer]
OnCalendar=*-*-* 00,06,12,18:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable with:

```bash
sudo systemctl enable --now fuzz-fill-pr-check.timer
```

## Low-level CLI

The orchestrator wraps [`src/pr_check/checker.py`](../../src/pr_check/checker.py):

```bash
PYTHONPATH=src python3 -m pr_check discover
PYTHONPATH=src python3 -m pr_check plan --state-file data/pr-check/state.json
PYTHONPATH=src python3 -m pr_check report \
  --state-file data/pr-check/state.json \
  --report-dir data/pr-check/reports
```
