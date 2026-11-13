#!/usr/bin/env python3
"""Discover llvm/llvm-project PRs and dispatch PR gap analysis.

Used by .github/workflows/pr-gap-scan.yml: find candidate PRs by category,
then trigger pr-gap-analysis.yml for each. State is persisted to a JSON file
so discover/dispatch can be resumed. Does not wait for analysis runs or draft
review comments -- each analysis run files its own pr-analysis-result issue.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Max concurrent `gh api` subprocesses for per-PR discovery fetches. These are
# independent GETs against non-search REST endpoints (5000/hr limit), so
# running them concurrently is safe; kept modest to avoid hammering the API.
PR_FETCH_WORKERS = 8

# Discovery only looks at PRs updated in the last N days. A PR nobody has
# touched in over a week is unlikely to be worth reviewing first, and
# narrowing the search query itself (not just truncating results after the
# fact) is what actually cuts the number of /pulls/<n> and /pulls/<n>/files
# calls discovery has to pay for.
DISCOVERY_WINDOW_DAYS = 7

# Backstop on how many PRs a single label search will scan before giving up,
# even if max_scan_pages/quota would allow more. Some labels (e.g.
# llvm:transforms, backend:AMDGPU) carry 400-1000+ open PRs even within the
# 7-day window, and discover_group() only ranks after scanning everything, so
# without this a single busy label can burn hundreds of API calls. Logged
# when it triggers so the coverage loss is visible, not silent.
PER_LABEL_SCAN_CAP = 30

DEFAULT_LLVM_REPO = "llvm/llvm-project"
DEFAULT_FUZZ_FILL_REPO = os.environ.get("FUZZ_FILL_GITHUB_REPO", "ROCm/fuzz-fill")
DEFAULT_REF = os.environ.get("FUZZ_FILL_WORKFLOW_REF", "users/mgcarrasco/manual-workflow")

# Exact backend source dirs. Used to attribute a PR to a quota when it really
# edits that backend. Not a discovery gate: --auto also analyzes other
# llvm/lib and clang/lib changes (see auto_would_run).
BACKEND_PATH_RES = {
    "amdgpu": re.compile(r"^llvm/lib/Target/AMDGPU/"),
    "spirv": re.compile(r"^llvm/lib/Target/SPIRV/"),
}

# Same prefixes gap_scope.classifier ignores / accepts. Kept inline so this
# script stays stdlib-only (no PYTHONPATH, no venv).
TEST_PATH_PREFIXES = (
    "llvm/test/",
    "clang/test/",
    "llvm/unittests/",
    "clang/unittests/",
)
LIB_PATH_PREFIXES = ("llvm/lib/", "clang/lib/")

# llvm/llvm-project auto-labels PRs by changed-file globs (.github/new-prs-labeler.yml).
# Used to narrow discover()'s candidate pool before paying for a /pulls/<n>/files call
# per PR. These globs are broader than BACKEND_PATH_RES (e.g. backend:AMDGPU fires on
# any path containing "amdgpu" anywhere in the repo, not just llvm/lib/Target/AMDGPU/).
# The files call still runs, but only to drop PRs --auto would skip and to
# attribute backend quotas.
BACKEND_LABELS = {
    "amdgpu": "backend:AMDGPU",
    "spirv": "backend:SPIR-V",
}

# Shared-quota discovery groups (--category llvm|clang, also --group). Labels
# come from llvm/llvm-project .github/new-prs-labeler.yml. Matching lib
# prefixes are the only files that gate a PR and that count toward
# lib_diff_size.
GROUP_CONFIGS = {
    "llvm": {
        "labels": ("llvm:ir", "llvm:analysis", "llvm:transforms"),
        "lib_prefixes": (
            "llvm/lib/IR/",
            "llvm/lib/Analysis/",
            "llvm/lib/Transforms/",
        ),
    },
    "clang": {
        "labels": (
            "clang:frontend",
            "clang:codegen",
            "clang:driver",
            "clang:analysis",
            "clang:static analyzer",
            "clang:bytecode",
            "clang:dataflow",
            "clang:modules",
        ),
        "lib_prefixes": ("clang/lib/",),
    },
}

# All discoverable categories: backends + groups. --category accepts these.
CATEGORY_CHOICES = tuple(sorted(set(BACKEND_LABELS) | set(GROUP_CONFIGS)))
DEFAULT_CATEGORIES = ("amdgpu", "spirv")

# Expected artifact naming from pr-gap-analysis.yml -- used to detect a
# reusable prior run's artifacts, and to notice if the workflow's naming
# convention has drifted out from under this check. Finding runs always
# upload results; HTML coverage uploads when generate_html is on (default);
# raw (all baseline CSVs) and instrumented tools are opt-in via upload_raw /
# upload_tools.
FINDING_RESULTS_ARTIFACT_RE = re.compile(r"^gap-finding-results-pr(\d+)-(\d+)$")
FINDING_RAW_ARTIFACT_RE = re.compile(r"^gap-finding-raw-pr(\d+)-(\d+)$")
PR_HEAD_ARTIFACT_RE = re.compile(r"^pr-head-pr(\d+)-(\d+)$")
INSTRUMENTED_TOOLS_ARTIFACT_RE = re.compile(
    r"^instrumented-tools-pr(\d+)-(\d+)$"
)
HTML_COVERAGE_ARTIFACT_RE = re.compile(r"^html-coverage-pr(\d+)-(\d+)$")


def _is_expected_artifact_name(name):
    return bool(
        FINDING_RESULTS_ARTIFACT_RE.match(name)
        or FINDING_RAW_ARTIFACT_RE.match(name)
        or PR_HEAD_ARTIFACT_RE.match(name)
        or INSTRUMENTED_TOOLS_ARTIFACT_RE.match(name)
        or HTML_COVERAGE_ARTIFACT_RE.match(name)
    )


def _finding_artifact_name(number, run_id, *, raw=False):
    prefix = "gap-finding-raw-pr" if raw else "gap-finding-results-pr"
    return f"{prefix}{number}-{run_id}"

def log(msg):
    print(msg, file=sys.stderr)


def check_gh():
    if not shutil.which("gh"):
        sys.exit("error: gh CLI is required (https://cli.github.com/)")


def gh_api_json(path, retries=5, backoff=2.0):
    """GET `path` via `gh api`, retrying transient failures.

    Concurrent discovery (_prefetch_pr_cores/_prefetch_reviewed) fires several
    of these at once, which makes hitting GitHub's secondary rate limit or a
    one-off network blip more likely than the old fully-serial callers did --
    without a retry, one flaky call aborts an entire multi-category discover()
    and throws away everything already fetched (discover only saves to
    --state once, at the end).
    """
    last_err = None
    for attempt in range(retries):
        result = subprocess.run(["gh", "api", path], capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        last_err = (result.stderr or result.stdout or "").strip()
        if attempt < retries - 1:
            delay = backoff * (2 ** attempt)
            log(f"warning: gh api {path!r} failed (attempt {attempt + 1}/{retries}): "
                f"{last_err} -- retrying in {delay:.0f}s")
            time.sleep(delay)
    raise RuntimeError(f"gh api {path!r} failed after {retries} attempts: {last_err}")


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


def _since_date(days):
    """YYYY-MM-DD `days` ago (UTC), for a search `updated:>=` qualifier."""
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))


def search_open_prs_by_label(llvm_repo, label, per_page, page, since_date=None):
    """One page of open PRs carrying `label`, most-recently-updated first.

    `since_date` (YYYY-MM-DD) restricts to PRs updated on/after that date --
    narrowing the search query itself, not just how many results are kept.
    """
    q = f'repo:{llvm_repo} is:pr is:open label:"{label}"'
    if since_date:
        q += f" updated:>={since_date}"
    data = gh_api_json(
        f"search/issues?q={urllib.parse.quote(q)}&sort=updated&order=desc"
        f"&per_page={per_page}&page={page}"
    )
    return data.get("items", [])


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


def normalize_repo_path(path):
    return path.replace("\\", "/").lstrip("./")


def is_test_path(path):
    return any(path.startswith(prefix) for prefix in TEST_PATH_PREFIXES)


def backend_for_path(path):
    for backend, regex in BACKEND_PATH_RES.items():
        if regex.match(path):
            return backend
    return None


def auto_would_run(paths):
    """True when gap-scope --auto would build and analyze these paths.

    Mirrors classifier rules 1–3: ignore test trees, then run if anything
    left is under llvm/lib/ or clang/lib/. Rule 4 (tests, docs, other) is
    a CI skip, so discovery should not dispatch it.
    """
    for raw in paths:
        path = normalize_repo_path(raw)
        if not path or is_test_path(path):
            continue
        if any(path.startswith(prefix) for prefix in LIB_PATH_PREFIXES):
            return True
    return False


def matches_group_lib(path, lib_prefixes):
    """True when *path* is a non-test file under one of the group's lib trees."""
    path = normalize_repo_path(path)
    if not path or is_test_path(path):
        return False
    return any(path.startswith(prefix) for prefix in lib_prefixes)


