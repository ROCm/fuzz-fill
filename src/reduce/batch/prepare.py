"""Scaffold one per-line reduction case directory."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from reduce.batch.candidate_test import TestShInfo, copy_input_bc
from reduce.batch.coverage import llvm_rel_source_path
from reduce.batch.templates import render_interesting_ir, render_interesting_mir


def prepare_test_case(
    *,
    row_index: int,
    test_name: str,
    test_info: TestShInfo,
    file_col: str,
    line: int,
    covered: str,
    hexes_sorted: list[str],
    out_parent: Path,
    template_interesting: str,
    pipeline_steps: list[dict],
    template_interesting_mir: str | None,
    mir_template_name: str | None,
    pass_under_test: str | None,
    mtriple: str | None,
    mir_codegen_only: bool,
) -> tuple[bool, Path]:
    """Create ``t-NNNNN-<short>/`` with config.json and interesting scripts."""
    short = Path(test_name).stem[:8] if test_name else f"r{row_index}"
    dest_dir = out_parent / f"t-{row_index:05d}-{short}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    if len(hexes_sorted) > 1:
        detail = ", ".join(f"0x{h}" for h in hexes_sorted)
        print(
            f"Row {row_index}: ambiguous COVERED - {len(hexes_sorted)} "
            f"addresses on source line {line}; using {covered}; all: {detail}",
            file=sys.stderr,
        )

    _write_case_files(
        dest_dir,
        test_info=test_info,
        file_col=file_col,
        line=line,
        covered=covered,
        pipeline_steps=pipeline_steps,
        template_interesting=template_interesting,
        template_interesting_mir=template_interesting_mir,
        mir_template_name=mir_template_name,
        pass_under_test=pass_under_test,
        mtriple=mtriple,
        mir_codegen_only=mir_codegen_only,
    )
    return len(hexes_sorted) > 1, dest_dir


def _write_case_files(
    dest_dir: Path,
    *,
    test_info: TestShInfo,
    file_col: str,
    line: int,
    covered: str,
    pipeline_steps: list[dict],
    template_interesting: str,
    template_interesting_mir: str | None,
    mir_template_name: str | None,
    pass_under_test: str | None,
    mtriple: str | None,
    mir_codegen_only: bool,
) -> None:
    input_name = copy_input_bc(test_info, dest_dir)
    reduced_dir = (dest_dir / "reduced").resolve()
    config = {
        "input": input_name,
        "file": llvm_rel_source_path(file_col),
        "line": line,
        "replacement": "",
        "output_dir": str(reduced_dir),
        "pipeline": pipeline_steps,
    }
    (dest_dir / "config.json").write_text(
        json.dumps(config, indent=4) + "\n", encoding="utf-8"
    )

    ir_script = dest_dir / "interesting_ir.sh"
    ir_script.write_text(
        render_interesting_ir(
            template_interesting,
            covered=covered,
            llvm_bin=test_info.llvm_bin,
            llc_flags=test_info.llc_flags,
        ),
        encoding="utf-8",
    )
    ir_script.chmod(0o755)

    if template_interesting_mir is None:
        return

    if pass_under_test is None or mtriple is None:
        raise ValueError(
            "pass_under_test and mtriple are required to generate interesting_mir.sh."
        )
    mir_script = dest_dir / "interesting_mir.sh"
    mir_script.write_text(
        render_interesting_mir(
            template_interesting_mir,
            template_name=mir_template_name or "interesting_mir.sh",
            covered=covered,
            llvm_bin=test_info.llvm_bin,
            mtriple=mtriple,
            mir_codegen_only=mir_codegen_only,
            llc_flags=test_info.llc_flags,
            pass_under_test=pass_under_test,
        ),
        encoding="utf-8",
    )
    mir_script.chmod(0o755)
