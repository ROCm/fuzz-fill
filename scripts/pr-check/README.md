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

# Regenerate latest.json / latest.md from state without running checks
./scripts/pr-check/check-llvm-prs.sh --report-only

# Discover, plan, run up to PR_CHECK_MAX_PER_RUN checks, and write reports
./scripts/pr-check/check-llvm-prs.sh
```

Override config path:

```bash
./scripts/pr-check/check-llvm-prs.sh --config /path/to/my-config.env
```

## What each run does

1. **Discover** — `gh search prs` for open PRs touching `llvm/lib/Target/AMDGPU` and/or `llvm/lib/Target/SPIRV`
2. **Plan** — compare against `state.json`; queue entries that are new or have a changed head SHA
3. **Check** — for each planned `(PR, backend)` pair (up to `PR_CHECK_MAX_PER_RUN`):
   - Build Docker image `fuzz-fill-test:llvm-pr-<n>-<backend>` via [`build-image-pr.sh`](../docker/build-image-pr.sh)
   - Run [`pr-cov-gaps-detection.sh`](../docker/pr-cov-gaps-detection.sh)
   - Record `gaps`, `clean`, or `failed` in state
4. **Report** — write `data/pr-check/reports/latest.json` and `latest.md`

## Output layout

| Path | Description |
|------|-------------|
| `data/pr-check/state.json` | Persistent check history keyed by `"<pr>:<backend>"` |
| `data/pr-check/runs/<pr>-<backend>/` | Per-check artifacts (`baseline/`, `commit_lines_report/`, …) |
| `data/pr-check/reports/latest.json` | Machine-readable summary of all checked PRs |
| `data/pr-check/reports/latest.md` | Human-readable gap report with PR links |
| `data/pr-check/reports/runs/<timestamp>.json` | Snapshot from each report generation |

A PR has **coverage gaps** when `target_lines_uncovered.csv` is non-empty (added lines not covered by the regression suite).

## Cron example

```cron
# Every 6 hours: run at most one PR/backend check, then refresh reports
0 */6 * * * cd /path/to/fuzz-fill && ./scripts/pr-check/check-llvm-prs.sh >> /var/log/fuzz-fill-pr-check.log 2>&1
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

The orchestrator wraps [`scripts/pr_check/checker.py`](../pr_check/checker.py):

```bash
PYTHONPATH=scripts python3 -m pr_check discover
PYTHONPATH=scripts python3 -m pr_check plan --state-file data/pr-check/state.json
PYTHONPATH=scripts python3 -m pr_check report \
  --state-file data/pr-check/state.json \
  --report-dir data/pr-check/reports
```
