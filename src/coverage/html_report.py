# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Write a self-contained HTML coverage report from ``line_coverage_summary.csv``."""

from __future__ import annotations

import html
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from coverage.line_coverage_summary import load_line_coverage_summary

STATUS_TO_CLASS = {
    "covered": "covered",
    "partially": "partially-covered",
    "uncovered": "not-covered",
}

# Per-file source pages: caveats + color meaning for the line view.
SOURCE_LEGEND_HTML = """\
<div class="legend">
  <p>Colors come from debug information in an optimized build using
    SanitizerCoverage, so a source line may have no color because its code was
    removed or merged.</p>
  <p>Some blocks are not instrumented when a dominator already implies they ran.
    A source line can have no color even though it executes.</p>
  <p><span class="swatch covered"></span>
    <strong>Green — covered.</strong>
    Every instrumentation point on this line ran.</p>
  <p><span class="swatch partially-covered"></span>
    <strong>Orange — partially.</strong>
    SanitizerCoverage can insert several points on one line.
    Some of the instrumentation points ran, but not all.</p>
  <p><span class="swatch not-covered"></span>
    <strong>Red — uncovered.</strong>
    No instrumentation point on this line ran.</p>
  <p><strong>No color.</strong>
    This line has no instrumentation points, so it is not in the coverage counts.</p>
</div>
"""

# Index: purpose + how coverage is computed (per-line legend is on file pages).
INDEX_INTRO_HTML = """\
<div class="legend">
  <p>This report is designed to highlight <strong>coverage gaps</strong>:
    source lines that were uncovered in this test-suite run.</p>
  <p>It comes from an LLVM build with <strong>SanitizerCoverage</strong>.
    A test run records executed instrumentation points and maps them to source
    lines via debug information.</p>
  <p>Lines are then:</p>
  <ul class="status-list">
    <li><span class="swatch covered"></span>
      <strong>covered</strong> (every point on the line ran)</li>
    <li><span class="swatch partially-covered"></span>
      <strong>partial</strong> (some ran)</li>
    <li><span class="swatch not-covered"></span>
      <strong>uncovered</strong> (none ran)</li>
  </ul>
  <p>The tree is sorted by uncovered count so gaps surface first;
    open a file for the line view.</p>
</div>
"""

