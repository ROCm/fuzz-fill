#!/usr/bin/env python3
"""GitHub helpers shared by the pr-gap scripts.

Owns `gh api` access with retries and the lookup of pr-analysis-result
report issues, so pr-gap-scan.py and pr-gap-file-issue.sh agree on how an
issue is tied to a PR. Stdlib-only.

CLI (used by pr-gap-file-issue.sh):
  pr_gap_github.py keys --llvm-repo L --pr N --run-id ID --head SHA
      Print the label, Tracking-PR line, Workflow-Run line, analyzed-head
      sentence and Analyzed-Head line, one per line.
  pr_gap_github.py find-open --repo R --llvm-repo L --pr N
      Print the oldest open report issue for the PR, or nothing.
  pr_gap_github.py mentions --repo R --issue N --text T
      Print the issue number if its body or a comment contains T, or nothing.
"""

import argparse
import json
import subprocess
import sys
import time

REPORT_ISSUE_LABEL = "pr-analysis-result"


def log(msg):
    print(msg, file=sys.stderr)


def gh_api_json(path, retries=5, backoff=2.0):
    """GET `path` via `gh api`, retrying transient failures.

    Concurrent discovery in pr-gap-scan.py fires several of these at once,
    which makes hitting GitHub's secondary rate limit or a one-off network
    blip more likely; without a retry one flaky call aborts a whole run.
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


def tracking_key(llvm_repo, number):
    """The line pr-gap-file-issue.sh writes to tie an issue to a PR.

    redirect.github.com keeps GitHub from backlinking the issue onto the PR.
    """
    return f"Tracking-PR: https://redirect.github.com/{llvm_repo}/pull/{number}"


def tracking_keys(llvm_repo, number):
    """Current key first, then the plain form written on earlier issues."""
    return (tracking_key(llvm_repo, number), f"Tracking-PR: {llvm_repo}/pull/{number}")


def workflow_run_key(run_id):
    return f"Workflow-Run: {run_id}"


def analyzed_head_line(head_sha):
    """The sentence a reader sees naming the analyzed head."""
    return f"Analyzed head `{head_sha[:12]}` (`{head_sha}`)."


def analyzed_head_key(head_sha):
    return f"Analyzed-Head: {head_sha}"


def analyzed_head_markers(head_sha):
    """Text that shows a report covers head_sha. Issues filed before
    Analyzed-Head existed carry only the sentence."""
    return (analyzed_head_key(head_sha), analyzed_head_line(head_sha))


def find_pr_issues(repo, llvm_repo, number, state="open"):
    """Report issues in `repo` for the PR, oldest first. `state`: open|closed|all."""
    keys = tracking_keys(llvm_repo, number)
    issues = gh_api_paginated(
        f"repos/{repo}/issues?state={state}&labels={REPORT_ISSUE_LABEL}"
    )
    matches = [
        i for i in issues
        if i.get("pull_request") is None
        and any(k in (i.get("body") or "") for k in keys)
    ]
    return sorted(matches, key=lambda i: i["number"])


def issue_mentions(repo, issue, *texts):
    """True if the issue body or any of its comments contains one of `texts`.

    Later runs on the same PR post as comments, not as new issues.
    """
    def has(body):
        return any(t in (body or "") for t in texts)

    if has(issue.get("body")):
        return True
    comments = gh_api_paginated(f"repos/{repo}/issues/{issue['number']}/comments")
    return any(has(c.get("body")) for c in comments)


def _cmd_keys(args):
    print(REPORT_ISSUE_LABEL)
    print(tracking_key(args.llvm_repo, args.pr))
    print(workflow_run_key(args.run_id))
    print(analyzed_head_line(args.head))
    print(analyzed_head_key(args.head))


def _cmd_find_open(args):
    issues = find_pr_issues(args.repo, args.llvm_repo, args.pr, state="open")
    if issues:
        print(issues[0]["number"])


def _cmd_mentions(args):
    issue = gh_api_json(f"repos/{args.repo}/issues/{args.issue}")
    if issue_mentions(args.repo, issue, args.text):
        print(issue["number"])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("keys", help="label and key lines written on report issues")
    p.add_argument("--llvm-repo", required=True)
    p.add_argument("--pr", required=True, type=int)
    p.add_argument("--run-id", required=True)
    p.add_argument("--head", required=True)
    p.set_defaults(func=_cmd_keys)

    p = sub.add_parser("find-open", help="oldest open report issue for a PR")
    p.add_argument("--repo", required=True)
    p.add_argument("--llvm-repo", required=True)
    p.add_argument("--pr", required=True, type=int)
    p.set_defaults(func=_cmd_find_open)

    p = sub.add_parser("mentions", help="whether an issue body or comment contains text")
    p.add_argument("--repo", required=True)
    p.add_argument("--issue", required=True, type=int)
    p.add_argument("--text", required=True)
    p.set_defaults(func=_cmd_mentions)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
