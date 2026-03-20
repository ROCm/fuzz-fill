import argparse
from datetime import datetime
from pathlib import Path

from reduce.config import load_reduce_config
from reduce.reducer import Reducer
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
        help="Path to config.json (map of original_test path -> file, line, interesting, ...).",
    )
    parser.add_argument(
        "--llvm-bin",
        type=Path,
        required=True,
        help="Path to llvm-project bin directory (overrides \"llvm_bin\" in config if set).",
    )
    parser.add_argument(
        "--engine",
        choices=("llvmreduce-ir", "llvm-reduce-mir"),
        default="llvmreduce-ir",
        help="Reduction backend (default: %(default)s).",
    )
    ns = parser.parse_args()
    cfg = load_reduce_config(ns.config, llvm_bin_cli=ns.llvm_bin.resolve())

    t = cfg.test
    test = Test(t.original_test, t.interesting, f"/{t.file}", t.line)

    current_file = Path(__file__).resolve()
    default_output_dir = (
        current_file.parent.parent.parent
        / "data"
        / "output"
        / t.original_test.name
        / datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    output_dir = cfg.output_dir or default_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if cfg.action == "test":
        test.run()

    if cfg.action == "reduce":
        reducer = Reducer(cfg.llvm_bin, output_dir, test, engine=ns.engine)
        reducer.reduce()

if __name__ == "__main__":
    main()
