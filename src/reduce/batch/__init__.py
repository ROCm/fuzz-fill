"""Batch reduction from gap-fill ``new_coverage.csv`` output."""

from reduce.batch.candidate_test import TestShInfo, copy_input_bc, parse_test_sh
from reduce.batch.coverage import (
    load_new_coverage_rows,
    llvm_rel_source_path,
    parse_covered_points_field,
    resolve_covered_hexes,
)
from reduce.batch.pipeline import (
    build_pipeline_steps,
    parse_pipeline_arg,
    validate_pipeline_cli,
)
from reduce.batch.prepare import prepare_test_case
from reduce.batch.templates import (
    mir_template_basename,
    render_interesting_ir,
    render_interesting_mir,
)

__all__ = [
    "TestShInfo",
    "build_pipeline_steps",
    "copy_input_bc",
    "load_new_coverage_rows",
    "llvm_rel_source_path",
    "parse_covered_points_field",
    "parse_pipeline_arg",
    "parse_test_sh",
    "prepare_test_case",
    "render_interesting_ir",
    "render_interesting_mir",
    "resolve_covered_hexes",
    "validate_pipeline_cli",
]
