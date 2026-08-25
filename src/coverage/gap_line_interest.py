# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Heuristics for skipping uncovered lines that are ambiguous or low-interest gap-fill targets.

Gap-fill works best on concrete executable statements. Some uncovered lines are still
reachable, but make poor targets because coverage on that line is hard to interpret or
not worth pursuing—for example debug logging, bare control-flow keywords, or structural
declarations whose execution does not clearly relate to PR logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DEBUG_RE = re.compile(
    r"\b("
    r"dbgs\s*\("
    r"|LLVM_DEBUG\s*\("
    r"|DEBUG_WITH_TYPE\s*\("
    r"|errs\s*\(\)"
    r")",
    re.IGNORECASE,
)
ASSERT_RE = re.compile(r"\bassert\s*\(", re.IGNORECASE)
CONTROL_FLOW_RE = re.compile(
    r"^\s*(?:}?\s*)?(?:else\s+)?(?:if|while|for)\s*\(",
    re.IGNORECASE,
)
RETURN_RE = re.compile(r"^\s*return\b", re.IGNORECASE)
CLASS_DEF_RE = re.compile(
    r"^\s*(?:template\s*<[^>]*>\s*)?"
    r"(?:class|struct|union|enum(?:\s+class)?)\s+\w+",
    re.IGNORECASE,
)
FUNC_DEF_RE = re.compile(
    r"""
    ^\s*
    (?:
        (?:static|virtual|explicit|inline|constexpr|consteval|friend)\s+
    )*
    (?:
        auto\s+\w+\s*=\s*\[
        |
        (?:[\w:<>*&]+\s+)+\w+\s*\(
        |
        ~?[A-Z]\w*\s*\(
        |
        operator\b
    )
    [^;]*
    \)\s*
    (?:const\s*)?
    (?:override\s*)?
    (?:final\s*)?
    (?:noexcept(?:\s*\([^)]*\))?\s*)?
    \{
    """,
    re.VERBOSE,
)
FUNC_DEF_WRAP_RE = re.compile(
    r"\)\s*(?:const|override|final)\s*\{",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GapLineInterestDecision:
    include: bool
    reason: str = ""


def classify_gap_line_interest(text: str) -> GapLineInterestDecision:
    """Return whether an uncovered line is an interesting gap-fill target."""
    stripped = (text or "").strip()
    if not stripped:
        return GapLineInterestDecision(True, "")
    if DEBUG_RE.search(stripped):
        return GapLineInterestDecision(False, "debug")
    if ASSERT_RE.search(stripped):
        return GapLineInterestDecision(False, "assert")
    if CONTROL_FLOW_RE.search(stripped):
        return GapLineInterestDecision(False, "control_flow")
    if RETURN_RE.search(stripped):
        return GapLineInterestDecision(False, "return")
    if CLASS_DEF_RE.search(stripped):
        return GapLineInterestDecision(False, "class_def")
    if FUNC_DEF_RE.search(stripped) or FUNC_DEF_WRAP_RE.search(stripped):
        return GapLineInterestDecision(False, "function_def")
    return GapLineInterestDecision(True, "")
