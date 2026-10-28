---
name: pr-gap-scan-clang
description: >-
  Scan recent llvm/llvm-project PRs labeled for clang frontend, codegen,
  driver, analysis, static analyzer, bytecode, dataflow, or modules for
  fuzz-fill coverage gaps, keeping the largest non-test clang/lib diffs in a
  shared quota, and draft local review files for PRs with real uncovered
  lines. Use when asked to "scan clang PRs for gaps", "scan clang frontend
  PRs", or similar.
---

# PR gap scan (clang)

Same pipeline as [pr-gap-scan](../pr-gap-scan/SKILL.md) (discover → dispatch
→ process → local draft), but discovery uses `--category clang` instead of the
AMDGPU/SPIRV backend labels. To combine with other categories in one run
(each with its own limit, overlaps deduped), see that skill's `--category`
usage.

## Discovery

One shared `--limit` (default 20) across these auto-applied labels from
`llvm/llvm-project`'s `.github/new-prs-labeler.yml`:

- `clang:frontend`
- `clang:codegen`
- `clang:driver`
- `clang:analysis`
- `clang:static analyzer`
- `clang:bytecode`
- `clang:dataflow`
- `clang:modules`

A labeled PR is eligible only when it changes a non-test file under
`clang/lib/` (headers, tests, unittests, and docs alone are not enough —
`--auto` would skip them). Eligible PRs are ranked by
`additions + deletions` on those `clang/lib/` files only; paths under
`llvm/test/`, `clang/test/`, `llvm/unittests/`, and `clang/unittests/` never
count toward size. Ties prefer the more recently updated PR. Already
reviewed PRs (any comment body containing "fuzz-fill", no newer commit) are
dropped before the quota is filled.

Dispatch and drafting reuse
[`../pr-gap-scan/scripts/scan.py`](../pr-gap-scan/scripts/scan.py). CI
classifies each PR with `--auto` (typically rule 2 for clang-only lib
changes).

## Usage

```bash
SCAN=.claude/skills/pr-gap-scan/scripts/scan.py
STATE=./data/pr-gap-scan-clang/$(date -u +%Y%m%d)/state.json
ARTIFACTS=./data/pr-gap-scan-clang/$(date -u +%Y%m%d)/artifacts
COMMENTS=./data/pr-gap-scan-clang/$(date -u +%Y%m%d)/comments

python3 "$SCAN" run \
  --state "$STATE" \
  --category clang \
  --artifacts-dir "$ARTIFACTS" \
  --out-dir "$COMMENTS"
```

Step-by-step:

```bash
python3 "$SCAN" discover --state "$STATE" --category clang --limit 20
python3 "$SCAN" dispatch --state "$STATE"
python3 "$SCAN" process  --state "$STATE" --artifacts-dir "$ARTIFACTS" \
  --out-dir "$COMMENTS" --poll-interval 60
```

To force one PR regardless of these filters, use
[pr-gap-check](../pr-gap-check/SKILL.md).

## After the run

Drafts land under `--out-dir` as `pr-<N>.md` when uncovered lines remain.
Review them locally. The agent does not post these files to GitHub, does not
run `gh pr comment`, and does not offer to publish them. See
[pr-gap-scan](../pr-gap-scan/SKILL.md) for the draft template, drift / LIT /
stacked-PR warnings, and prerequisites.
