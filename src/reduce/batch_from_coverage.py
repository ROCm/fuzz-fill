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
from reduce.batch.gap_fill import clear_output_dir, resolve_batch_inputs
from reduce.batch.pipeline import (
    build_pipeline_steps,
    parse_pipeline_arg,
    validate_pipeline_cli,
)
from reduce.batch.prepare import prepare_test_case
from reduce.batch.templates import mir_template_basename
from reduce.run_single import run_single_reduce


def _default_ir_template() -> Path:
    return Path(__file__).resolve().parent / "template_interesting_ir.sh"


def run_case_reduce(*, case_dir: Path, tools: ReduceTools) -> None:
    """Run reduce for one prepared case directory."""
    run_single_reduce(config=case_dir / "config.json", tools=tools)


@dataclass(frozen=True)
class BatchTemplateContext:
    interesting_ir: str
    interesting_mir: str | None
    mir_template_name: str | None


def _load_template_context_for_pipeline(
    ir_template: Path,
    mir_template_dir: Path | None,
    pass_ids: list[str],
    *,
    mir_codegen_only: bool,
) -> BatchTemplateContext:
    interesting_ir = ir_template.read_text(encoding="utf-8")
    if "llvm_reduce_mir" not in pass_ids:
        return BatchTemplateContext(
            interesting_ir=interesting_ir,
            interesting_mir=None,
            mir_template_name=None,
        )
    if mir_template_dir is None:
        raise ValueError(
            "--mir-template-dir is required when the pipeline includes llvm_reduce_mir."
        )
    mir_template_name = mir_template_basename(mir_codegen_only=mir_codegen_only)
    interesting_mir = (mir_template_dir / mir_template_name).read_text(encoding="utf-8")
    return BatchTemplateContext(
        interesting_ir=interesting_ir,
        interesting_mir=interesting_mir,
        mir_template_name=mir_template_name,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--gap-fill-dir",
        type=Path,
        required=True,
        help="Gap-fill output directory (incremental/new_coverage.csv, candidate_tests/).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Case output directory (default: <gap-fill-dir>/reduced/).",
    )
    p.add_argument(
        "-n",
        "--n",
        type=int,
        required=True,
        metavar="N",
        help="Process the first N CSV data rows.",
    )
    p.add_argument(
        "--scaffold-only",
        action="store_true",
        help="Create case directories only; do not run llvm-reduce.",
    )
    p.add_argument(
        "--corpus-dir",
        type=Path,
        default=None,
        help="Fuzz corpus root from gap filling (resolves .ll/.bc paths from test.sh).",
    )
    p.add_argument(
        "--ir-template",
        type=Path,
        default=None,
        help="IR interestingness template (default: src/reduce/template_interesting_ir.sh).",
    )
    p.add_argument(
        "--mir-template-dir",
        type=Path,
        default=None,
        help="Directory with interesting_mir.sh templates (required for llvm_reduce_mir).",
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
    p.add_argument(
        "--llvm-bin",
        type=Path,
        default=None,
        help="LLVM bin directory with llvm-reduce and llvm-dis (non-sancov build).",
    )
    p.add_argument(
        "--instrumented-bin-dir",
        type=Path,
        default=None,
        help="SanitizerCoverage LLVM bin directory with llc.",
    )
    p.add_argument("--llc", type=Path, default=None, help="Path to llc (overrides --instrumented-bin-dir).")
    p.add_argument(
        "--llvm-reduce",
        type=Path,
        default=None,
        help="Path to llvm-reduce (overrides --llvm-bin).",
    )
    p.add_argument(
        "--llvm-dis",
        type=Path,
        default=None,
        help="Path to llvm-dis (overrides --llvm-bin).",
    )
    return p


def _resolve_tool_paths(args: argparse.Namespace) -> tuple[Path | None, Path | None, Path | None]:
    llc = args.llc.expanduser().resolve() if args.llc is not None else None
    llvm_reduce = args.llvm_reduce.expanduser().resolve() if args.llvm_reduce is not None else None
    llvm_dis = args.llvm_dis.expanduser().resolve() if args.llvm_dis is not None else None
    llvm_bin = args.llvm_bin.expanduser().resolve() if args.llvm_bin is not None else None
    instrumented_bin_dir = (
        args.instrumented_bin_dir.expanduser().resolve()
        if args.instrumented_bin_dir is not None
        else None
    )

    has_explicit_tools = llc is not None or llvm_reduce is not None or llvm_dis is not None
    has_bin_dirs = llvm_bin is not None or instrumented_bin_dir is not None

    if has_explicit_tools and has_bin_dirs:
        raise ValueError(
            "Pass either --llvm-bin/--instrumented-bin-dir or --llc/--llvm-reduce/--llvm-dis, "
            "not both."
        )
    if (llvm_bin is None) ^ (instrumented_bin_dir is None):
        if has_bin_dirs:
            raise ValueError("Pass both --llvm-bin and --instrumented-bin-dir.")

    if llvm_bin is not None and instrumented_bin_dir is not None:
        llc = instrumented_bin_dir / "llc"
        llvm_reduce = llvm_bin / "llvm-reduce"
        if llvm_dis is None:
            llvm_dis = llvm_bin / "llvm-dis"

    if (llc is None) ^ (llvm_reduce is None):
        raise ValueError(
            "Pass both --llc and --llvm-reduce, or both --llvm-bin and --instrumented-bin-dir."
        )

    return llc, llvm_reduce, llvm_dis


def _resolve_tools(args: argparse.Namespace) -> ReduceTools | None:
    if args.scaffold_only:
        if (
            args.llc is not None
            or args.llvm_reduce is not None
            or args.llvm_dis is not None
            or args.llvm_bin is not None
            or args.instrumented_bin_dir is not None
        ):
            raise ValueError(
                "--scaffold-only cannot be combined with LLVM tool path options."
            )
        return None

    llc, llvm_reduce, llvm_dis = _resolve_tool_paths(args)
    try:
        return reduce_tools_from_args(llc=llc, llvm_reduce=llvm_reduce, llvm_dis=llvm_dis)
    except SystemExit as exc:
        raise ValueError(str(exc)) from exc


def _process_rows(
    rows: list[dict[str, str]],
    *,
    candidate_tests: Path,
    corpus_dir: Path | None,
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
            test_name = row["test_name"].strip()
            test_info = parse_test_sh(
                candidate_tests / test_name / "test.sh",
                test_name=test_name,
                corpus_dir=corpus_dir,
            )
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
                test_name=test_name,
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

    if args.n < 1:
        print("--n must be a positive integer.", file=sys.stderr)
        return 2
    if args.creduce_n is not None and args.creduce_n < 1:
        print("--creduce-n must be a positive integer.", file=sys.stderr)
        return 2

    try:
        csv_path, candidate_tests, out_parent = resolve_batch_inputs(
            gap_fill_dir=args.gap_fill_dir,
            output=args.output,
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    corpus_dir = args.corpus_dir.expanduser().resolve() if args.corpus_dir is not None else None
    if corpus_dir is not None and not corpus_dir.is_dir():
        print(f"--corpus-dir is not a directory: {corpus_dir}", file=sys.stderr)
        return 2

    ir_template = (
        args.ir_template.expanduser().resolve()
        if args.ir_template is not None
        else _default_ir_template()
    )
    if not ir_template.is_file():
        print(f"--ir-template must be an existing file: {ir_template}", file=sys.stderr)
        return 2

    mir_template_dir = (
        args.mir_template_dir.expanduser().resolve()
        if args.mir_template_dir is not None
        else None
    )

    try:
        tools = _resolve_tools(args)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

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
            ir_template=ir_template,
            mir_template_dir=mir_template_dir,
            mir_codegen_only=args.mir_codegen_only,
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    templates = _load_template_context_for_pipeline(
        ir_template,
        mir_template_dir,
        pass_ids,
        mir_codegen_only=args.mir_codegen_only,
    )

    try:
        rows = load_new_coverage_rows(csv_path, limit=args.n)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    clear_output_dir(out_parent)

    llc_path, llvm_reduce_path, _ = _resolve_tool_paths(args)
    if tools is not None:
        llc_path = tools.llc
        llvm_reduce_path = tools.llvm_reduce

    return _process_rows(
        rows,
        candidate_tests=candidate_tests,
        corpus_dir=corpus_dir,
        out_parent=out_parent,
        pass_ids=pass_ids,
        templates=templates,
        tools=tools,
        llc=llc_path,
        llvm_reduce=llvm_reduce_path,
        pass_under_test=args.pass_under_test,
        mtriple=args.mtriple,
        mir_codegen_only=args.mir_codegen_only,
        extract_mir_output=args.extract_mir_output,
        extract_ir_output=args.extract_ir_output,
        creduce_n=args.creduce_n,
    )