SHARED_CSS = """\
    body { font-family: sans-serif; margin: 1.5rem; }
    .covered { background: #d1fae5; }
    .partially-covered { background: #fef3c7; }
    .not-covered { background: #ffe4e6; }
    /* Keep index prose, stats, and tree on one column width. */
    .legend, .totals, .tree, body > h2, body > p {
      max-width: 52rem;
    }
    .legend { line-height: 1.5; }
    .legend p { margin: 0.45rem 0; }
    .legend .status-list {
      list-style: none; margin: 0.35rem 0 0.55rem; padding: 0;
    }
    .legend .status-list li { margin: 0.2rem 0; }
    .swatch {
      display: inline-block; width: 1em; height: 1em;
      vertical-align: middle; margin-right: 0.35rem; border: 1px solid #ccc;
    }
    .swatch.covered { background: #34d399; }
    .swatch.partially-covered { background: #fbbf24; }
    .swatch.not-covered { background: #fb7185; }
    .totals { margin: 1rem 0; }
    .totals li { margin: 0.2rem 0; }
    .source {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px; line-height: 1.4;
      border: 1px solid #ddd; background: #fff;
      overflow-x: auto; margin: 0; padding: 0;
    }
    .line {
      display: flex; align-items: stretch;
      position: relative;
      min-height: 1.4em; white-space: pre;
    }
    .gutter {
      flex: 0 0 3.75em; box-sizing: border-box;
      padding: 0 0.5em 0 0; text-align: right;
      color: #888; text-decoration: none; user-select: none;
      background: #f6f6f6; border-right: 1px solid #e2e2e2;
      font-variant-numeric: tabular-nums;
    }
    .gutter:hover { color: #111; text-decoration: underline; }
    /* Mouse click leaves :focus on the gutter; kill the browser box. */
    .gutter:focus { outline: none; }
    .gutter:focus-visible { outline: 2px solid #2563eb; outline-offset: -2px; }
    .code { flex: 1 1 auto; padding: 0 0.75em; min-width: 0; }
    .tree { font-family: monospace; font-size: 0.9rem; }
    .tree details { margin-left: 0.85rem; }
    .tree > details { margin-left: 0; }
    .tree summary {
      cursor: pointer; list-style: none; padding: 0.15rem 0;
    }
    .tree summary::-webkit-details-marker { display: none; }
    .tree summary::before { content: "▸ "; color: #666; }
    .tree details[open] > summary::before { content: "▾ "; }
    .tree .dir-name { font-weight: 600; }
    .tree .counts {
      color: #555; font-variant-numeric: tabular-nums; margin-left: 0.5rem;
    }
    .tree .file-row {
      margin-left: 1.6rem; padding: 0.1rem 0;
    }
    .tree .file-row a { text-decoration: none; }
    .tree .file-row a:hover { text-decoration: underline; }
    .jump-bar {
      position: sticky; top: 0; z-index: 1;
      background: #f7f7f7; border: 1px solid #ddd; border-radius: 4px;
      padding: 0.4rem 0.6rem; margin: 0.75rem 0 1rem;
      display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;
    }
    .jump-bar button {
      font: inherit; cursor: pointer; padding: 0.2rem 0.55rem;
    }
    .jump-bar button.mode-active {
      background: #2563eb; color: #fff; border-color: #1d4ed8;
    }
    .jump-bar .hint { color: #666; font-size: 0.9rem; }
    .jump-bar .mode-group {
      display: flex; flex-wrap: wrap; gap: 0.25rem; align-items: center;
    }
    /* Current target: left rail (does not fight coverage fills). */
    .line.jump-current {
      box-shadow: inset 3px 0 0 #2563eb;
    }
    .line.jump-current .gutter {
      color: #1d4ed8; font-weight: 600; background: #dbeafe;
    }
    /* Brief amber flash on land — same cue as GitHub #Lnn. */
    .line.jump-flash::after {
      content: "";
      position: absolute; inset: 0;
      pointer-events: none;
      background: #fef08a;
      animation: jump-flash-fade 1.15s ease-out forwards;
    }
    @keyframes jump-flash-fade {
      from { opacity: 0.75; }
      to { opacity: 0; }
    }
"""

