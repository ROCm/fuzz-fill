import argparse
import sys
from pathlib import Path

from fuzz_fill.env import FUZZ_FILL_LLC, FUZZ_FILL_LLVM_DIS, FUZZ_FILL_LLVM_REDUCE
from fuzz_fill.llvm_tools import reduce_tools_from_args
from fuzz_fill.log import (
    add_log_level_argument,
    add_log_to_file_argument,
    configure_logging,
)
from reduce import batch_from_coverage
from reduce.reducer import known_pass_ids
from reduce.run_single import run_single_reduce


def _run_single_from_args(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Reduce tests using a JSON config (see example/config.json)."
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        required=True,
        help='Path to config.json (includes "pipeline": pass ids, plus input/file/line, ...).',
    )
    parser.add_argument(
        "--llc",
        type=Path,
        default=None,
        help=f"Path to the llc executable (or set {FUZZ_FILL_LLC}).",
    )
    parser.add_argument(
        "--llvm-reduce",
        type=Path,
        default=None,
        help=f"Path to the llvm-reduce executable (or set {FUZZ_FILL_LLVM_REDUCE}).",
    )
    parser.add_argument(
        "--llvm-dis",
        type=Path,
        default=None,
        help=(
            f"Path to the llvm-dis executable (or set {FUZZ_FILL_LLVM_DIS}); "
            "required when reducing .bc input with llvm_reduce_ir."
        ),
    )
    parser.add_argument(
        "--only-pass",
        default=argparse.SUPPRESS,
        choices=sorted(known_pass_ids()),
        metavar="PASS_ID",
        help="Run a single pass by id (input is config input; use .mir for llvm_reduce_mir).",
    )
    add_log_level_argument(parser)
    add_log_to_file_argument(parser)
    ns = parser.parse_args(argv)
    configure_logging(ns.log_level)
    tools = reduce_tools_from_args(
        llc=ns.llc,
        llvm_reduce=ns.llvm_reduce,
        llvm_dis=ns.llvm_dis,
    )
    run_single_reduce(
        config=ns.config,
        tools=tools,
        only_pass=getattr(ns, "only_pass", None),
        log_level=ns.log_level,
        log_to_file=ns.log_to_file,
    )


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "batch-from-coverage":
        raise SystemExit(batch_from_coverage.main(sys.argv[2:]))
    _run_single_from_args()


if __name__ == "__main__":
    main()