def group_has_lib_change(filenames, lib_prefixes):
    return any(matches_group_lib(name, lib_prefixes) for name in filenames)


def lib_diff_size(files, lib_prefixes):
    """Sum additions+deletions on matching lib files; tests never count."""
    total = 0
    for entry in files:
        name = entry.get("filename") or ""
        if not matches_group_lib(name, lib_prefixes):
            continue
        total += int(entry.get("additions") or 0) + int(entry.get("deletions") or 0)
    return total


def select_top_by_lib_size(candidates, limit):
    """Keep the *limit* largest lib diffs; ties prefer more recently updated."""
    ranked = sorted(
        candidates,
        key=lambda c: (c.get("lib_diff_size", 0), c.get("updated_at") or ""),
        reverse=True,
    )
    return ranked[:limit]


def backends_for_paths(paths, requested):
    """Backends whose llvm/lib/Target/<Backend>/ tree appears in paths."""
    wanted = set(requested)
    return sorted(
        {b for path in paths if (b := backend_for_path(path)) and b in wanted}
    )


def label_backends(label_names, requested):
    """Requested backends whose GitHub label is in label_names."""
    wanted = set(requested)
    return sorted(
        b for b, label in BACKEND_LABELS.items()
        if b in wanted and label in label_names
    )


def attribute_backends(paths, label_names, requested):
    """Which backend quotas a PR counts against.

    A real llvm/lib/Target/<Backend>/ edit wins, so an AMDGPU+SPIRV source
    change counts against both even if only one label search found it.
    Otherwise fall back to the backend labels the PR carries: that is how a
    clang/lib or other llvm/lib change stays tied to AMDGPU or SPIRV.
    """
    path_hits = backends_for_paths(paths, requested)
    if path_hits:
        return path_hits
    return label_backends(label_names, requested)


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