SOURCE_PAGE_SCRIPT = """\
<script>
(function () {
  let current = null;

  function focusLine(el, { scroll } = { scroll: true }) {
    if (!el) return;
    if (current) {
      current.classList.remove("jump-current", "jump-flash");
    }
    current = el;
    el.classList.add("jump-current");
    // Retrigger the flash even when re-focusing the same line.
    void el.offsetWidth;
    el.classList.add("jump-flash");
    el.addEventListener(
      "animationend",
      () => el.classList.remove("jump-flash"),
      { once: true }
    );
    if (scroll) el.scrollIntoView({ block: "center" });
    history.replaceState(null, "", "#" + el.id);
    // Drop leftover focus ring on a previously clicked gutter number.
    const active = document.activeElement;
    if (active && active.classList && active.classList.contains("gutter")) {
      active.blur();
    }
  }

  // Gutter clicks: center the line instead of the browser's default
  // jump-to-top hash scroll.
  document.querySelectorAll("a.gutter").forEach((a) => {
    a.addEventListener("click", (ev) => {
      const el = document.getElementById(a.getAttribute("href").slice(1));
      if (!el) return;
      ev.preventDefault();
      focusLine(el);
      a.blur();
    });
  });

  const bar = document.getElementById("jump-bar");
  if (!bar) return;

  const modes = [
    {
      id: "uncovered",
      label: "uncovered",
      lines: Array.from(document.querySelectorAll("div.line.not-covered")),
    },
    {
      id: "partially",
      label: "partially",
      lines: Array.from(
        document.querySelectorAll("div.line.partially-covered")
      ),
    },
    {
      id: "covered",
      label: "covered",
      lines: Array.from(document.querySelectorAll("div.line.covered")),
    },
    {
      id: "instrumented",
      label: "instrumented",
      lines: Array.from(
        document.querySelectorAll(
          "div.line.covered, div.line.partially-covered, div.line.not-covered"
        )
      ),
    },
  ].filter((m) => m.lines.length > 0);

  if (!modes.length) return;

  const status = document.getElementById("jump-status");
  const nextBtn = document.getElementById("jump-next");
  const prevBtn = document.getElementById("jump-prev");
  const modeBtns = Array.from(bar.querySelectorAll("button[data-mode]"));
  let modeIdx = 0;
  // Prefer uncovered when present.
  for (let i = 0; i < modes.length; i++) {
    if (modes[i].id === "uncovered") { modeIdx = i; break; }
  }
  let idx = -1;

  function lines() { return modes[modeIdx].lines; }

  function setStatus() {
    if (!status) return;
    const m = modes[modeIdx];
    status.textContent = (idx < 0)
      ? (m.lines.length + " " + m.label)
      : ((idx + 1) + " / " + m.lines.length + " " + m.label);
  }

  function setModeActive() {
    const id = modes[modeIdx].id;
    for (const btn of modeBtns) {
      btn.classList.toggle("mode-active", btn.dataset.mode === id);
    }
    setStatus();
  }

  function syncIdxToCurrent() {
    if (!current) { idx = -1; return; }
    const i = lines().indexOf(current);
    idx = i;
  }

  function setMode(nextIdx) {
    if (!modes.length) return;
    modeIdx = ((nextIdx % modes.length) + modes.length) % modes.length;
    syncIdxToCurrent();
    setModeActive();
  }

  function go(delta) {
    const list = lines();
    if (!list.length) return;
    if (idx < 0) {
      const mid = window.scrollY + window.innerHeight / 2;
      let best = 0;
      let bestDist = Infinity;
      for (let i = 0; i < list.length; i++) {
        const top = list[i].getBoundingClientRect().top + window.scrollY;
        const dist = Math.abs(top - mid);
        if (dist < bestDist) { bestDist = dist; best = i; }
      }
      idx = best - (delta > 0 ? 1 : -1);
    }
    idx = (idx + delta + list.length) % list.length;
    focusLine(list[idx]);
    setStatus();
  }

  if (nextBtn) nextBtn.addEventListener("click", () => go(1));
  if (prevBtn) prevBtn.addEventListener("click", () => go(-1));
  for (const btn of modeBtns) {
    btn.addEventListener("click", () => {
      const i = modes.findIndex((m) => m.id === btn.dataset.mode);
      if (i >= 0) setMode(i);
    });
  }

  document.addEventListener("keydown", (ev) => {
    if (ev.target && /INPUT|TEXTAREA|SELECT/.test(ev.target.tagName)) return;
    if (ev.key === "n") { ev.preventDefault(); go(1); }
    else if (ev.key === "j") { ev.preventDefault(); go(-1); }
    else if (ev.key === "m") { ev.preventDefault(); setMode(modeIdx + 1); }
  });

  setModeActive();

  const hash = location.hash.replace(/^#/, "");
  if (hash) {
    const el = document.getElementById(hash);
    if (el) {
      // Re-center after the browser's initial hash jump-to-top.
      focusLine(el);
      syncIdxToCurrent();
      setStatus();
    }
  }
})();
</script>
"""


@dataclass(frozen=True)
class FileStats:
    path: str  # stripped display path
    source_path: Path  # absolute path from CSV
    covered: int
    partially: int
    uncovered: int

    @property
    def instrumented(self) -> int:
        return self.covered + self.partially + self.uncovered

    @property
    def basename(self) -> str:
        return Path(self.path).name


@dataclass
class TreeNode:
    name: str
    children: dict[str, TreeNode] = field(default_factory=dict)
    files: list[FileStats] = field(default_factory=list)
    covered: int = 0
    partially: int = 0
    uncovered: int = 0

    @property
    def instrumented(self) -> int:
        return self.covered + self.partially + self.uncovered


