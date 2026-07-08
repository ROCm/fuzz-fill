import argparse
from datetime import datetime
from pathlib import Path

from fuzz_fill.env import FUZZ_FILL_LLC, FUZZ_FILL_LLVM_DIS, FUZZ_FILL_LLVM_REDUCE
from fuzz_fill.llvm_tools import reduce_tools_from_args
from fuzz_fill.log import (
    add_log_level_argument,
    add_log_to_file_argument,
    configure_logging,
    disable_log_file,
    enable_log_file,
)
from reduce.config import load_reduce_config, pipeline_steps_for_only_pass
from reduce.reducer import Reducer, known_pass_ids
from reduce.test import Test


def main():
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
    ns = parser.parse_args()
    configure_logging(ns.log_level)
    tools = reduce_tools_from_args(
        llc=ns.llc,
        llvm_reduce=ns.llvm_reduce,
        llvm_dis=ns.llvm_dis,
    )
    print("[main] loading config...", flush=True)
    cfg = load_reduce_config(ns.config)

    if getattr(ns, "only_pass", None) is not None:
        pipeline_steps = pipeline_steps_for_only_pass(cfg.pipeline, ns.only_pass)
    else:
        pipeline_steps = cfg.pipeline

    test = Test(cfg.original_test, None, f"/{cfg.file}", cfg.line)

    current_file = Path(__file__).resolve()
    default_output_dir = (
        current_file.parent.parent.parent
        / "data"
        / "output"
        / cfg.original_test.name
        / datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    output_dir = cfg.output_dir or default_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if ns.log_to_file:
        try:
            enable_log_file(output_dir)
            configure_logging(ns.log_level)
            print("[main] loading config...", flush=True)

            pass_ids = [s.id for s in pipeline_steps]
            print(
                f"[main] reduce ({len(pass_ids)} pass(es): {', '.join(pass_ids)})",
                flush=True,
            )
            reducer = Reducer(
                cfg.llvm_bin,
                output_dir,
                test,
                pipeline_steps=pipeline_steps,
            )   
            reducer.reduce()

        finally:
            if ns.log_to_file:
                disable_log_file()


if __name__ == "__main__":
    main()