def _fetch_pr_core(llvm_repo, number):
    """One PR's metadata + changed files -- the two calls every discovery
    path needs regardless of category. Independent of any other PR, so safe
    to run from a worker thread."""
    pr = gh_api_json(f"repos/{llvm_repo}/pulls/{number}")
    files = gh_api_paginated(f"repos/{llvm_repo}/pulls/{number}/files")
    return {
        "pr": pr,
        "files": files,
        "filenames": [f["filename"] for f in files],
        "label_names": {label["name"] for label in pr.get("labels", [])},
    }


def _prefetch_pr_cores(llvm_repo, numbers, cache, max_workers=PR_FETCH_WORKERS):
    """Populate `cache[number]` (a _fetch_pr_core() result) for any of
    `numbers` not already cached, fetching concurrently. `cache` may already
    hold entries from a different category's pass over an overlapping PR."""
    todo = [n for n in numbers if n not in cache]
    if not todo:
        return
    with ThreadPoolExecutor(max_workers=min(max_workers, len(todo))) as pool:
        futures = {pool.submit(_fetch_pr_core, llvm_repo, n): n for n in todo}
        for future in as_completed(futures):
            cache[futures[future]] = future.result()


def _prefetch_reviewed(llvm_repo, numbers, reviewed_cache, max_workers=PR_FETCH_WORKERS):
    """Populate `reviewed_cache[number]` (already_reviewed_without_new_commits()
    result) concurrently for any of `numbers` not already cached."""
    todo = [n for n in numbers if n not in reviewed_cache]
    if not todo:
        return
    with ThreadPoolExecutor(max_workers=min(max_workers, len(todo))) as pool:
        futures = {
            pool.submit(already_reviewed_without_new_commits, llvm_repo, n): n
            for n in todo
        }
        for future in as_completed(futures):
            reviewed_cache[futures[future]] = future.result()