def _strip_path(abs_path: str, strip_prefix: Path | None) -> str:
    if strip_prefix is None:
        return abs_path
    prefix = str(strip_prefix.resolve())
    path = str(Path(abs_path).resolve())
    if path == prefix:
        return Path(abs_path).name
    prefix_slash = prefix.rstrip("/") + "/"
    if path.startswith(prefix_slash):
        return path[len(prefix_slash) :]
    return abs_path


def _pct(part: int, whole: int) -> str:
    if whole == 0:
        return "0.0%"
    return f"{100.0 * part / whole:.1f}%"


def _rel_to_index(page_rel: str) -> str:
    depth = len(Path(page_rel).parts) - 1
    if depth <= 0:
        return "index.html"
    return "../" * depth + "index.html"


def _page_relpath(stripped: str) -> str:
    return f"{stripped}.html"


def _counts_span(covered: int, partially: int, uncovered: int) -> str:
    instrumented = covered + partially + uncovered
    return (
        f'<span class="counts">'
        f"instr={instrumented} "
        f"cov={covered} ({_pct(covered, instrumented)}) "
        f"part={partially} ({_pct(partially, instrumented)}) "
        f"unc={uncovered} ({_pct(uncovered, instrumented)})"
        f"</span>"
    )


def _aggregate(
    coverage_by_line: dict[tuple[str, int], str],
    strip_prefix: Path | None,
) -> tuple[list[FileStats], TreeNode, dict[str, dict[int, str]]]:
    """Build per-file stats, a path tree, and line status maps."""
    by_file: dict[str, dict[str, int]] = defaultdict(
        lambda: {"covered": 0, "partially": 0, "uncovered": 0}
    )
    source_by_stripped: dict[str, Path] = {}
    lines_by_stripped: dict[str, dict[int, str]] = defaultdict(dict)

    for (file_path, line), status in coverage_by_line.items():
        if status not in STATUS_TO_CLASS:
            raise SystemExit(
                f"unexpected coverage status {status!r} for {file_path}:{line}"
            )
        stripped = _strip_path(file_path, strip_prefix)
        by_file[stripped][status] += 1
        source_by_stripped[stripped] = Path(file_path)
        lines_by_stripped[stripped][int(line)] = status

    files = [
        FileStats(
            path=path,
            source_path=source_by_stripped[path],
            covered=counts["covered"],
            partially=counts["partially"],
            uncovered=counts["uncovered"],
        )
        for path, counts in by_file.items()
    ]
    files.sort(key=lambda f: (-f.uncovered, f.path))

    root = TreeNode(name="")
    for f in files:
        parts = Path(f.path).parts
        if not parts:
            continue
        node = root
        for part in parts[:-1]:
            if part not in node.children:
                node.children[part] = TreeNode(name=part)
            node = node.children[part]
        node.files.append(f)

    def _rollup(node: TreeNode) -> None:
        covered = partially = uncovered = 0
        for child in node.children.values():
            _rollup(child)
            covered += child.covered
            partially += child.partially
            uncovered += child.uncovered
        for f in node.files:
            covered += f.covered
            partially += f.partially
            uncovered += f.uncovered
        node.covered = covered
        node.partially = partially
        node.uncovered = uncovered
        node.files.sort(key=lambda f: (-f.uncovered, f.basename))
        # Sort child dirs by uncovered descending, then name.
        ordered = sorted(
            node.children.items(),
            key=lambda item: (-item[1].uncovered, item[0]),
        )
        node.children = dict(ordered)

    _rollup(root)
    return files, root, lines_by_stripped


def _render_tree_node(
    node: TreeNode,
    written_pages: set[str],
) -> str:
    # Mix child directories and files at this level, hottest (most uncovered) first.
    entries: list[tuple[int, str, str]] = []
    for child in node.children.values():
        body = _render_tree_node(child, written_pages)
        summary = (
            f'<span class="dir-name">{html.escape(child.name)}/</span>'
            f"{_counts_span(child.covered, child.partially, child.uncovered)}"
        )
        entries.append(
            (
                child.uncovered,
                child.name,
                f"<details><summary>{summary}</summary>\n{body}</details>",
            )
        )
    for f in node.files:
        page = _page_relpath(f.path)
        name = html.escape(f.basename)
        if f.path in written_pages:
            label = f'<a href="{html.escape(page)}">{name}</a>'
        else:
            label = name
        entries.append(
            (
                f.uncovered,
                f.basename,
                f'<div class="file-row">{label}'
                f"{_counts_span(f.covered, f.partially, f.uncovered)}</div>",
            )
        )
    entries.sort(key=lambda item: (-item[0], item[1]))
    return "\n".join(html_chunk for _, _, html_chunk in entries)


