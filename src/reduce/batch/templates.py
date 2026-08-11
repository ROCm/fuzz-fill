"""Render interesting_ir.sh and interesting_mir.sh from example templates."""

from __future__ import annotations

import re
from pathlib import Path


def _substitute_once(
    text: str,
    *,
    pattern: str,
    repl: str | re.Pattern[str],
    template_name: str,
    label: str,
) -> str:
    out, count = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(
            f'Template {template_name} must contain exactly one {label} line.'
        )
    return out


def _apply_llvm_bin_and_covered(
    template_text: str,
    *,
    template_name: str,
    covered: str,
    llvm_bin: Path,
) -> str:
    out = _substitute_once(
        template_text,
        pattern=r"^LLVM_BIN=.*$",
        repl=f"LLVM_BIN={llvm_bin}",
        template_name=template_name,
        label="LLVM_BIN=...",
    )
    return _substitute_once(
        out,
        pattern=r'^COVERED="[^"]*"',
        repl=f'COVERED="{covered}"',
        template_name=template_name,
        label='COVERED="..."',
    )


def _apply_llc_flags(
    out: str,
    *,
    template_name: str,
    llc_flags: tuple[str, ...],
    llc_invocation_pattern: str,
    llc_invocation_repl: str,
) -> str:
    flags_value = " ".join(llc_flags)
    if re.search(r"^LLC_FLAGS=", out, flags=re.MULTILINE):
        out = _substitute_once(
            out,
            pattern=r"^LLC_FLAGS=.*$",
            repl=f'LLC_FLAGS="{flags_value}"',
            template_name=template_name,
            label="LLC_FLAGS=...",
        )
    else:
        out = _substitute_once(
            out,
            pattern=r"^(LLC=\$LLVM_BIN/llc)$",
            repl=rf'\1\nLLC_FLAGS="{flags_value}"',
            template_name=template_name,
            label="LLC=$LLVM_BIN/llc or LLC_FLAGS=...",
        )
    out, count = re.subn(
        llc_invocation_pattern,
        llc_invocation_repl,
        out,
        count=1,
    )
    if count != 1:
        raise ValueError(
            f"Template {template_name} must match llc invocation pattern "
            f"{llc_invocation_pattern!r}."
        )
    return out


def mir_template_basename(*, mir_codegen_only: bool) -> str:
    return "interesting_mir_codegen.sh" if mir_codegen_only else "interesting_mir.sh"


def render_interesting_ir(
    template_text: str,
    *,
    covered: str,
    llvm_bin: Path,
    llc_flags: tuple[str, ...],
) -> str:
    template_name = "interesting_ir.sh"
    out = _apply_llvm_bin_and_covered(
        template_text,
        template_name=template_name,
        covered=covered,
        llvm_bin=llvm_bin,
    )
    return _apply_llc_flags(
        out,
        template_name=template_name,
        llc_flags=llc_flags,
        llc_invocation_pattern=r'(\$LLC)\s+"\$1"',
        llc_invocation_repl=r'\1 $LLC_FLAGS "$1"',
    )


def render_interesting_mir(
    template_text: str,
    *,
    template_name: str,
    covered: str,
    llvm_bin: Path,
    mtriple: str,
    mir_codegen_only: bool,
    llc_flags: tuple[str, ...],
    pass_under_test: str | None,
) -> str:
    out = _apply_llvm_bin_and_covered(
        template_text,
        template_name=template_name,
        covered=covered,
        llvm_bin=llvm_bin,
    )
    out = _substitute_once(
        out,
        pattern=r'-mtriple=[^\s"]+',
        repl=f"-mtriple={mtriple}",
        template_name=template_name,
        label="-mtriple=<triple>",
    )

    if mir_codegen_only:
        return _apply_llc_flags(
            out,
            template_name=template_name,
            llc_flags=llc_flags,
            llc_invocation_pattern=r"(\$LLC)\s+(\$LLC_FLAGS\s+)?",
            llc_invocation_repl=r"\1 $LLC_FLAGS ",
        )

    if pass_under_test is None:
        raise ValueError("pass_under_test is required for machine-pass interesting_mir.sh.")
    return _substitute_once(
        out,
        pattern=r'-run-pass=[^\s"]+',
        repl=f"-run-pass={pass_under_test}",
        template_name=template_name,
        label="-run-pass=<pass>",
    )
