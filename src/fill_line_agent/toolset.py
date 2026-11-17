# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Shared tool / input-format registry for fill-line and usher-test."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ToolName = Literal["opt", "llc", "clang_cc1", "clang", "clangxx"]
InputFormat = Literal["ll", "mir", "c", "cpp", "hip", "cl"]
BinaryKey = Literal["opt", "llc", "clang", "clang++"]

TOOL_NAMES: tuple[ToolName, ...] = (
    "opt",
    "llc",
    "clang_cc1",
    "clang",
    "clangxx",
)
CLANG_TOOLS: frozenset[ToolName] = frozenset({"clang_cc1", "clang", "clangxx"})
LLVM_TOOLS: frozenset[ToolName] = frozenset({"opt", "llc"})
SOURCE_FORMATS: frozenset[InputFormat] = frozenset({"c", "cpp", "hip", "cl"})
IR_FORMATS: frozenset[InputFormat] = frozenset({"ll", "mir"})


@dataclass(frozen=True)
class ToolSpec:
    """One agent-selectable tool and how it maps to binaries / lit / formats."""

    name: ToolName
    binary: BinaryKey
    """Key under the instrumented bin dir (``clang`` or ``clang++``)."""

    lit_token: str
    """Token written on RUN lines (``opt`` or ``%clang_cc1``)."""

    formats: tuple[InputFormat, ...]
    comment_prefix: str
    """Line-comment prefix for rendered tests (``;``, ``#``, or ``//``)."""


TOOL_SPECS: dict[ToolName, ToolSpec] = {
    "opt": ToolSpec(
        name="opt",
        binary="opt",
        lit_token="opt",
        formats=("ll",),
        comment_prefix=";",
    ),
    "llc": ToolSpec(
        name="llc",
        binary="llc",
        lit_token="llc",
        formats=("ll", "mir"),
        comment_prefix=";",
    ),
    "clang_cc1": ToolSpec(
        name="clang_cc1",
        binary="clang",
        lit_token="%clang_cc1",
        formats=("c", "cpp", "hip", "cl"),
        comment_prefix="//",
    ),
    "clang": ToolSpec(
        name="clang",
        binary="clang",
        lit_token="%clang",
        formats=("c", "cpp", "hip", "cl"),
        comment_prefix="//",
    ),
    "clangxx": ToolSpec(
        name="clangxx",
        binary="clang++",
        lit_token="%clangxx",
        formats=("c", "cpp", "hip", "cl"),
        comment_prefix="//",
    ),
}

LIT_TOKEN_TO_TOOL: dict[str, ToolName] = {
    spec.lit_token: name for name, spec in TOOL_SPECS.items()
}
# Bare names also appear in older / fill-line IR tests.
LIT_TOKEN_TO_TOOL["opt"] = "opt"
LIT_TOKEN_TO_TOOL["llc"] = "llc"

FORMAT_COMMENT: dict[InputFormat, str] = {
    "ll": ";",
    "mir": "#",
    "c": "//",
    "cpp": "//",
    "hip": "//",
    "cl": "//",
}

FORMAT_SUFFIX: dict[InputFormat, str] = {
    "ll": "ll",
    "mir": "mir",
    "c": "c",
    "cpp": "cpp",
    "hip": "hip",
    "cl": "cl",
}


def is_clang_tool(tool: str) -> bool:
    return tool in CLANG_TOOLS


def is_source_format(fmt: str) -> bool:
    return fmt in SOURCE_FORMATS


def formats_for_tool(tool: ToolName) -> tuple[InputFormat, ...]:
    return TOOL_SPECS[tool].formats


def comment_prefix_for(fmt: str, tool: ToolName | None = None) -> str:
    if fmt in FORMAT_COMMENT:
        return FORMAT_COMMENT[fmt]  # type: ignore[index]
    if tool is not None:
        return TOOL_SPECS[tool].comment_prefix
    return ";"


def lit_token_for(tool: ToolName) -> str:
    return TOOL_SPECS[tool].lit_token


def tool_from_lit_token(token: str) -> ToolName | None:
    return LIT_TOKEN_TO_TOOL.get(token)


def target_area_for_path(rel_path: str) -> Literal["clang", "llvm", "other"]:
    norm = rel_path.replace("\\", "/")
    if norm.startswith("clang/"):
        return "clang"
    if norm.startswith("llvm/"):
        return "llvm"
    return "other"


def allowed_source_formats(
    *,
    rel_path: str,
    diff_text: str = "",
) -> list[InputFormat]:
    """Language gate for source inputs: C/C++ by default; HIP/OpenCL when warranted."""
    blob = f"{rel_path}\n{diff_text}".lower()
    out: list[InputFormat] = ["c", "cpp"]
    hip_markers = ("hip", "cuda", "__global__", "hipcc", "clang/lib/codegentrcuda")
    if any(m in blob for m in hip_markers):
        out.append("hip")
    cl_markers = ("opencl", ".cl", "cl_khr", "clang/lib/semaopencl", "codegtenopencl")
    if any(m in blob for m in cl_markers):
        out.append("cl")
    return out
