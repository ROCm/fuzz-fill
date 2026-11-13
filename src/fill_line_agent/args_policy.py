# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Validate agent-proposed opt/llc argv for fill-line runs."""

from __future__ import annotations

import re
from typing import Literal

ToolName = Literal["opt", "llc"]
InputFormat = Literal["ll", "mir"]

_FORBIDDEN_FLAGS = frozenset({
    "-load",
    "--load",
    "-load-pass-plugin",
    "--load-pass-plugin",
})
_SHELL_META = re.compile(r"[;&|`$<>]")
_PATHISH = re.compile(r"(/|\.\./|\.\\)")


def validate_argv(
    tool: ToolName,
    argv: list[str],
    fmt: InputFormat,
) -> list[str]:
    """Return cleaned argv or raise ``ValueError`` if the proposal is rejected."""
    if fmt == "mir" and tool == "opt":
        raise ValueError("opt does not accept MIR input; use llc or format=ll")
    if not isinstance(argv, list) or any(not isinstance(a, str) for a in argv):
        raise ValueError("args must be a list of strings")

    cleaned: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if not arg:
            raise ValueError("empty argument is not allowed")
        if _SHELL_META.search(arg):
            raise ValueError(f"shell metacharacters are not allowed: {arg!r}")
        if arg in ("-o", "--o") or arg.startswith("-o=") or arg.startswith("--o="):
            raise ValueError("do not pass -o; the harness supplies the output path")
        flag = arg.split("=", 1)[0]
        if flag in _FORBIDDEN_FLAGS:
            raise ValueError(f"flag is not allowed: {flag}")
        if flag.startswith("-load") or flag.startswith("--load"):
            raise ValueError(f"flag is not allowed: {flag}")
        # Reject absolute/relative path arguments that look like input files.
        if not arg.startswith("-") and _PATHISH.search(arg):
            raise ValueError(f"file path arguments are not allowed: {arg!r}")
        if arg.endswith((".ll", ".mir", ".bc", ".o", ".s")) and not arg.startswith("-"):
            raise ValueError(f"input/output file arguments are not allowed: {arg!r}")
        cleaned.append(arg)
        i += 1
    return cleaned