def discover(llvm_repo, limit, max_scan_pages=20, per_page=50, backends=None,
             pr_cache=None, reviewed_cache=None, since_days=DISCOVERY_WINDOW_DAYS,
             per_label_scan_cap=PER_LABEL_SCAN_CAP):
    """Find up to `limit` most-recently-updated candidate PRs per backend.

    Each requested backend (default: both amdgpu and spirv) gets its own
    quota of `limit` PRs, found by searching open PRs carrying that
    backend's label (BACKEND_LABELS) instead of listing every open PR and
    fetching its changed files -- only PRs GitHub already labeled as
    touching the backend ever pay for a /pulls/<n>/files call. The files
    call does not require llvm/lib/Target/<Backend>/. It drops a PR only
    when --auto would skip it (no non-test llvm/lib or clang/lib change)
    and attributes quotas via attribute_backends(). A PR touching more
    than one requested backend counts against each of their quotas at
    once, but only lists the backend(s) that still had room in its
    `backends` field, so dispatch() doesn't analyze a backend past its
    limit. A PR found under one backend's label search is only processed
    once even if it also carries another requested backend's label.
    """
    if pr_cache is None:
        pr_cache = {}
    if reviewed_cache is None:
        reviewed_cache = {}
    requested = set(backends) if backends else set(BACKEND_PATH_RES)
    since_date = _since_date(since_days) if since_days else None
    candidates = []
    counts = {backend: 0 for backend in requested}
    seen = set()
    scanned = 0
    for backend in sorted(requested):
        label = BACKEND_LABELS[backend]
        page = 1
        label_scanned = 0
        while counts[backend] < limit and page <= max_scan_pages:
            if label_scanned >= per_label_scan_cap:
                log(
                    f"stop scanning label {label!r}: hit per-label cap "
                    f"({per_label_scan_cap}) before filling backend={backend} quota"
                )
                break
            items = search_open_prs_by_label(llvm_repo, label, per_page, page, since_date)
            if not items:
                break
            page_numbers = [item["number"] for item in items if item["number"] not in seen]
            seen.update(page_numbers)
            scanned += len(page_numbers)
            label_scanned += len(page_numbers)
            # Fetch the whole page's PR metadata + files concurrently -- the
            # two calls every item needs regardless of quota/filter outcome,
            # and cached so a PR shared with another category isn't refetched.
            _prefetch_pr_cores(llvm_repo, page_numbers, pr_cache)
            # The quota check below depends on live `counts`, which only
            # advances as earlier items in this same page are committed, so
            # this pass (and the already-reviewed check it gates) stays
            # sequential -- only the network fetch above was parallelized.
            for number in page_numbers:
                core = pr_cache[number]
                pr, filenames, label_names = core["pr"], core["filenames"], core["label_names"]
                if not auto_would_run(filenames):
                    log(
                        f"skip PR #{number}: --auto would skip "
                        "(no non-test llvm/lib or clang/lib changes)"
                    )
                    continue
                attributed = attribute_backends(filenames, label_names, requested)
                if not attributed and backend in requested:
                    attributed = [backend]
                backends_hit = [b for b in attributed if counts[b] < limit]
                if not backends_hit:
                    continue
                if number not in reviewed_cache:
                    reviewed_cache[number] = already_reviewed_without_new_commits(llvm_repo, number)
                if reviewed_cache[number]:
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
                    }
                )
                for b in backends_hit:
                    counts[b] += 1
                log(f"candidate PR #{number} ({'/'.join(backends_hit)}): {pr['title']}")
            if len(items) < per_page:
                break
            page += 1
    counts_str = ", ".join(f"{b}={c}" for b, c in sorted(counts.items()))
    log(f"checked {scanned} labeled PR(s), found {len(candidates)} candidate(s) ({counts_str})")
    return candidates


