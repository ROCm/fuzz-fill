"""
Create per-line reduce harness directories from incremental/new_coverage.csv.

See ``python -m reduce batch-from-coverage --help`` for usage.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from fuzz_fill.llvm_tools import ReduceTools, reduce_tools_from_args
from reduce.batch.candidate_test import parse_test_sh
from reduce.batch.coverage import load_new_coverage_rows, resolve_covered_hexes
from reduce.batch.pipeline import (
    build_pipeline_steps,
    parse_pipeline_arg,
    validate_pipeline_cli,
)
from reduce.batch.prepare import prepare_test_case
from reduce.batch.templates import mir_template_basename
from reduce.run_single import run_single_reduce


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_case_reduce(*, case_dir: Path, tools: ReduceTools) -> None:
    """Run reduce for one prepared case directory."""
    run_single_reduce(config=case_dir / "config.json", tools=tools)


@dataclass(frozen=True)
class BatchTemplateContext:
    interesting_ir: str
    interesting_mir: str | None
    mir_template_name: str | None


def _load_template_context_for_pipeline(
    template_dir: Path,
    pass_ids: list[str],
    *,
    mir_codegen_only: bool,
) -> BatchTemplateContext:
    interesting_ir = (template_dir / "interesting_ir.sh").read_text(encoding="utf-8")
    if "llvm_reduce_mir" not in pass_ids:
        return BatchTemplateContext(
            interesting_ir=interesting_ir,
            interesting_mir=None,
            mir_template_name=None,
        )
    mir_template_name = mir_template_basename(mir_codegen_only=mir_codegen_only)
    interesting_mir = (template_dir / mir_template_name).read_text(encoding="utf-8")
    return BatchTemplateContext(
        interesting_ir=interesting_ir,
        interesting_mir=interesting_mir,
        mir_template_name=mir_template_name,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, required=True, help="new_coverage.csv path.")
    p.add_argument(
        "--candidate-tests",
        type=Path,
        required=True,
        help="candidate_tests directory from gap filling.",
    )
    p.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory to create t-00001-xxxx subdirectories under.",
    )
    p.add_argument(
        "--template-dir",
        type=Path,
        default=_repo_root() / "example" / "amd" / "new-test-1",
        help="Directory containing interesting_ir.sh (coverage-based template).",
    )
    p.add_argument(
        "--pipeline",
        default="llvm_reduce_ir",
        metavar="PASS_IDS",
        help="Comma-separated reduce pass ids (default: llvm_reduce_ir).",
    )
    p.add_argument(
        "--with-creduce",
        action="store_true",
        help="Append creduce to --pipeline if not already present.",
    )
    p.add_argument(
        "--creduce-n",
        type=int,
        default=None,
        metavar="N",
        help="Pass creduce --n (parallelism) for creduce pipeline steps.",
    )
    p.add_argument("--pass-under-test", default=None, metavar="PASS")
    p.add_argument("--mtriple", default=None)
    p.add_argument("--mir-codegen-only", action="store_true")
    p.add_argument("--extract-mir-output", default=None, metavar="BASENAME")
    p.add_argument("--extract-ir-output", default=None, metavar="BASENAME")
    p.add_argument("--llc", type=Path, default=None)
    p.add_argument("--llvm-reduce", type=Path, default=None)
    p.add_argument("--llvm-dis", type=Path, default=None)
    p.add_argument(
        "--n",
        type=int,
        default=None,
        metavar="N",
        help="Process at most the first N CSV data rows (default: all rows).",
    )
    return p


def _resolve_tools(args: argparse.Namespace) -> ReduceTools | None:
    llc = args.llc.resolve() if args.llc is not None else None
    llvm_reduce = args.llvm_reduce.resolve() if args.llvm_reduce is not None else None
    llvm_dis = args.llvm_dis.resolve() if args.llvm_dis is not None else None
    if (llc is None) ^ (llvm_reduce is None):
        raise ValueError("Pass both --llc and --llvm-reduce to run reduce, or omit both.")
    if llc is None:
        return None
    return reduce_tools_from_args(llc=llc, llvm_reduce=llvm_reduce, llvm_dis=llvm_dis)


def _process_rows(
    rows: list[dict[str, str]],
    *,
    candidate_tests: Path,
    out_parent: Path,
    pass_ids: list[str],
    templates: BatchTemplateContext,
    tools: ReduceTools | None,
    llc: Path | None,
    llvm_reduce: Path | None,
    pass_under_test: str | None,
    mtriple: str | None,
    mir_codegen_only: bool,
    extract_mir_output: str | None,
    extract_ir_output: str | None,
    creduce_n: int | None,
) -> int:
    ok = 0
    ambiguous_rows = 0
    for i, row in enumerate(rows, start=1):
        try:
            line = int(row["line"])
        except ValueError:
            print(f"Row {i}: bad line {row['line']!r}", file=sys.stderr)
            continue
        try:
            covered, hexes_sorted = resolve_covered_hexes(row["covered-points"])
            test_info = parse_test_sh(candidate_tests / row["test_name"].strip() / "test.sh")
            row_pipeline = build_pipeline_steps(
                pass_ids,
                pass_under_test=pass_under_test,
                mtriple=mtriple,
                llc_flags=test_info.llc_flags,
                extract_mir_output=extract_mir_output,
                extract_ir_output=extract_ir_output,
                creduce_n=creduce_n,
            )
            amb, dest = prepare_test_case(
                row_index=i,
                test_name=row["test_name"].strip(),
                test_info=test_info,
                file_col=row["file"].strip(),
                line=line,
                covered=covered,
                hexes_sorted=hexes_sorted,
                out_parent=out_parent,
                template_interesting=templates.interesting_ir,
                pipeline_steps=row_pipeline,
                template_interesting_mir=templates.interesting_mir,
                mir_template_name=templates.mir_template_name,
                pass_under_test=pass_under_test,
                mtriple=mtriple,
                mir_codegen_only=mir_codegen_only,
            )
            if tools is not None:
                print(
                    f"Row {i}: running reduce (llc={llc}, llvm-reduce={llvm_reduce})...",
                    file=sys.stderr,
                    flush=True,
                )
                run_case_reduce(case_dir=dest, tools=tools)
            print(dest)
            ok += 1
            if amb:
                ambiguous_rows += 1
        except (OSError, ValueError, FileNotFoundError, SystemExit) as e:
            print(f"Row {i}: {e}", file=sys.stderr)

    _print_summary(ok, len(rows), ambiguous_rows)
    if ok == 0:
        return 1
    return 0 if ok == len(rows) else 1


def _print_summary(ok: int, total: int, ambiguous_rows: int) -> None:
    if ambiguous_rows:
        print(
            f"Summary: {ambiguous_rows} row(s) had multiple COVERED candidates on the same "
            "source line (lowest address was used; see messages above).",
            file=sys.stderr,
        )
    elif ok > 0:
        if ok == total:
            print(
                "Summary: every row matched to a unique COVERED address "
                "(one instrumentation site per file/source line).",
                file=sys.stderr,
            )
        else:
            print(
                f"Summary: each of the {ok} successful row(s) matched to a unique COVERED "
                "address (one instrumentation site per file/source line).",
                file=sys.stderr,
            )


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    if args.n is not None and args.n < 1:
        print("--n must be a positive integer.", file=sys.stderr)
        return 2
    if args.creduce_n is not None and args.creduce_n < 1:
        print("--creduce-n must be a positive integer.", file=sys.stderr)
        return 2

    try:
        tools = _resolve_tools(args)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    candidate_tests = args.candidate_tests.resolve()
    out_parent = args.output.resolve()
    out_parent.mkdir(parents=True, exist_ok=True)
    template_dir = args.template_dir.resolve()

    try:
        pass_ids = parse_pipeline_arg(args.pipeline)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    if args.with_creduce and "creduce" not in pass_ids:
        pass_ids.append("creduce")

    try:
        validate_pipeline_cli(
            pass_ids,
            pass_under_test=args.pass_under_test,
            mtriple=args.mtriple,
            template_dir=template_dir,
            mir_codegen_only=args.mir_codegen_only,
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    templates = _load_template_context_for_pipeline(
        template_dir,
        pass_ids,
        mir_codegen_only=args.mir_codegen_only,
    )

    try:
        rows = load_new_coverage_rows(args.csv, limit=args.n)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    llc = args.llc.resolve() if args.llc is not None else None
    llvm_reduce = args.llvm_reduce.resolve() if args.llvm_reduce is not None else None

    return _process_rows(
        rows,
        candidate_tests=candidate_tests,
        out_parent=out_parent,
        pass_ids=pass_ids,
        templates=templates,
        tools=tools,
        llc=llc,
        llvm_reduce=llvm_reduce,
        pass_under_test=args.pass_under_test,
        mtriple=args.mtriple,
        mir_codegen_only=args.mir_codegen_only,
        extract_mir_output=args.extract_mir_output,
        extract_ir_output=args.extract_ir_output,
        creduce_n=args.creduce_n,
    )
