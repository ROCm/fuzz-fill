---
name: pr-gap-scan
description: >-
  Scan recent llvm/llvm-project PRs touching the AMDGPU/SPIRV backends for
  fuzz-fill coverage gaps, and draft review comments for the ones that have
  real (non-trivial) uncovered lines. Use when asked to "scan PRs for gaps",
  "run the PR gap scan", or similar.
---

# PR gap scan

Finds recently-active llvm/llvm-project PRs touching the AMDGPU/SPIRV
backends, runs fuzz-fill's PR gap-finding CI job against each, and drafts a
review comment (as a local file, never posted automatically) for every PR
that has real uncovered lines.

All of the logic lives in `scripts/scan.py` (stdlib-only, no venv needed).
It's a resumable, multi-hour pipeline — dispatched CI runs build LLVM from
scratch and can each take tens of minutes — so it's driven by a JSON state
file rather than kept in the conversation. Re-running the same command is
always safe; completed phases are skipped.

## Pipeline

1. **discover** — list open PRs in `llvm/llvm-project`, most-recently-updated
   first, and keep the first `--limit` (default 20) **per backend** whose
   changed files touch `llvm/lib/Target/AMDGPU/` or `llvm/lib/Target/SPIRV/`
   — i.e. up to 20 AMDGPU PRs and up to 20 SPIRV PRs, not 20 total. Pass one
   or more `--backend {amdgpu,spirv}` to scan only that backend (default:
   both). A PR touching both backends counts against both quotas, but only
   lists the backend(s) that still had room when it was found (so a backend
   past its limit doesn't get analyzed for that PR). A PR is dropped if
   fuzz-fill already left a comment on it (body contains "fuzz-fill",
   case-insensitive) and no commit has landed since that comment. Each kept
   candidate records its head SHA and which backend(s) it touches.
2. **dispatch** — for each candidate PR x backend not forced (see
   [pr-gap-check](../pr-gap-check/SKILL.md)), first checks whether a prior
   successful run already analyzed this exact PR/commit/backend: it looks up
   past `pr-gap-analysis.yml` runs matching this PR and backend, and for each
   checks its `pr-head-pr<N>-<run_id>` artifact (published early in that run)
   against the candidate's current head SHA. A match means the existing
   `gap-finding-pr<N>-<run_id>` artifact is reused — no new job is scheduled.
   If a matching run's artifacts don't fit the expected
   `gap-finding-pr<N>-<run_id>` / `pr-head-pr<N>-<run_id>` naming (e.g. the
   workflow's artifact names changed), this logs a warning and falls back to
   scheduling a fresh run rather than silently skipping the check. Otherwise,
   triggers `pr-gap-analysis.yml` on `ROCm/fuzz-fill` via `gh workflow run`
   with `run_gap_filling=false` (gap finding only, per the ask — no gap
   filling) and resolves/records the new run ID.
3. **process** — polls all dispatched runs, but doesn't wait for the whole
   batch: each polling cycle it refreshes run statuses, downloads (collects)
   the `gap-finding-pr<N>-<run_id>` artifact for any run that just completed
   successfully, and immediately drafts the comment for any PR whose *every*
   backend run has now reached a terminal state — without waiting on any
   other PR's still-running jobs. It reads
   `commit_lines_report/target_lines_uncovered.csv` from each artifact,
   merges lines across backends for the same PR, fetches each line's actual
   source text from
   `raw.githubusercontent.com/llvm/llvm-project/<pr_head>/<file>`, and drops
   any line whose text contains `llvm_unreachable` or `assert(` — those
   aren't meaningful gaps. If anything survives, re-checks the PR's *current*
   head against the `pr_head` the artifact was actually analyzed against
   (CI can take a long time — the PR may have gained new commits since it was
   dispatched); if they differ, prepends a drift warning to the file. It also
   checks each backend's artifact for a `README-WARNING` file (written by the
   workflow when LIT tests failed during that backend's baseline coverage
   run) and prepends a warning block for each affected backend if so. It also
   re-fetches the PR's current base branch and, if it isn't the repo's
   default branch, prepends a stacked-PR warning (see "Stacked PRs" below).
   Then writes the draft comment for that PR to `--out-dir/pr-<N>.md` using
   the template below. PRs where everything was filtered out get no file.
   The loop keeps polling until every dispatched run is terminal.

Run all three phases in one go with `run`, or step through them individually
(useful for resuming or debugging). `collect` and `comment` also remain
available standalone for manual/debugging use (e.g. re-running `comment`
after tweaking the trivial-line filter without re-running CI) — `process` is
just the two of them driven incrementally off the polling loop instead of a
one-shot pass after everything finishes.

To force the analysis on one specific PR regardless of discovery filters
(e.g. it was already commented on, or doesn't touch a backend path), use the
[pr-gap-check](../pr-gap-check/SKILL.md) skill instead — same script, `target`
subcommand.

## Usage

```bash
STATE=./data/pr-gap-scan/$(date -u +%Y%m%d)/state.json
ARTIFACTS=./data/pr-gap-scan/$(date -u +%Y%m%d)/artifacts
COMMENTS=./data/pr-gap-scan/$(date -u +%Y%m%d)/comments

python3 .claude/skills/pr-gap-scan/scripts/scan.py run \
  --state "$STATE" \
  --artifacts-dir "$ARTIFACTS" \
  --out-dir "$COMMENTS"
```

The `$(date ...)` above is just so a fresh invocation lands in a new
directory; to resume a specific in-flight scan, reuse its existing
`--state` path instead of generating a new one.

Step-by-step equivalent (same effect, useful when you want to inspect
`$STATE` between phases):

```bash
SCAN=.claude/skills/pr-gap-scan/scripts/scan.py
python3 "$SCAN" discover --state "$STATE" --limit 20
# Or, to scan only one backend (e.g. asked to "just check AMDGPU"):
python3 "$SCAN" discover --state "$STATE" --limit 20 --backend amdgpu
python3 "$SCAN" dispatch --state "$STATE"
python3 "$SCAN" process  --state "$STATE" --artifacts-dir "$ARTIFACTS" \
  --out-dir "$COMMENTS" --poll-interval 60
```

Since `dispatch`/`process` are idempotent against `$STATE`, it's safe to run
`process` again later (e.g. in a follow-up session) if CI is still running —
it picks up the same run IDs and keeps polling/drafting as remaining PRs
finish (PRs already ready get their comment file re-written, which is
harmless).

### After the run

The comment files under `--out-dir` are **drafts only** — nothing gets
posted automatically. Check whether the file has a drift warning, a LIT test
failure warning, or a stacked-PR warning at the top first (see below); if it
does, re-run the analysis (drift), double-check the failing tests (LIT), or
confirm the base branch/PR is settled (stacked) before trusting the
findings. Otherwise, review each `pr-<N>.md`, and if it looks right, post it
yourself:

```bash
gh pr comment <N> -R llvm/llvm-project --body-file "$COMMENTS/pr-<N>.md"
```

Posting is a visible, hard-to-fully-undo action on someone else's PR —
always confirm with the user before running `gh pr comment`, even if the
scan itself ran unattended.

## Comment template

Each `pr-<N>.md` starts with a title line (not part of the comment itself —
just so opening the file lets you jump straight to the PR), then the
message:

```
# [#218649](https://github.com/llvm/llvm-project/pull/218649) — [AMDGPU] MC support for indexed VBUFFER resources for gfx13

Hi! This comment was generated using [fuzz-fill](https://github.com/ROCm/fuzz-fill), a new tool we're building to help improve LLVM test coverage by spotting lines introduced in a PR that don't yet appear to be exercised by the full test suite, including any tests added in this PR.

Looking at PR head 9f967d998a20, we found 1 line added or modified here that we couldn't find a test for:

1. https://github.com/llvm/llvm-project/blob/9f967d998a2073e2e3c3c527a49f2e2bf26c391d/llvm/lib/Target/AMDGPU/AMDGPUISelDAGToDAG.cpp#L4405

If it makes sense, adding a regression test that validates these lines would be great. And if any of them are already tested and we missed it, we'd love to hear so we can improve the tool. Feel free to give us some feedback on whether this review was useful from your perspective. Thanks!
```

The prose uses the short (12-char) SHA, deliberately without backticks —
GitHub autolinks bare hex commit SHAs to the commit page on its own, and
backticks would suppress that. Permalinks use the full 40-char SHA (the
PR's head commit, from `README-finding.txt`'s `pr_head`, not the squashed
commit `gap-finding-pr.sh` builds against). The title line above the message
is generated from the PR's own title/URL and should be stripped if you post
the file's body as-is with `gh pr comment --body-file` — it's there for the
person reading the draft, not for the PR itself.

If the PR has picked up new commits since the artifact's `pr_head` (checked
live at comment-writing time), the file gets an extra block prepended above
the message, wrapped in `<!-- -->` so GitHub hides it if the file is ever
posted verbatim, but still visible to whoever opens the raw file:

```
<!-- fuzz-fill internal note: do not post this block, GitHub hides HTML comments when rendering so it won't show up if you do, but strip it if you're posting the body some other way. -->
> [!WARNING]
> PR #<N> has drifted since this analysis ran. It was analyzed against commit `<short>` (`<full>`), but the PR's current tip is `<short>` (`<full>`). The uncovered lines below may be stale -- re-run the analysis (pr-gap-check's `target` subcommand forces a fresh run) before posting.
<!-- end internal note -->
```

Similarly, if any backend's CI run reported LIT test failures during its
baseline coverage pass (the workflow tolerates these — `LIT_ALLOW_FAILURES`
— rather than aborting the job, and stages the resulting `README-WARNING`
file into the artifact if so), the file gets another hidden block, one
`[!WARNING]` per affected backend:

```
<!-- fuzz-fill internal note: do not post this block, GitHub hides HTML comments when rendering so it won't show up if you do, but strip it if you're posting the body some other way. -->
> [!WARNING]
> **amdgpu**:
> WARNING: 3 LIT test(s) failed during the baseline run (e.g., failed a check, timed out, unresolved, or unexpectedly passed).
> Failed tests may lead to an incomplete coverage profile. As a result,
> target_lines_uncovered.csv may report lines as uncovered even though they are
> actually covered by a (failing) test.
> Review baseline/lit_failures.json for the list of failing tests.
<!-- end internal note -->
```

This means the coverage baseline may be incomplete — some of the "uncovered"
lines below could actually be covered by a test that failed for an unrelated
reason. Treat findings alongside this warning with extra skepticism before
posting; the artifact's `out/baseline/lit_failures.json` has the full list
of failing tests if you want to check further.

Finally, if the PR is **stacked** (see below), the file gets a third hidden
block, placed above the other two since it's a structural fact about the PR
rather than an analysis-run caveat:

```
<!-- fuzz-fill internal note: do not post this block, GitHub hides HTML comments when rendering so it won't show up if you do, but strip it if you're posting the body some other way. -->
> [!WARNING]
> PR #<N> looks stacked: its base branch is `<base_ref>`, not the repository's default branch (`<default_branch>`), which is itself still-open PR #<M> ('<title>'). The gap analysis only considered lines unique to this PR (diffed against its merge-base), but that merge-base will move if the base branch gets amended or rebased before it merges -- which can invalidate this analysis without this PR's own head commit ever changing, so the drift check (which only compares this PR's own head commit) wouldn't catch it. Confirm the base PR/branch is settled before trusting these findings.
<!-- end internal note -->
```

### Stacked PRs

A PR is considered **stacked** if its base branch (re-fetched live, at
comment-writing time) isn't the repository's default branch (`main` for
`llvm/llvm-project`) — i.e. it's opened against another branch rather than
trunk, which on GitHub is the standard way to build one PR on top of another
still-unmerged one. This is detected with two API calls per candidate at
comment time: `GET /repos/{repo}` for the default branch (cached per repo for
the run), and `GET /repos/{repo}/pulls?head={owner}:{base_ref}` to see if
that base branch is itself another open PR's head (named in the warning if
so; otherwise it's noted as unmatched — could be a maintenance branch, or
the base PR already merged without this one being retargeted yet).