def _render_source_page(
    *,
    display_path: str,
    source_text: str,
    line_status: dict[int, str],
    index_href: str,
) -> str:
    rows: list[str] = []
    counts = {"covered": 0, "partially": 0, "uncovered": 0}
    for line_no, line in enumerate(source_text.splitlines(), start=1):
        status = line_status.get(line_no)
        status_cls = STATUS_TO_CLASS.get(status, "") if status else ""
        if status in counts:
            counts[status] += 1
        classes = "line " + status_cls if status_cls else "line"
        # Do not put newlines between rows — they show up as blank gaps.
        escaped = html.escape(line.rstrip("\n"), quote=False) or "&nbsp;"
        rows.append(
            f'<div id="L{line_no}" class="{classes}">'
            f'<a class="gutter" href="#L{line_no}">{line_no}</a>'
            f'<span class="code">{escaped}</span></div>'
        )
    body = "".join(rows)
    instrumented = counts["covered"] + counts["partially"] + counts["uncovered"]
    if instrumented:
        mode_btns: list[str] = []
        if counts["uncovered"]:
            mode_btns.append(
                '<button type="button" data-mode="uncovered">uncovered</button>'
            )
        if counts["partially"]:
            mode_btns.append(
                '<button type="button" data-mode="partially">partially</button>'
            )
        if counts["covered"]:
            mode_btns.append(
                '<button type="button" data-mode="covered">covered</button>'
            )
        mode_btns.append(
            '<button type="button" data-mode="instrumented">instrumented</button>'
        )
        if counts["uncovered"]:
            default_label, default_count = "uncovered", counts["uncovered"]
        elif counts["partially"]:
            default_label, default_count = "partially", counts["partially"]
        elif counts["covered"]:
            default_label, default_count = "covered", counts["covered"]
        else:
            default_label, default_count = "instrumented", instrumented
        jump_bar = f"""\
  <div class="jump-bar" id="jump-bar">
    <button type="button" id="jump-prev">Previous</button>
    <button type="button" id="jump-next">Next</button>
    <span id="jump-status" class="hint">{default_count} {default_label}</span>
    <span class="mode-group">{"".join(mode_btns)}</span>
    <span class="hint">Keys: <kbd>n</kbd> next, <kbd>j</kbd> previous, <kbd>m</kbd> mode</span>
  </div>
"""
    else:
        jump_bar = ""

    return f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{html.escape(display_path)}</title>
  <style>
{SHARED_CSS}
  </style>
