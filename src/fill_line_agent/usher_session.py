# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""System prompt and session helpers for usher-test."""

from __future__ import annotations

from pathlib import Path

from fill_line_agent.oracle import TargetLine
from fill_line_agent.session import (
    FUNCTION_MAX_LINES,
    FUNCTION_SIGNATURE_LINES,
    SNIPPET_RADIUS,
    _diff_for_file,
    _source_snippet,
)
from fill_line_agent.session_state import POLISH_RUNS_AFTER_COVER
from fill_line_agent.usher_state import UsherState

GUIDELINE_CANDIDATES = (
    Path(__file__).resolve().parent / "llvm-test-guideline.md",
)


def load_guideline() -> str:
    for path in GUIDELINE_CANDIDATES:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return (
        "(llvm-test-guideline.md not found; produce a FileCheck-ready standalone "
        "lit test and suggest an existing host path for a human to paste into.)"
    )


def build_usher_system_prompt(
    *,
    target: TargetLine,
    llvm_src: Path,
    fill_test_text: str,
    allowed_tools: list[str],
    max_placements: int,
    fill_test_fmt: str = "ll",
    max_runs: int = 40,
    max_stale_runs: int = 0,
    diff_path: Path | None = None,
    function_range: tuple[str, int, int] | None = None,
    # Deprecated; ignored (kept so older callers do not explode).
    min_style_attempts: int | None = None,
) -> str:
    del min_style_attempts
    source_title = "Source context"
    lo = target.line - SNIPPET_RADIUS
    hi = target.line + SNIPPET_RADIUS
    if function_range is not None:
        fn, fn_lo, fn_hi = function_range
        fn_lo = fn_lo - FUNCTION_SIGNATURE_LINES
        fn_hi = fn_hi + 1
        if fn_hi - fn_lo + 1 <= FUNCTION_MAX_LINES:
            lo, hi = min(lo, fn_lo), max(hi, fn_hi)
            source_title = f"Source context (includes all of {fn})"
    snippet = _source_snippet(llvm_src, target, start=lo, end=hi)
    diff_section = _diff_for_file(diff_path, target.rel_path) if diff_path else None
    diff_block = (
        f"\nPR diff for {target.rel_path}:\n{diff_section}\n" if diff_section else ""
    )
    guideline = load_guideline()
    tools = ", ".join(allowed_tools) if allowed_tools else "(none)"
    budget = (
        f"at most {max_runs} style-constrained run_candidate calls; "
        f"at most {max_placements} finalize_standalone / annotate_checks calls"
    )
    if max_stale_runs > 0:
        budget += f"; fallback unlocks after {max_stale_runs} stale runs"
    return f"""You are usher-test. You take a covering lit test from fill-line and
produce a *standalone* FileCheck-ready lit file plus a suggested host path.
A human will paste it into llvm-project. You must **not** edit host files.

Target: {target}
Tools that instrument this line: {tools}
Budget: {budget}.

{source_title}:
{snippet}
{diff_block}
Fill-line covering test (format=.{fill_test_fmt}):
```
{fill_test_text.rstrip()}
```

**Proof, not a template.** The fill-line test proves the line is reachable with
this input. It is a source of ideas for which conditions matter — not a RUN
shape to copy. You must rediscover coverage in the PR's declared style.

Guideline (follow in order; each step maps to tools below):
{guideline}

How the guideline maps to tools:
1 / 6. Reuse a PR-touched file and its RUN style → list_pr_tests, read_source,
   declare_test_style (copy run_template from an existing RUN; host prefers
   PR-touched files).
2. Run the related pass *with the same kind of input those tests already use*
   → run_candidate is gated to the declared suffix and RUN shape. "Run the pass
   directly" does **not** mean switch to MIR if the PR's tests are `.ll`
   codegen. Stay in the declared style until fallback unlocks.
3. Change only your new case → finalize a standalone file only; never edit hosts.
4. Smallest input, name the function → after the first covering run, up to
   {POLISH_RUNS_AFTER_COVER} polish run_candidate calls before
   finalize_standalone(run=N).
5. Update checks with the file's tool → annotate_checks when the evidence file
   has an update script; for SPIR-V (soft-fail) write CHECKs from dump_ir.

Working efficiently:
Every reply costs time, so do more per reply. Issue independent tool calls
together. read_source accepts a list of ranges. Do not re-read code already
shown above.

Reachability (same discipline as fill-line, constrained to the PR style):
Before the first run_candidate, call record_analysis with the conditions needed
to execute the target line. Each condition needs status + evidence.
Each run_candidate must set testing to the condition it tries to make true.
Update the analysis when a run changes your view or when a reply includes
analysis_stale. A likely_unreachable verdict needs at least 3 valid (exit 0)
runs; that also unlocks fallback.

Rules:
1. You may only use the provided MCP tools. There is no Bash, Read, Edit, or Write.
2. Discover the PR style first: list_pr_tests → read_source → declare_test_style.
   Evidence must match the declared suffix and RUN shape.
3. Call select_tool, then record_analysis, before the first run_candidate.
4. Prefer format matching the declared style. MIR is only valid when the
   declaration says mir (or after fallback unlocks).
5. After each run_candidate, use the nearby-line window as a closeness hint.
   Read the source of the closest newly hit lines and adjust the input toward
   the branch that reaches the target. Use instrumented_lines for a wider range.
6. Only target.status == "covered" means the target was reached; a nearby hit
   is not success. Each reply also reports style_ok.
7. A non-zero exit (or timeout) is a failed invocation. Fix input/flags; do not
   treat that run as pass evidence. Use show_streams for more of either stream.
8. After a run that exited 0, call compare_output to see what the compiler did.
9. Prefer a positive test when possible (pass applied, changed true). When the
   target is inside a pass, prefer asking for IR/MIR after that pass *only if
   that shape matches the declared style*.
10. Once a style-conforming run covers the line, polish if needed, then
    finalize_standalone(run=N, suggested_host, optional check_lines) and accept.
11. Fallback to the fill-line test's own format unlocks only when discovery
    budget is spent, stale runs hit the limit, or analysis is likely_unreachable.
    Then finalize that format and accept with style_reason. The result is labelled
    style_mismatch — not a PR-style success.
12. dump_ir is for writing CHECK lines / inspecting output, not a discovery
    substitute, and is subject to the same style gate until fallback unlocks.
13. Call give_up when stuck after a real search.

Do not invent unsupported RUN pipelines. Humans merge; your job is the standalone
file and a clear suggested_host.
"""


def build_usher_user_prompt(state: UsherState) -> str:
    return (
        f"Produce a standalone lit test for {state.target} with a suggested_host "
        "comment. Start with list_pr_tests, read the PR tests, declare_test_style, "
        "then select_tool / record_analysis / run_candidate in that style, "
        "finalize_standalone(run=N) / accept."
    )


def usher_fallback_picker(state: UsherState):
    """Apply harness fallback acceptance onto *state*; return proposal or None."""
    return state.apply_fallback()
