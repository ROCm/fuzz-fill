#!/usr/bin/env python3
"""Scan recent llvm/llvm-project PRs touching AMDGPU/SPIRV for coverage gaps.

Drives the pr-gap-analysis.yml workflow (ROCm/fuzz-fill) end to end:
discover candidate PRs -> dispatch gap-finding-only runs -> poll and process
each PR as soon as its runs finish (download artifacts, filter out trivial
uncovered lines, write a draft review comment) without waiting on the rest
of the batch.

All state is persisted to a JSON file so the script can be re-run (e.g. after
being interrupted, or hours later once CI runs complete) and pick up where it
left off. See SKILL.md in the parent directory for the intended workflow.
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

DEFAULT_LLVM_REPO = "llvm/llvm-project"
DEFAULT_FUZZ_FILL_REPO = os.environ.get("FUZZ_FILL_GITHUB_REPO", "ROCm/fuzz-fill")
DEFAULT_REF = os.environ.get("FUZZ_FILL_WORKFLOW_REF", "users/mgcarrasco/manual-workflow")

BACKEND_PATH_RES = {
    "amdgpu": re.compile(r"^llvm/lib/Target/AMDGPU/"),
    "spirv": re.compile(r"^llvm/lib/Target/SPIRV/"),
}

# Expected artifact naming from pr-gap-analysis.yml -- used to detect a
# reusable prior run's artifacts, and to notice if the workflow's naming
# convention has drifted out from under this check.
FINDING_ARTIFACT_RE = re.compile(r"^gap-finding-pr(\d+)-(\d+)$")
PR_HEAD_ARTIFACT_RE = re.compile(r"^pr-head-pr(\d+)-(\d+)$")

# Lines whose entire purpose is to be unreachable/defensive aren't meaningful
# coverage gaps -- excluded per the review criteria this skill implements.
TRIVIAL_LINE_RE = re.compile(r"llvm_unreachable|\bassert\s*\(")

# gap-finding-pr.sh builds inside the container at this path, and
# target_lines_uncovered.csv's `file` column reflects that absolute build
# path rather than a path relative to the repo root. Strip it so permalinks
# and raw.githubusercontent.com fetches resolve correctly.
CONTAINER_BUILD_PREFIX = "/work/pr-llvm/"


def normalize_target_path(path):
    if path.startswith(CONTAINER_BUILD_PREFIX):
        return path[len(CONTAINER_BUILD_PREFIX):]
    return path

COMMENT_TEMPLATE = """\
Hi! This comment was generated using [fuzz-fill](https://github.com/ROCm/fuzz-fill), \
a new tool we're building to help improve LLVM test coverage by spotting lines \
introduced in a PR that don't yet appear to be exercised by the full test suite, \
including any tests added in this PR.

Looking at PR head {short_sha}, we found {count} line{plural} added or modified \
here that we couldn't find a test for:

{links}

If it makes sense, adding a regression test that validates these lines would be \
great. And if any of them are already tested and we missed it, we'd love to hear \
so we can improve the tool. Feel free to give us some feedback on whether this \
review was useful from your perspective. Thanks!
"""


def log(msg):
    print(msg, file=sys.stderr)


def check_gh():
    if not shutil.which("gh"):
        sys.exit("error: gh CLI is required (https://cli.github.com/)")


def gh_api_json(path):
    result = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def gh_api_paginated(path, per_page=100, max_pages=50):
    items = []
    page = 1
    sep = "&" if "?" in path else "?"
    while page <= max_pages:
        data = gh_api_json(f"{path}{sep}per_page={per_page}&page={page}")
        if not isinstance(data, list):
            return data
        items.extend(data)
        if len(data) < per_page:
            break
        page += 1
    return items


def load_state(path):
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return {"candidates": [], "runs": {}}


def save_state(state, path):
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


# --- discover -----------------------------------------------------------


def backend_for_path(path):
    for backend, regex in BACKEND_PATH_RES.items():
        if regex.match(path):
            return backend
    return None


def already_reviewed_without_new_commits(llvm_repo, number):
    """Returns True if fuzz-fill already commented and no commits landed since."""
    comments = gh_api_paginated(f"repos/{llvm_repo}/issues/{number}/comments")
    marker_comments = [c for c in comments if "fuzz-fill" in (c.get("body") or "").lower()]
    if not marker_comments:
        return False
    last_comment_at = max(c["created_at"] for c in marker_comments)

    commits = gh_api_paginated(f"repos/{llvm_repo}/pulls/{number}/commits")
    if not commits:
        return True
    last_commit_at = max(c["commit"]["committer"]["date"] for c in commits)
    return last_commit_at <= last_comment_at


def discover(llvm_repo, limit, max_scan_pages=20, per_page=50, backends=None):
    """Find up to `limit` most-recently-updated candidate PRs per backend.

    Each requested backend (default: both amdgpu and spirv) gets its own
    quota of `limit` PRs. A PR touching more than one requested backend
    counts against each of their quotas at once, but only lists the
    backend(s) that still had room in its `backends` field, so dispatch()
    doesn't analyze a backend past its limit.
    """
    requested = set(backends) if backends else set(BACKEND_PATH_RES)
    candidates = []
    counts = {backend: 0 for backend in requested}
    scanned = 0
    page = 1
    while any(counts[b] < limit for b in counts) and page <= max_scan_pages:
        prs = gh_api_json(
            f"repos/{llvm_repo}/pulls?state=open&sort=updated&direction=desc"
            f"&per_page={per_page}&page={page}"
        )
        if not prs:
            break
        for pr in prs:
            scanned += 1
            number = pr["number"]
            files = gh_api_paginated(f"repos/{llvm_repo}/pulls/{number}/files")
            all_backends = sorted(
                {b for f in files if (b := backend_for_path(f["filename"])) and b in requested}
            )
            backends_hit = [b for b in all_backends if counts[b] < limit]
            if not backends_hit:
                continue
            if already_reviewed_without_new_commits(llvm_repo, number):
                log(f"skip PR #{number}: already reviewed, no new commits since")
                continue
            candidates.append(
                {
                    "number": number,
                    "head_sha": pr["head"]["sha"],
                    "backends": backends_hit,
                    "url": pr["html_url"],
                    "title": pr["title"],
                    "updated_at": pr["updated_at"],
                    "llvm_repo": llvm_repo,
                    "forced": False,
                }
            )
            for b in backends_hit:
                counts[b] += 1
            log(f"candidate PR #{number} ({'/'.join(backends_hit)}): {pr['title']}")
        page += 1
    counts_str = ", ".join(f"{b}={c}" for b, c in sorted(counts.items()))
    log(f"scanned {scanned} PR(s), found {len(candidates)} candidate(s) ({counts_str})")
    return candidates


def target_one(state, state_path, llvm_repo, number, backend_override=None):
    """Force-add a single PR as a candidate, bypassing the discovery filters.

    Unlike discover(), this ignores the "already reviewed, no new commits"
    check, and clears any prior run state for this PR so dispatch() always
    triggers a fresh CI run rather than reusing a stale/failed one. Marking
    the candidate "forced" also makes dispatch() skip its artifact-reuse
    check (find_cached_run()) for this PR -- forcing means always fresh.
    """
    pr = gh_api_json(f"repos/{llvm_repo}/pulls/{number}")
    if backend_override:
        backends = sorted(set(backend_override))
    else:
        files = gh_api_paginated(f"repos/{llvm_repo}/pulls/{number}/files")
        backends = sorted({b for f in files if (b := backend_for_path(f["filename"]))})
        if not backends:
            sys.exit(
                f"error: PR #{number} doesn't touch AMDGPU/SPIRV backend paths; "
                "pass --backend to force a specific backend anyway"
            )

    cand = {
        "number": number,
        "head_sha": pr["head"]["sha"],
        "backends": backends,
        "url": pr["html_url"],
        "title": pr["title"],
        "updated_at": pr["updated_at"],
        "llvm_repo": llvm_repo,
        "forced": True,
    }
    for backend in backends:
        state["runs"].pop(f"{number}:{backend}", None)
    state["candidates"] = [c for c in state["candidates"] if c["number"] != number] + [cand]
    save_state(state, state_path)
    log(f"forced candidate PR #{number} ({'/'.join(backends)}): {pr['title']}")


# --- dispatch -------------------------------------------------------------


def dispatch_one(fuzz_fill_repo, ref, llvm_repo, number, backend):
    subprocess.run(
        [
            "gh", "workflow", "run", "pr-gap-analysis.yml",
            "-R", fuzz_fill_repo,
            "--ref", ref,
            "-f", f"pr_id={number}",
            "-f", f"github_repo={llvm_repo}",
            "-f", f"backend_tests={backend}",
            "-f", "run_gap_filling=false",
        ],
        check=True,
    )


def resolve_run_id(fuzz_fill_repo, number, backend, since_iso, known_ids, retries=12, delay=5):
    marker = f"llvm#{number} ({backend})"
    for attempt in range(retries):
        time.sleep(delay)
        data = gh_api_json(
            f"repos/{fuzz_fill_repo}/actions/workflows/pr-gap-analysis.yml/runs"
            f"?event=workflow_dispatch&per_page=20"
        )
        for run in data.get("workflow_runs", []):
            if (
                marker in (run.get("display_title") or "")
                and run["id"] not in known_ids
                and run["created_at"] >= since_iso
            ):
                return run["id"]
        log(f"  ...waiting for run to register (attempt {attempt + 1}/{retries})")
    return None


def list_prior_runs(fuzz_fill_repo, number, backend, per_page=100, max_pages=5):
    """Completed, successful pr-gap-analysis.yml runs for this PR/backend, newest first."""
    marker = f"llvm#{number} ({backend})"
    runs = []
    page = 1
    while page <= max_pages:
        data = gh_api_json(
            f"repos/{fuzz_fill_repo}/actions/workflows/pr-gap-analysis.yml/runs"
            f"?event=workflow_dispatch&status=success&per_page={per_page}&page={page}"
        )
        batch = data.get("workflow_runs", [])
        if not batch:
            break
        runs.extend(r for r in batch if marker in (r.get("display_title") or ""))
        if len(batch) < per_page:
            break
        page += 1
    return runs


def fetch_artifact_text(fuzz_fill_repo, run_id, artifact_name):
    """Downloads a small single-file artifact and returns its text, or None on failure."""
    with tempfile.TemporaryDirectory() as dest:
        try:
            subprocess.run(
                ["gh", "run", "download", str(run_id), "-R", fuzz_fill_repo, "-n", artifact_name, "-D", dest],
                check=True, capture_output=True, text=True,
            )
        except subprocess.CalledProcessError:
            return None
        files = [f for f in os.listdir(dest) if os.path.isfile(os.path.join(dest, f))]
        if not files:
            return None
        with open(os.path.join(dest, files[0])) as f:
            return f.read().strip()


def find_cached_run(fuzz_fill_repo, number, backend, head_sha):
    """Look for a prior successful run for this PR/backend that already analyzed
    head_sha, so dispatch() can reuse its artifact instead of scheduling a new run.

    Returns the run_id to reuse, or None if no prior run matches. Warns (and skips
    that run for reuse purposes) if a run's artifacts don't match the naming
    convention this depends on ('gap-finding-pr<N>-<run_id>' / 'pr-head-pr<N>-<run_id>'),
    since that would otherwise make this check silently useless.
    """
    for run in list_prior_runs(fuzz_fill_repo, number, backend):
        run_id = run["id"]
        artifacts = gh_api_json(f"repos/{fuzz_fill_repo}/actions/runs/{run_id}/artifacts?per_page=100")
        names = {a["name"] for a in artifacts.get("artifacts", [])}
        expected_finding = f"gap-finding-pr{number}-{run_id}"
        expected_head = f"pr-head-pr{number}-{run_id}"
        unrecognized = {n for n in names if not FINDING_ARTIFACT_RE.match(n) and not PR_HEAD_ARTIFACT_RE.match(n)}
        if unrecognized:
            log(
                f"warning: run {run_id} (PR #{number}, {backend}) has artifact(s) "
                f"{sorted(unrecognized)} that don't match the expected "
                f"'gap-finding-pr<N>-<run_id>' / 'pr-head-pr<N>-<run_id>' naming convention "
                "-- has the workflow's artifact naming changed? skipping cache reuse for this run"
            )
            continue
        if expected_finding not in names:
            continue
        if expected_head not in names:
            log(
                f"warning: run {run_id} (PR #{number}, {backend}) has a gap-finding artifact "
                f"but no '{expected_head}' artifact to verify its analyzed commit -- skipping "
                "cache reuse for this run"
            )
            continue
        analyzed_sha = fetch_artifact_text(fuzz_fill_repo, run_id, expected_head)
        if analyzed_sha == head_sha:
            return run_id
    return None


def dispatch(state, state_path, fuzz_fill_repo, ref, llvm_repo):
    known_ids = {r["run_id"] for r in state["runs"].values() if "run_id" in r}
    for cand in state["candidates"]:
        number = cand["number"]
        head_sha = cand.get("head_sha")
        forced = cand.get("forced", False)
        for backend in cand["backends"]:
            key = f"{number}:{backend}"
            if key in state["runs"]:
                continue
            if not forced and head_sha:
                cached_run_id = find_cached_run(fuzz_fill_repo, number, backend, head_sha)
                if cached_run_id is not None:
                    log(
                        f"PR #{number} ({backend}): reusing artifact from run {cached_run_id} "
                        f"(already analyzed {head_sha[:12]}), skipping dispatch"
                    )
                    known_ids.add(cached_run_id)
                    state["runs"][key] = {
                        "run_id": cached_run_id,
                        "status": "completed",
                        "conclusion": "success",
                        "downloaded": False,
                    }
                    save_state(state, state_path)
                    continue
            since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            log(f"dispatching PR #{number} ({backend})")
            dispatch_one(fuzz_fill_repo, ref, llvm_repo, number, backend)
            run_id = resolve_run_id(fuzz_fill_repo, number, backend, since, known_ids)
            if run_id is None:
                log(f"  warning: could not resolve run id for {key}; check manually")
                continue
            known_ids.add(run_id)
            state["runs"][key] = {
                "run_id": run_id,
                "status": "queued",
                "conclusion": None,
                "downloaded": False,
            }
            log(f"  run id: {run_id}")
            save_state(state, state_path)


# --- collect -----------------------------------------------------------


def collect(state, state_path, fuzz_fill_repo, artifacts_dir):
    for key, run in state["runs"].items():
        if run.get("status") != "completed" or run.get("downloaded"):
            continue
        if run.get("conclusion") != "success":
            log(f"skip {key}: run did not succeed (conclusion={run.get('conclusion')})")
            continue
        number, backend = key.split(":")
        dest = os.path.join(artifacts_dir, f"pr-{number}", backend)
        os.makedirs(dest, exist_ok=True)
        name = f"gap-finding-pr{number}-{run['run_id']}"
        subprocess.run(
            ["gh", "run", "download", str(run["run_id"]), "-R", fuzz_fill_repo, "-n", name, "-D", dest],
            check=True,
        )
        run["downloaded"] = True
        run["artifact_dir"] = dest
        save_state(state, state_path)


# --- comment -----------------------------------------------------------


def parse_readme(path):
    info = {}
    with open(path) as f:
        for line in f:
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()
    return info


def fetch_source_lines(sha, path, cache):
    key = (sha, path)
    if key not in cache:
        url = f"https://raw.githubusercontent.com/llvm/llvm-project/{sha}/{path}"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                text = resp.read().decode("utf-8", errors="replace")
        except Exception as e:  # network hiccup or file moved/renamed
            log(f"warning: failed to fetch {url}: {e}")
            text = ""
        cache[key] = text.splitlines()
    return cache[key]


def is_trivial_line(sha, path, line_no, cache):
    lines = fetch_source_lines(sha, path, cache)
    text = lines[line_no - 1] if 1 <= line_no <= len(lines) else ""
    return bool(TRIVIAL_LINE_RE.search(text))


def render_comment(pr_head, entries):
    links = "\n".join(
        f"{i}. https://github.com/llvm/llvm-project/blob/{pr_head}/{file}#L{line}"
        for i, (file, line) in enumerate(entries, 1)
    )
    return COMMENT_TEMPLATE.format(
        short_sha=pr_head[:12],
        count=len(entries),
        plural="" if len(entries) == 1 else "s",
        links=links,
    )


def fetch_live_pr(llvm_repo, number):
    """One live GET of the PR; returns {"head_sha", "base_ref"}, or None on failure
    (closed/renumbered/network hiccup -- don't block the report on this)."""
    try:
        pr = gh_api_json(f"repos/{llvm_repo}/pulls/{number}")
        return {"head_sha": pr["head"]["sha"], "base_ref": pr["base"]["ref"]}
    except Exception as e:
        log(f"warning: could not re-check PR #{number}'s current state: {e}")
        return None


def default_branch(llvm_repo, cache):
    key = ("_default_branch", llvm_repo)
    if key not in cache:
        cache[key] = gh_api_json(f"repos/{llvm_repo}")["default_branch"]
    return cache[key]


def find_base_pr(llvm_repo, base_ref):
    """If base_ref is itself the head branch of another currently-open PR in
    llvm_repo, return that PR's {number, title}; else None (already merged,
    a maintenance branch, or otherwise not a live PR)."""
    owner = llvm_repo.split("/", 1)[0]
    try:
        matches = gh_api_json(
            f"repos/{llvm_repo}/pulls?state=open&head={owner}:{base_ref}&per_page=1"
        )
    except Exception:
        return None
    if not matches:
        return None
    return {"number": matches[0]["number"], "title": matches[0]["title"]}


def render_drift_warning(number, analyzed_sha, live_sha):
    # HTML comments are stripped from GitHub's rendered view, so this stays
    # visible to whoever reads the raw file but disappears if the file is
    # posted as-is with `gh pr comment --body-file`.
    return (
        "<!-- fuzz-fill internal note: do not post this block, GitHub hides "
        "HTML comments when rendering so it won't show up if you do, but "
        "strip it if you're posting the body some other way. -->\n"
        "> [!WARNING]\n"
        f"> PR #{number} has drifted since this analysis ran. It was analyzed "
        f"against commit `{analyzed_sha[:12]}` (`{analyzed_sha}`), but the "
        f"PR's current tip is `{live_sha[:12]}` (`{live_sha}`). The uncovered "
        "lines below may be stale -- re-run the analysis (pr-gap-check's "
        "`target` subcommand forces a fresh run) before posting.\n"
        "<!-- end internal note -->\n\n"
    )


def render_stacked_pr_warning(number, base_ref, base_branch, base_pr):
    if base_pr:
        detail = (
            f"which is itself still-open PR #{base_pr['number']} "
            f"({base_pr['title']!r})"
        )
    else:
        detail = (
            "which doesn't match any currently open PR -- it may be a "
            "maintenance branch, or the PR this was stacked on has already "
            "merged without this PR being retargeted onto the default branch yet"
        )
    return (
        "<!-- fuzz-fill internal note: do not post this block, GitHub hides "
        "HTML comments when rendering so it won't show up if you do, but "
        "strip it if you're posting the body some other way. -->\n"
        "> [!WARNING]\n"
        f"> PR #{number} looks stacked: its base branch is `{base_ref}`, not "
        f"the repository's default branch (`{base_branch}`), {detail}. The gap "
        "analysis only considered lines unique to this PR (diffed against its "
        "merge-base), but that merge-base will move if the base branch gets "
        "amended or rebased before it merges -- which can invalidate this "
        "analysis without this PR's own head commit ever changing, so the "
        "drift check (which only compares this PR's own head commit) "
        "wouldn't catch it. Confirm the base PR/branch is settled before "
        "trusting these findings.\n"
        "<!-- end internal note -->\n\n"
    )


def render_lit_failures_warning(warnings):
    # Same hidden-note treatment as render_drift_warning: visible in the raw
    # draft for whoever reviews it, stripped by GitHub if posted verbatim.
    lines = [
        "<!-- fuzz-fill internal note: do not post this block, GitHub hides "
        "HTML comments when rendering so it won't show up if you do, but "
        "strip it if you're posting the body some other way. -->"
    ]
    for backend, message in warnings:
        lines.append("> [!WARNING]")
        lines.append(f"> **{backend}**:")
        for line in message.splitlines():
            lines.append(f"> {line}" if line else ">")
    lines.append("<!-- end internal note -->\n")
    return "\n".join(lines)


def render_pr_comment(cand, state, out_dir, cache):
    """Build and write the draft comment for one candidate, if it has any
    surviving (non-trivial) uncovered lines. Returns the written path, or
    None if there was nothing to write (no artifact yet, or everything
    filtered out as trivial).
    """
    number = cand["number"]
    entries = set()
    pr_head = None
    lit_warnings = []
    for backend in cand["backends"]:
        run = state["runs"].get(f"{number}:{backend}")
        if not run or not run.get("downloaded"):
            continue
        adir = run["artifact_dir"]
        readme_path = os.path.join(adir, "README-finding.txt")
        csv_path = os.path.join(adir, "out", "commit_lines_report", "target_lines_uncovered.csv")
        if not os.path.isfile(csv_path):
            continue
        info = parse_readme(readme_path) if os.path.isfile(readme_path) else {}
        pr_head = info.get("pr_head") or cand["head_sha"]
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                entries.add((normalize_target_path(row["file"]), int(row["line"])))
        warning_path = os.path.join(adir, "README-WARNING")
        if os.path.isfile(warning_path):
            with open(warning_path) as f:
                lit_warnings.append((backend, f.read().strip()))
    if not entries or pr_head is None:
        return None
    surviving = sorted(e for e in entries if not is_trivial_line(pr_head, e[0], e[1], cache))
    if not surviving:
        log(f"PR #{number}: all {len(entries)} uncovered line(s) filtered as trivial")
        return None
    text = render_comment(pr_head, surviving)
    llvm_repo = cand.get("llvm_repo", DEFAULT_LLVM_REPO)
    live_pr = fetch_live_pr(llvm_repo, number)
    live_head = live_pr["head_sha"] if live_pr else None
    if live_head and live_head != pr_head:
        log(f"warning: PR #{number} has drifted (analyzed {pr_head[:12]}, now at {live_head[:12]})")
        text = render_drift_warning(number, pr_head, live_head) + text
    if lit_warnings:
        log(f"warning: PR #{number} had LIT test failures during analysis for: "
            f"{', '.join(b for b, _ in lit_warnings)}")
        text = render_lit_failures_warning(lit_warnings) + text
    base_ref = live_pr["base_ref"] if live_pr else None
    if base_ref:
        base_branch = default_branch(llvm_repo, cache)
        if base_ref != base_branch:
            base_pr = find_base_pr(llvm_repo, base_ref)
            log(f"warning: PR #{number} looks stacked (base branch {base_ref!r} "
                f"!= default branch {base_branch!r})")
            text = render_stacked_pr_warning(number, base_ref, base_branch, base_pr) + text
    title = f"# [#{number}]({cand['url']}) — {cand['title']}\n\n"
    text = title + text
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"pr-{number}.md")
    with open(out_path, "w") as f:
        f.write(text)
    log(f"wrote {out_path} ({len(surviving)} line(s), {len(entries) - len(surviving)} filtered as trivial)")
    return out_path


def comment(state, out_dir):
    cache = {}
    written = []
    for cand in state["candidates"]:
        path = render_pr_comment(cand, state, out_dir, cache)
        if path:
            written.append(path)
    return written


def candidate_ready(state, cand):
    """True once every backend run for this candidate has reached a terminal
    state (completed, downloaded-or-not) -- i.e. there's nothing left to
    wait for before writing this PR's comment, win or lose."""
    for backend in cand["backends"]:
        run = state["runs"].get(f"{cand['number']}:{backend}")
        if run is not None and run.get("status") != "completed":
            return False
    return True


def process(state, state_path, fuzz_fill_repo, artifacts_dir, out_dir, poll_interval):
    """Poll dispatched runs and handle each PR as soon as its own runs finish
    -- download its artifact(s) and write its draft comment immediately --
    rather than waiting for every dispatched run in the batch to complete
    before touching any of them.
    """
    cache = {}
    done = set()
    while True:
        for run in state["runs"].values():
            if run.get("status") == "completed":
                continue
            data = gh_api_json(f"repos/{fuzz_fill_repo}/actions/runs/{run['run_id']}")
            run["status"] = data["status"]
            run["conclusion"] = data.get("conclusion")
        save_state(state, state_path)

        collect(state, state_path, fuzz_fill_repo, artifacts_dir)

        for cand in state["candidates"]:
            number = cand["number"]
            if number in done:
                continue
            if candidate_ready(state, cand):
                render_pr_comment(cand, state, out_dir, cache)
                done.add(number)

        pending = [k for k, v in state["runs"].items() if v.get("status") != "completed"]
        if not pending:
            return
        log(f"waiting on {len(pending)} run(s): {', '.join(pending)}")
        time.sleep(poll_interval)


# --- CLI -----------------------------------------------------------------


def add_common_args(p):
    p.add_argument("--state", required=True, help="Path to the JSON state file")


def cmd_discover(args):
    state = load_state(args.state)
    state["candidates"] = discover(args.llvm_repo, args.limit, args.max_scan_pages, backends=args.backend)
    save_state(state, args.state)


def cmd_dispatch(args):
    state = load_state(args.state)
    dispatch(state, args.state, args.fuzz_fill_repo, args.ref, args.llvm_repo)


def cmd_collect(args):
    state = load_state(args.state)
    collect(state, args.state, args.fuzz_fill_repo, args.artifacts_dir)


def cmd_comment(args):
    state = load_state(args.state)
    comment(state, args.out_dir)


def cmd_process(args):
    state = load_state(args.state)
    process(state, args.state, args.fuzz_fill_repo, args.artifacts_dir, args.out_dir, args.poll_interval)


def cmd_target(args):
    state = load_state(args.state)
    target_one(state, args.state, args.llvm_repo, args.pr, args.backend)


def cmd_run(args):
    state = load_state(args.state)
    if getattr(args, "pr", None):
        target_one(state, args.state, args.llvm_repo, args.pr, args.backend)
    elif not state["candidates"]:
        state["candidates"] = discover(args.llvm_repo, args.limit, args.max_scan_pages, backends=args.backend)
        save_state(state, args.state)
    dispatch(state, args.state, args.fuzz_fill_repo, args.ref, args.llvm_repo)
    process(state, args.state, args.fuzz_fill_repo, args.artifacts_dir, args.out_dir, args.poll_interval)


def main():
    check_gh()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("discover", help="Find candidate PRs, write them to --state")
    add_common_args(p)
    p.add_argument("--llvm-repo", default=DEFAULT_LLVM_REPO)
    p.add_argument("--limit", type=int, default=20, help="Max candidates to keep per backend")
    p.add_argument("--max-scan-pages", type=int, default=20)
    p.add_argument(
        "--backend", choices=["amdgpu", "spirv"], action="append",
        help="Repeatable; default: scan both amdgpu and spirv",
    )
    p.set_defaults(func=cmd_discover)

    p = sub.add_parser("dispatch", help="Trigger gap-finding-only runs for candidates in --state")
    add_common_args(p)
    p.add_argument("--fuzz-fill-repo", default=DEFAULT_FUZZ_FILL_REPO)
    p.add_argument("--ref", default=DEFAULT_REF)
    p.add_argument("--llvm-repo", default=DEFAULT_LLVM_REPO)
    p.set_defaults(func=cmd_dispatch)

    p = sub.add_parser("collect", help="Download artifacts for completed runs")
    add_common_args(p)
    p.add_argument("--fuzz-fill-repo", default=DEFAULT_FUZZ_FILL_REPO)
    p.add_argument("--artifacts-dir", required=True)
    p.set_defaults(func=cmd_collect)

    p = sub.add_parser("comment", help="Filter uncovered lines and write draft comments")
    add_common_args(p)
    p.add_argument("--out-dir", required=True)
    p.set_defaults(func=cmd_comment)

    p = sub.add_parser(
        "process",
        help="Poll dispatched runs, downloading and drafting each PR's comment as soon as it's ready",
    )
    add_common_args(p)
    p.add_argument("--fuzz-fill-repo", default=DEFAULT_FUZZ_FILL_REPO)
    p.add_argument("--artifacts-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--poll-interval", type=int, default=60)
    p.set_defaults(func=cmd_process)

    p = sub.add_parser(
        "target", help="Force-add one specific PR as a candidate, bypassing discovery filters"
    )
    add_common_args(p)
    p.add_argument("--llvm-repo", default=DEFAULT_LLVM_REPO)
    p.add_argument("--pr", type=int, required=True, help="llvm/llvm-project PR number")
    p.add_argument(
        "--backend", choices=["amdgpu", "spirv"], action="append",
        help="Repeatable; default: auto-detect from the PR's changed files",
    )
    p.set_defaults(func=cmd_target)

    p = sub.add_parser("run", help="Run discover -> dispatch -> process (poll/collect/comment as each PR is ready)")
    add_common_args(p)
    p.add_argument("--llvm-repo", default=DEFAULT_LLVM_REPO)
    p.add_argument("--fuzz-fill-repo", default=DEFAULT_FUZZ_FILL_REPO)
    p.add_argument("--ref", default=DEFAULT_REF)
    p.add_argument("--pr", type=int, default=None, help="Force-analyze one PR instead of discovering")
    p.add_argument(
        "--backend", choices=["amdgpu", "spirv"], action="append",
        help="Repeatable. With --pr: override the PR's auto-detected backend(s). "
        "Without --pr: restrict discovery to this backend (default: both)",
    )
    p.add_argument("--limit", type=int, default=20, help="Max candidates to keep per backend")
    p.add_argument("--max-scan-pages", type=int, default=20)
    p.add_argument("--poll-interval", type=int, default=60)
    p.add_argument("--artifacts-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
