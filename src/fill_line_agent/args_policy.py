# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Validate agent-proposed tool argv for fill-line runs."""

from __future__ import annotations

import re

from fill_line_agent.toolset import (
    InputFormat,
    ToolName,
    formats_for_tool,
    is_clang_tool,
)

_FORBIDDEN_FLAGS = frozenset({
    "-load",
    "--load",
    "-load-pass-plugin",
    "--load-pass-plugin",
})
_CLANG_FORBIDDEN = frozenset({
    "-fplugin",
    "-fplugin=",
    "-save-temps",
    "-fno-integrated-cc1",
})
# < and > are allowed: they appear in new-PM pass names (require<...>, default<O2>).
# Argv is never run through a shell (subprocess list form).
_SHELL_META = re.compile(r"[;&|`$]")
_PATHISH = re.compile(r"(/|\.\./|\.\\)")
_DRIVER_MODES = frozenset({"-c", "-S", "-E", "-fsyntax-only", "-###"})


def validate_argv(
    tool: ToolName,
    argv: list[str],
    fmt: InputFormat,
) -> list[str]:
    """Return cleaned argv or raise ``ValueError`` if the proposal is rejected.

    Host-file ``RUN`` lines trusted by usher should skip this helper and run as
    parsed. Model-invented argv still goes through here.
    """
    allowed = formats_for_tool(tool)
    if fmt not in allowed:
        raise ValueError(f"{tool} does not accept format={fmt}; allowed: {allowed}")
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
        if arg.startswith("@"):
            raise ValueError("response files (@args) are not allowed")
        flag = arg.split("=", 1)[0]
        if flag in _FORBIDDEN_FLAGS:
            raise ValueError(f"flag is not allowed: {flag}")
        if flag.startswith("-load") or flag.startswith("--load"):
            raise ValueError(f"flag is not allowed: {flag}")
        if is_clang_tool(tool):
            if flag.startswith("-fplugin") or flag in _CLANG_FORBIDDEN or arg in _CLANG_FORBIDDEN:
                raise ValueError(f"flag is not allowed: {arg}")
            if flag.startswith("-Xclang"):
                # Next arg (or -Xclang=value) must not sneak in -load / -fplugin.
                rest = arg.split("=", 1)[1] if "=" in arg else (
                    argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith("-") else ""
                )
                if rest.startswith("-load") or rest.startswith("-fplugin"):
                    raise ValueError(f"flag is not allowed via -Xclang: {rest}")
            if flag in ("-I", "-include", "-isystem", "-iquote") or arg.startswith(
                ("-I/", "-I./", "-I../", "-include/", "-isystem/")
            ):
                # Path-like include dirs are rejected; bare -I without path is rare.
                if flag in ("-I", "-include", "-isystem", "-iquote"):
                    if i + 1 < len(argv) and _PATHISH.search(argv[i + 1]):
                        raise ValueError(
                            f"path-like include arguments are not allowed: {argv[i + 1]!r}"
                        )
                elif _PATHISH.search(arg):
                    raise ValueError(f"path-like include arguments are not allowed: {arg!r}")
        # Reject absolute/relative path arguments that look like input files.
        if not arg.startswith("-") and _PATHISH.search(arg):
            raise ValueError(f"file path arguments are not allowed: {arg!r}")
        if arg.endswith(
            (".ll", ".mir", ".bc", ".o", ".s", ".c", ".cpp", ".cc", ".cxx", ".hip", ".cl")
        ) and not arg.startswith("-"):
            raise ValueError(f"input/output file arguments are not allowed: {arg!r}")
        cleaned.append(arg)
        i += 1

    if tool in ("clang", "clangxx"):
        if not any(
            a in _DRIVER_MODES or a.startswith("-emit-") for a in cleaned
        ):
            raise ValueError(
                "driver mode must include one of -c, -S, -E, -fsyntax-only, or -### "
                "(no linking)"
            )
    if tool == "clang_cc1" and not any(
        a == "-triple" or a.startswith("-triple=") for a in cleaned
    ):
        raise ValueError("clang_cc1 requires -triple")

    return cleaned