def discover_group(llvm_repo, group, limit, max_scan_pages=20, per_page=50,
                    pr_cache=None, reviewed_cache=None, since_days=DISCOVERY_WINDOW_DAYS,
                    per_label_scan_cap=PER_LABEL_SCAN_CAP):
    """Find up to `limit` open PRs for a shared llvm/clang quota.

    Searches every label in GROUP_CONFIGS[group], dedupes, keeps PRs that
    change a matching lib path (tests/headers/docs alone are not enough),
    drops already-reviewed ones, then keeps the largest lib diffs
    (additions+deletions on matching lib files only; test paths excluded).
    Ties break toward the more recently updated PR.
    """
    if group not in GROUP_CONFIGS:
        sys.exit(f"error: unknown group {group!r}; choose from {sorted(GROUP_CONFIGS)}")
    if pr_cache is None:
        pr_cache = {}
    if reviewed_cache is None:
        reviewed_cache = {}
    config = GROUP_CONFIGS[group]
    labels = config["labels"]
    lib_prefixes = config["lib_prefixes"]
    since_date = _since_date(since_days) if since_days else None
    seen = set()
    scanned = 0
    eligible = []
    for label in labels:
        page = 1
        label_scanned = 0
        while page <= max_scan_pages:
            if label_scanned >= per_label_scan_cap:
                log(
                    f"stop scanning label {label!r}: hit per-label cap "
                    f"({per_label_scan_cap}) for group={group}"
                )
                break
            items = search_open_prs_by_label(llvm_repo, label, per_page, page, since_date)
            if not items:
                break
            page_numbers = [item["number"] for item in items if item["number"] not in seen]
            seen.update(page_numbers)
            scanned += len(page_numbers)
            label_scanned += len(page_numbers)
            # Unlike discover(), eligibility here never depends on processing
            # order (top-N-by-size selection happens after every PR in every
            # label is collected), so both the metadata fetch and the
            # already-reviewed check can run fully concurrently per page.
            _prefetch_pr_cores(llvm_repo, page_numbers, pr_cache)
            lib_changed = [
                n for n in page_numbers
                if group_has_lib_change(pr_cache[n]["filenames"], lib_prefixes)
            ]
            lib_changed_set = set(lib_changed)
            for number in page_numbers:
                if number not in lib_changed_set:
                    log(
                        f"skip PR #{number}: no non-test change under "
                        f"{'/'.join(lib_prefixes)}"
                    )
            _prefetch_reviewed(llvm_repo, lib_changed, reviewed_cache)
            for number in lib_changed:
                if reviewed_cache[number]:
                    log(f"skip PR #{number}: already reviewed, no new commits since")
                    continue
                core = pr_cache[number]
                pr, files = core["pr"], core["files"]
                size = lib_diff_size(files, lib_prefixes)
                label_names = sorted(
                    name for name in core["label_names"] if name in labels
                )
                eligible.append(
                    {
                        "number": number,
                        "head_sha": pr["head"]["sha"],
                        "backends": [group],
                        "group": group,
                        "labels": label_names,
                        "lib_diff_size": size,
                        "url": pr["html_url"],
                        "title": pr["title"],
                        "updated_at": pr["updated_at"],
                        "llvm_repo": llvm_repo,
                    }
                )
                log(
                    f"eligible PR #{number} ({group}, lib_diff={size}): {pr['title']}"
                )
            if len(items) < per_page:
                break
            page += 1
    candidates = select_top_by_lib_size(eligible, limit)
    kept = {c["number"] for c in candidates}
    for c in eligible:
        if c["number"] not in kept:
            log(
                f"drop PR #{c['number']}: outside top {limit} by lib diff "
                f"(size={c['lib_diff_size']})"
            )
    log(
        f"checked {scanned} labeled PR(s) for group={group}, "
        f"eligible={len(eligible)}, kept={len(candidates)} (limit={limit})"
    )
    return candidates


def _candidate_categories(cand):
    """Category tags recorded on a candidate (backends and/or group)."""
    cats = set(cand.get("categories") or [])
    cats.update(cand.get("backends") or [])
    if cand.get("group"):
        cats.add(cand["group"])
    return cats


def merge_candidates_by_number(candidate_lists):
    """Union candidates from several category scans; one entry per PR number.

    Overlaps keep a single candidate and merge category tags into
    ``categories`` / ``backends`` so dispatch still runs once.
    """
    by_number = {}
    for cand_list in candidate_lists:
        for cand in cand_list:
            number = cand["number"]
            if number not in by_number:
                merged = dict(cand)
                cats = sorted(_candidate_categories(merged))
                merged["categories"] = cats
                merged["backends"] = cats
                by_number[number] = merged
                continue
            existing = by_number[number]
            cats = sorted(_candidate_categories(existing) | _candidate_categories(cand))
            existing["categories"] = cats
            existing["backends"] = cats
            if cand.get("group") and not existing.get("group"):
                existing["group"] = cand["group"]
            if cand.get("labels"):
                existing["labels"] = sorted(
                    set(existing.get("labels") or []) | set(cand["labels"])
                )
            if cand.get("lib_diff_size") is not None:
                prev = existing.get("lib_diff_size")
                if prev is None or cand["lib_diff_size"] > prev:
                    existing["lib_diff_size"] = cand["lib_diff_size"]
    return [by_number[n] for n in sorted(by_number)]


