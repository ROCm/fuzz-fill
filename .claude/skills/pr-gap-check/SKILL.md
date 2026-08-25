---
name: pr-gap-check
description: >-
  Force a fuzz-fill coverage-gap analysis on one specific llvm/llvm-project
  PR, regardless of whether it's been reviewed before. Use when asked to
  "check PR <N> for gaps", "run gap analysis on this PR", or similar for a
  single named PR.
---

# PR gap check (single PR, forced)

Same machinery as [pr-gap-scan](../pr-gap-scan/SKILL.md), but for exactly one
PR the user names, and it **forces** the analysis: it does not skip PRs that
already have a fuzz-fill comment, and it clears any prior run recorded for
that PR so a fresh CI job is always dispatched — it also skips pr-gap-scan's
artifact-reuse cache check (never reuses an existing artifact from a
matching prior run, even if one exists for the same commit). Everything
else — gap-finding-only dispatch, incremental polling/artifact
download, filtering `llvm_unreachable`/`assert(` lines, and drafting a
comment — is identical, including the drift check: since CI can take a long
time, the draft comment re-checks the PR's live head against the commit the
artifact was actually analyzed against, and prepends a warning if the PR has
moved on.

This reuses `../pr-gap-scan/scripts/scan.py` directly (`target` subcommand
force-adds the PR as the sole candidate; `run --pr <N>` does the full
pipeline in one shot). There's nothing to duplicate here — read
[pr-gap-scan/SKILL.md](../pr-gap-scan/SKILL.md) for the full pipeline
description, comment template, and prerequisites.

## Usage

```bash
SCAN=.claude/skills/pr-gap-scan/scripts/scan.py
STATE=./data/pr-gap-check/pr-<N>/state.json
ARTIFACTS=./data/pr-gap-check/pr-<N>/artifacts
COMMENTS=./data/pr-gap-check/pr-<N>/comments

python3 "$SCAN" run \
  --state "$STATE" \
  --pr <N> \
  --artifacts-dir "$ARTIFACTS" \
  --out-dir "$COMMENTS"
```

Backend(s) are auto-detected from the PR's changed files (same
`llvm/lib/Target/AMDGPU/` / `llvm/lib/Target/SPIRV/` path match as
pr-gap-scan). If the PR doesn't touch those paths — or you want to force a
specific backend regardless — pass one or more `--backend {amdgpu,spirv}`
flags explicitly:

```bash
python3 "$SCAN" run --state "$STATE" --pr <N> --backend amdgpu \
  --artifacts-dir "$ARTIFACTS" --out-dir "$COMMENTS"
```

Step-by-step (to inspect `$STATE` between phases, e.g. while a long CI build
is running):

```bash
python3 "$SCAN" target   --state "$STATE" --pr <N>
python3 "$SCAN" dispatch --state "$STATE"
python3 "$SCAN" process  --state "$STATE" --artifacts-dir "$ARTIFACTS" \
  --out-dir "$COMMENTS" --poll-interval 60
```

Output is `$COMMENTS/pr-<N>.md` if the PR has real (non-trivial) uncovered
lines, or nothing if it doesn't. As with pr-gap-scan, this is a **draft only**
— review it and post it yourself with `gh pr comment <N> -R llvm/llvm-project
--body-file "$COMMENTS/pr-<N>.md"`; always confirm with the user before
posting to someone else's PR.