The reason this matters: `gap-finding-pr.sh` computes "added lines" as a diff
against this PR's own merge-base with its base branch, so it correctly
isolates just this PR's unique changes even when stacked — that part isn't
the problem. The problem is that the merge-base itself is unstable: if the
(still open, still-being-reviewed) base branch gets amended or rebased
before it merges, the analysis silently goes stale without this PR's own
head SHA ever changing, so the existing drift check (which only compares
this PR's head commit) has no way to catch it.

## Assumptions (revisit if wrong)

- Only **open** PRs are scanned (draft PRs included) — merged/closed PRs
  aren't actionable for a "please add a test" comment.
- "Introduces changes in the backend" is matched on source paths
  `llvm/lib/Target/AMDGPU/` and `llvm/lib/Target/SPIRV/` only (not test
  directories) — that's what determines whether the backend build is
  exercised at all.
- The already-commented filter matches any comment (any author) whose body
  contains "fuzz-fill" case-insensitively — adjust
  `already_reviewed_without_new_commits()` in `scan.py` if fuzz-fill comments
  should instead be identified by a specific bot account.
- The workflow currently only exists on the `users/mgcarrasco/manual-workflow`
  branch of `ROCm/fuzz-fill` (`--ref` default). Update the default (or pass
  `--ref main`) once `pr-gap-analysis.yml` merges to `main`.
- "Uncovered lines" always come from the gap-**finding** artifact
  (`out/commit_lines_report/target_lines_uncovered.csv`); gap filling is
  intentionally skipped (`run_gap_filling=false`) per the ask.

## Prerequisites

- `gh` CLI authenticated with access to both `llvm/llvm-project` (read) and
  `ROCm/fuzz-fill` (`actions:write` to dispatch workflows, and read access to
  runs/artifacts).
- Network access to `raw.githubusercontent.com` for the trivial-line filter.
- No Python packages beyond the standard library.