def discover_categories(llvm_repo, categories, limit, max_scan_pages=20, per_page=50,
                         on_category_done=None, since_days=DISCOVERY_WINDOW_DAYS,
                         per_label_scan_cap=PER_LABEL_SCAN_CAP):
    """Run each category's discover with its own ``limit``, then dedupe by PR.

    Backend categories (amdgpu/spirv) use label + --auto path gates. Group
    categories (llvm/clang) use their lib-path gates and largest-lib-diff
    ranking. A PR selected by more than one category is kept once.

    If `on_category_done` is given, it's called with the merge-so-far after
    each category finishes (e.g. to checkpoint --state to disk) -- a single
    category can need hundreds of GitHub API calls (discover_group scans
    every eligible PR before ranking), so without a mid-run checkpoint, one
    failure anywhere (rate limit, network blip) throws away every category
    that already completed.
    """
    requested = []
    seen = set()
    for cat in categories:
        if cat not in seen:
            requested.append(cat)
            seen.add(cat)
    if not requested:
        requested = list(DEFAULT_CATEGORIES)

    unknown = [c for c in requested if c not in CATEGORY_CHOICES]
    if unknown:
        sys.exit(
            f"error: unknown categor{'y' if len(unknown) == 1 else 'ies'} "
            f"{unknown}; choose from {list(CATEGORY_CHOICES)}"
        )

    # Shared across every category in this call: a PR that matches more than
    # one (e.g. carries both backend:AMDGPU and backend:SPIR-V, or an AMDGPU
    # PR that also touches llvm/lib/Transforms/) gets its metadata/files and
    # already-reviewed status fetched once total, not once per category.
    pr_cache = {}
    reviewed_cache = {}

    per_category = []
    for cat in requested:
        if cat in BACKEND_LABELS:
            found = discover(
                llvm_repo, limit, max_scan_pages, per_page=per_page, backends=[cat],
                pr_cache=pr_cache, reviewed_cache=reviewed_cache,
                since_days=since_days, per_label_scan_cap=per_label_scan_cap,
            )
            for cand in found:
                cand.setdefault("categories", list(cand.get("backends") or [cat]))
        else:
            found = discover_group(
                llvm_repo, cat, limit, max_scan_pages, per_page=per_page,
                pr_cache=pr_cache, reviewed_cache=reviewed_cache,
                since_days=since_days, per_label_scan_cap=per_label_scan_cap,
            )
            for cand in found:
                cand.setdefault("categories", [cat])
        per_category.append(found)
        log(f"category {cat}: selected {len(found)} PR(s) (limit={limit})")
        if on_category_done is not None:
            on_category_done(merge_candidates_by_number(per_category))

    merged = merge_candidates_by_number(per_category)
    overlap = sum(1 for c in merged if len(c.get("categories") or []) > 1)
    log(
        f"merged {sum(len(x) for x in per_category)} category selection(s) into "
        f"{len(merged)} unique PR(s)"
        + (f" ({overlap} overlapped across categories)" if overlap else "")
    )
    return merged


def normalize_categories(categories=None, backends=None, group=None):
    """Fold --category / --backend / --group into an ordered category list."""
    cats = []
    for c in categories or []:
        cats.append(c)
    for b in backends or []:
        cats.append(b)
    if group:
        if isinstance(group, (list, tuple)):
            cats.extend(group)
        else:
            cats.append(group)
    ordered = []
    seen = set()
    for c in cats:
        if c not in seen:
            ordered.append(c)
            seen.add(c)
    return ordered


def resolve_discover(
    llvm_repo,
    limit,
    max_scan_pages,
    backends=None,
    group=None,
    categories=None,
    on_category_done=None,
    since_days=DISCOVERY_WINDOW_DAYS,
    per_label_scan_cap=PER_LABEL_SCAN_CAP,
):
    cats = normalize_categories(categories, backends, group)
    if not cats:
        cats = list(DEFAULT_CATEGORIES)
    return discover_categories(
        llvm_repo, cats, limit, max_scan_pages, on_category_done=on_category_done,
        since_days=since_days, per_label_scan_cap=per_label_scan_cap,
    )



# --- dispatch -------------------------------------------------------------


