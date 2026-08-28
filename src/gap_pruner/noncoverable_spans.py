from __future__ import annotations

import bisect
import re
from pathlib import Path

# An identifier followed by a balanced "(...)" prunes every line that construct
# spans. Two kinds qualify, for the same reason: neither is a meaningful place
# to ask "did a test reach this?". Add more names as needed.
NONCOVERABLE_NAMES = frozenset(
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
        # control flow: the branch decision, not the branch body
        "if",
        "while",
        "for",
    }
)

_MEMBER_ACCESS = frozenset({".", "->"})

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


def find_noncoverable_lines(source_file: Path) -> set[int]:
    """Line numbers in ``source_file`` that are not meaningful coverage
    targets: blank, a standalone '{' or '}', or part of a NONCOVERABLE_NAMES
    construct, whether that construct spans one line or many.

    Everything is read straight off ``source_file`` -- never off a CSV's own
    ``text`` column, which may be stale, absent, or simply not trusted -- so
    the file is the one source of truth for what a line actually is.

    The test is purely lexical: a macro (``assert``), an ordinary call
    (``report_fatal_error``) and a keyword (``if``) all read as an identifier
    followed by a balanced ``(...)``, so one pass over the text covers all
    three and adding a name needs no other change. Qualified calls such as
    ``llvm::report_fatal_error(...)`` match; member calls such as
    ``obj.assert(...)`` deliberately do not.
    """
    text = source_file.read_text(encoding="utf-8")
    line_starts = [0, *(m.end() for m in re.finditer("\n", text))]

    pruned: set[int] = {
        i + 1 for i, line in enumerate(text.splitlines()) if line.strip() in ("", "{", "}")
    }
    prev = prev2 = ""
    prev_start = start = 0
    depth = 0
    for m in _TOKEN_RE.finditer(text):
        tok = m.group()
        if tok[0] == "/":
            continue  # only comments start with "/"; skip without losing history
        if not depth:
            if tok == "(" and prev in NONCOVERABLE_NAMES and prev2 not in _MEMBER_ACCESS:
                start, depth = prev_start, 1
        elif tok == "(":
            depth += 1
        elif tok == ")":
            depth -= 1
            if not depth:
                first = bisect.bisect_right(line_starts, start)
                last = bisect.bisect_right(line_starts, m.start())
                pruned.update(range(first, last + 1))
        prev2, prev, prev_start = prev, tok, m.start()
    return pruned
