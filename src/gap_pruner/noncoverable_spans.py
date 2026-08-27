from __future__ import annotations

import bisect
import re
from pathlib import Path

# Calls to these names get pruned, whether they span one line or many. These
# are all either never executed, compiled out of a release build, or an abort
# path, so they are not meaningful coverage targets. Add more names as needed.
NONCOVERABLE_CALL_NAMES = frozenset(
    {
        # never executed / compile-time only
        "assert",
        "static_assert",
        "llvm_unreachable",
        "llvm_unreachable_internal",
        # debug-only, compiled out unless NDEBUG is off and -debug is passed
        "LLVM_DEBUG",
        "DEBUG_WITH_TYPE",
        # fatal, terminating
        "report_fatal_error",
        "reportFatalUsageError",
        "reportFatalInternalError",
        "PrintFatalError",
    }
)

_MEMBER_ACCESS = frozenset({".", "->"})

# A multi-line if/else-if/while/for header spans several lines for the same
# reason a multi-line call does: the condition is one logical unit, not
# separately meaningful per line. Unlike NONCOVERABLE_CALL_NAMES, single-line
# headers are ordinary, coverable code and stay untouched.
_CONTROL_KEYWORDS = frozenset({"if", "while", "for"})

# Comments and literals come first so that a "//" inside a string, or a quote
# inside a comment, is never mistaken for code. Anything not listed here (";",
# "::", whitespace, ...) is simply skipped by finditer.
_TOKEN_RE = re.compile(
    r"""  //[^\n]*                                     # line comment
        | /\*.*?\*/                                    # block comment
        | R"(?P<raw>[^ ()\\]{0,16})\(.*?\)(?P=raw)"    # raw string literal
        | "(?:[^"\\\n]|\\.)*"                          # string literal
        | '(?:[^'\\\n]|\\.)*'                          # character literal
        | \w+                                          # identifier or number
        | ->                                           # member access, pointer
        | [.()]                                        # member access, parens
    """,
    re.S | re.X,
)


def find_noncoverable_lines(
    source_file: Path, names: frozenset[str] = NONCOVERABLE_CALL_NAMES
) -> set[int]:
    """Line numbers that are not meaningful coverage targets: a call to one of
    ``names`` (single- or multi-line), a multi-line if/else-if/while/for
    header, a blank line, or a line that is just a standalone '{' or '}'.

    Everything is read straight off ``source_file`` -- never off a CSV's own
    ``text`` column, which may be stale, absent, or simply not trusted -- so
    the file is the one source of truth for what a line actually is.

    The call/header test is purely lexical: a macro call (``assert``) and an
    ordinary function call (``report_fatal_error``) both read as an
    identifier followed by a balanced ``(...)``, so one pass over the text
    covers both and adding a name to ``names`` needs no other change.
    Qualified calls such as ``llvm::report_fatal_error(...)`` match; member
    calls such as ``obj.assert(...)`` deliberately do not. Control-flow
    headers are found the same way, keyed on a fixed keyword set instead of
    ``names``.
    """
    text = source_file.read_text(encoding="utf-8")
    line_starts = [0, *(m.end() for m in re.finditer("\n", text))]

    pruned: set[int] = {
        i + 1 for i, line in enumerate(text.splitlines()) if line.strip() in ("", "{", "}")
    }
    prev = prev2 = ""
    prev_start = call_start = 0
    depth = 0
    is_call = False
    for m in _TOKEN_RE.finditer(text):
        tok = m.group()
        if tok[0] == "/":
            continue  # only comments start with "/"; skip without losing history
        if not depth:
            if tok == "(" and prev2 not in _MEMBER_ACCESS:
                if prev in names:
                    call_start, depth, is_call = prev_start, 1, True
                elif prev in _CONTROL_KEYWORDS:
                    call_start, depth, is_call = prev_start, 1, False
        elif tok == "(":
            depth += 1
        elif tok == ")":
            depth -= 1
            if not depth:
                first = bisect.bisect_right(line_starts, call_start)
                last = bisect.bisect_right(line_starts, m.start())
                if is_call or last > first:
                    pruned.update(range(first, last + 1))
        prev2, prev, prev_start = prev, tok, m.start()
    return pruned