def dispatch_one(fuzz_fill_repo, ref, llvm_repo, number, *, upload_tools=False):
    args = [
        "gh", "workflow", "run", "pr-gap-analysis.yml",
        "-R", fuzz_fill_repo,
        "--ref", ref,
        "-f", f"pr_id={number}",
        "-f", f"github_repo={llvm_repo}",
    ]
    if upload_tools:
        args.extend(["-f", "upload_tools=true"])
    subprocess.run(args, check=True)


def run_title_marker(number):
    """Substring unique to this PR's workflow run-name (avoids llvm#1 matching llvm#12)."""
    return f"llvm#{number} by"


def resolve_run_id(fuzz_fill_repo, number, since_iso, known_ids, retries=12, delay=5):
    marker = run_title_marker(number)
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


def list_prior_runs(fuzz_fill_repo, number, per_page=100, max_pages=5):
    """Completed, successful pr-gap-analysis.yml runs for this PR, newest first."""
    marker = run_title_marker(number)
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


def find_cached_run(fuzz_fill_repo, number, head_sha):
    """Look for a prior successful run for this PR that already analyzed
    head_sha, so dispatch() can reuse its artifact instead of scheduling a new run.

    Returns the run_id to reuse, or None if no prior run matches. Warns (and skips
    that run for reuse purposes) if a run's artifacts don't match the naming
    convention this depends on ('gap-finding-results-pr<N>-<run_id>' /
    'pr-head-pr<N>-<run_id>'), since that would otherwise make this check
    silently useless.
    """
    for run in list_prior_runs(fuzz_fill_repo, number):
        run_id = run["id"]
        artifacts = gh_api_json(f"repos/{fuzz_fill_repo}/actions/runs/{run_id}/artifacts?per_page=100")
        names = {a["name"] for a in artifacts.get("artifacts", [])}
        expected_results = _finding_artifact_name(number, run_id)
        expected_head = f"pr-head-pr{number}-{run_id}"
        unrecognized = {n for n in names if not _is_expected_artifact_name(n)}
        if unrecognized:
            log(
                f"warning: run {run_id} (PR #{number}) has artifact(s) "
                f"{sorted(unrecognized)} that don't match the expected "
                f"'gap-finding-results-pr<N>-<run_id>' / 'pr-head-pr<N>-<run_id>' "
                "naming convention -- has the workflow's artifact naming changed? "
                "skipping cache reuse for this run"
            )
            continue
        if expected_results not in names:
            continue
        if expected_head not in names:
            log(
                f"warning: run {run_id} (PR #{number}) has a gap-finding artifact "
                f"but no '{expected_head}' artifact to verify its analyzed commit -- skipping "
                "cache reuse for this run"
            )
            continue
        analyzed_sha = fetch_artifact_text(fuzz_fill_repo, run_id, expected_head)
        if analyzed_sha == head_sha:
            return run_id
    return None


def dispatch(state, state_path, fuzz_fill_repo, ref, llvm_repo, *, upload_tools=False):
    known_ids = {r["run_id"] for r in state["runs"].values() if "run_id" in r}
    for cand in state["candidates"]:
        number = cand["number"]
        head_sha = cand.get("head_sha")
        key = str(number)
        if key in state["runs"]:
            continue
        if head_sha:
            cached_run_id = find_cached_run(fuzz_fill_repo, number, head_sha)
            if cached_run_id is not None:
                log(
                    f"PR #{number}: reusing artifact from run {cached_run_id} "
                    f"(already analyzed {head_sha[:12]}), skipping dispatch"
                )
                known_ids.add(cached_run_id)
                state["runs"][key] = {
                    "run_id": cached_run_id,
                    "status": "completed",
                    "conclusion": "success",
                }
                save_state(state, state_path)
                continue
        since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        log(f"dispatching PR #{number}")
        dispatch_one(
            fuzz_fill_repo, ref, llvm_repo, number, upload_tools=upload_tools,
        )
        run_id = resolve_run_id(fuzz_fill_repo, number, since, known_ids)
        if run_id is None:
            log(f"  warning: could not resolve run id for {key}; check manually")
            continue
        known_ids.add(run_id)
        state["runs"][key] = {
            "run_id": run_id,
            "status": "queued",
            "conclusion": None,
        }
        log(f"  run id: {run_id}")
        save_state(state, state_path)



# --- CLI -----------------------------------------------------------------


def add_common_args(p):
    p.add_argument("--state", required=True, help="Path to the JSON state file")