</head>
<body>
  <p><a href="{html.escape(index_href)}">Back to index</a></p>
  <h1>{html.escape(display_path)}</h1>
{SOURCE_LEGEND_HTML}
{jump_bar}  <div class="source">{body}</div>
{SOURCE_PAGE_SCRIPT}</body>
</html>
"""


def _render_run_meta(
    *,
    github_repo: str | None = None,
    llvm_ref: str | None = None,
    commit: str | None = None,
    projects: str | None = None,
    backends: str | None = None,
    tests: list[str] | None = None,
) -> str:
    """Optional run identity / scope lines for the index."""
    rows: list[str] = []
    if github_repo:
        rows.append(f"<li>Repository: {html.escape(github_repo)}</li>")
    if llvm_ref:
        rows.append(f"<li>Ref: {html.escape(llvm_ref)}</li>")
    if commit:
        rows.append(f"<li>Commit: {html.escape(commit)}</li>")
    if projects is not None:
        label = projects if projects else "none"
        rows.append(f"<li>Projects: {html.escape(label)}</li>")
    if backends:
        rows.append(f"<li>Backends: {html.escape(backends)}</li>")
    if tests:
        suites = ", ".join(html.escape(t) for t in tests)
        rows.append(f"<li>Tests: {suites}</li>")
    if not rows:
        return ""
    return (
        '  <h2>Run</h2>\n'
        '  <ul class="totals">\n'
        + "".join(f"    {row}\n" for row in rows)
        + "  </ul>\n"
    )


def _render_index(
    *,
    files: list[FileStats],
    tree: TreeNode,
    written_pages: set[str],
    github_repo: str | None = None,
    llvm_ref: str | None = None,
    commit: str | None = None,
    projects: str | None = None,
    backends: str | None = None,
    tests: list[str] | None = None,
) -> str:
    total_c = sum(f.covered for f in files)
    total_p = sum(f.partially for f in files)
    total_u = sum(f.uncovered for f in files)
    total_i = total_c + total_p + total_u
    tree_html = _render_tree_node(tree, written_pages)
    run_meta = _render_run_meta(
        github_repo=github_repo,
        llvm_ref=llvm_ref,
        commit=commit,
        projects=projects,
        backends=backends,
        tests=tests,
    )

    return f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Coverage Gaps Report</title>
  <style>
{SHARED_CSS}
  </style>
</head>
<body>
  <h1>Coverage Gaps Report</h1>
{INDEX_INTRO_HTML}
{run_meta}  <h2>Statistics</h2>
  <ul class="totals">
    <li>Instrumented lines: {total_i}</li>
    <li>Covered: {total_c} ({_pct(total_c, total_i)})</li>
    <li>Partially: {total_p} ({_pct(total_p, total_i)})</li>
    <li>Uncovered: {total_u} ({_pct(total_u, total_i)})</li>
  </ul>
  <h2>Directory Tree</h2>
  <p>Directories and files, nested like a filesystem. Expand a directory to see
    its children. Entries at each level are sorted by uncovered lines
    (descending).</p>
  <div class="tree">
{tree_html}
  </div>
</body>
</html>
"""


def write_html_report(
    summary_csv: Path,
    output_dir: Path,
    *,
    strip_prefix: Path | None = None,
    github_repo: str | None = None,
    llvm_ref: str | None = None,
    commit: str | None = None,
    projects: str | None = None,
    backends: str | None = None,
    tests: list[str] | None = None,
) -> None:
    """Build ``index.html`` and per-file pages under ``output_dir``.

    Optional run metadata (repo, ref, commit, projects, backends, tests) is
    shown on the index when provided. ``backends`` is LLVM_TARGETS_TO_BUILD;
    ``projects`` is LLVM_ENABLE_PROJECTS extras (e.g. ``clang``); ``tests``
    are the lit suites passed as ``--tests``.
    """
    coverage_by_line, _ = load_line_coverage_summary(summary_csv)
    files, tree, lines_by_stripped = _aggregate(coverage_by_line, strip_prefix)

    if output_dir.exists():
        # Replace a previous report so stale pages do not linger.
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written_pages: set[str] = set()
    for f in files:
        src = f.source_path
        if not src.is_file():
            print(
                f"warning: html-report: skipping missing source {src}",
                file=sys.stderr,
            )
            continue
        try:
            text = src.read_text(encoding="utf-8")
        except OSError as exc:
            print(
                f"warning: html-report: skipping unreadable source {src}: {exc}",
                file=sys.stderr,
            )
            continue

        page_rel = _page_relpath(f.path)
        page_path = output_dir / page_rel
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(
            _render_source_page(
                display_path=f.path,
                source_text=text,
                line_status=lines_by_stripped[f.path],
                index_href=_rel_to_index(page_rel),
            ),
            encoding="utf-8",
        )
        written_pages.add(f.path)

    (output_dir / "index.html").write_text(
        _render_index(
            files=files,
            tree=tree,
            written_pages=written_pages,
            github_repo=github_repo,
            llvm_ref=llvm_ref,
            commit=commit,
            projects=projects,
            backends=backends,
            tests=tests,
        ),
        encoding="utf-8",
    )