def add_upload_tools_arg(p):
    p.add_argument(
        "--upload-tools",
        action="store_true",
        help=(
            "Pass upload_tools=true to pr-gap-analysis.yml so the instrumented "
            "opt/llc build is saved as an artifact (~1.2 GB uncompressed)"
        ),
    )


def cmd_discover(args):
    state = load_state(args.state)

    def checkpoint(partial):
        state["candidates"] = partial
        save_state(state, args.state)

    state["candidates"] = resolve_discover(
        args.llvm_repo,
        args.limit,
        args.max_scan_pages,
        backends=args.backend,
        group=getattr(args, "group", None),
        categories=getattr(args, "category", None),
        on_category_done=checkpoint,
        since_days=args.since_days,
        per_label_scan_cap=args.scan_cap,
    )
    save_state(state, args.state)


def cmd_dispatch(args):
    state = load_state(args.state)
    dispatch(
        state, args.state, args.fuzz_fill_repo, args.ref, args.llvm_repo,
        upload_tools=args.upload_tools,
    )


def cmd_run(args):
    """discover then dispatch -- same sequence as the Actions workflow."""
    state = load_state(args.state)
    if not state["candidates"]:
        def checkpoint(partial):
            state["candidates"] = partial
            save_state(state, args.state)

        state["candidates"] = resolve_discover(
            args.llvm_repo,
            args.limit,
            args.max_scan_pages,
            backends=args.backend,
            group=getattr(args, "group", None),
            categories=getattr(args, "category", None),
            on_category_done=checkpoint,
            since_days=args.since_days,
            per_label_scan_cap=args.scan_cap,
        )
        save_state(state, args.state)
    dispatch(
        state, args.state, args.fuzz_fill_repo, args.ref, args.llvm_repo,
        upload_tools=args.upload_tools,
    )


def add_discover_scope_args(p):
    p.add_argument(
        "--category",
        choices=list(CATEGORY_CHOICES),
        action="append",
        help=(
            "Repeatable discovery category: amdgpu, spirv, llvm, clang. "
            "Each gets its own --limit; overlapping PRs are deduped. "
            "Default when none of --category/--backend/--group is set: "
            "amdgpu and spirv"
        ),
    )
    p.add_argument(
        "--backend",
        choices=["amdgpu", "spirv"],
        action="append",
        help="Alias for --category amdgpu|spirv (repeatable; can combine with --group/--category)",
    )
    p.add_argument(
        "--group",
        choices=sorted(GROUP_CONFIGS),
        action="append",
        help="Alias for --category llvm|clang (repeatable; can combine with --backend/--category)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max candidates to keep per category (default: 20)",
    )
    p.add_argument("--max-scan-pages", type=int, default=20)
    p.add_argument(
        "--since-days",
        type=int,
        default=DISCOVERY_WINDOW_DAYS,
        help=(
            "Only scan PRs updated in the last N days (0 disables the window; "
            f"default: {DISCOVERY_WINDOW_DAYS})"
        ),
    )
    p.add_argument(
        "--scan-cap",
        type=int,
        default=PER_LABEL_SCAN_CAP,
        help=(
            "Stop scanning a single label after this many PRs, even if quota/"
            f"max-scan-pages would allow more (default: {PER_LABEL_SCAN_CAP})"
        ),
    )


def main():
    check_gh()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("discover", help="Find candidate PRs, write them to --state")
    add_common_args(p)
    p.add_argument("--llvm-repo", default=DEFAULT_LLVM_REPO)
    add_discover_scope_args(p)
    p.set_defaults(func=cmd_discover)

    p = sub.add_parser("dispatch", help="Trigger pr-gap-analysis.yml for candidates in --state")
    add_common_args(p)
    p.add_argument("--fuzz-fill-repo", default=DEFAULT_FUZZ_FILL_REPO)
    p.add_argument("--ref", default=DEFAULT_REF)
    p.add_argument("--llvm-repo", default=DEFAULT_LLVM_REPO)
    add_upload_tools_arg(p)
    p.set_defaults(func=cmd_dispatch)

    p = sub.add_parser("run", help="Run discover then dispatch")
    add_common_args(p)
    p.add_argument("--llvm-repo", default=DEFAULT_LLVM_REPO)
    p.add_argument("--fuzz-fill-repo", default=DEFAULT_FUZZ_FILL_REPO)
    p.add_argument("--ref", default=DEFAULT_REF)
    add_discover_scope_args(p)
    add_upload_tools_arg(p)
    p.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
