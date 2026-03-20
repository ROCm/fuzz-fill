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
        "config",
        type=Path,
        help="Path to config.json (map of original_test path -> file, line, interesting, ...).",
    )
    parser.add_argument(
        "llvm_bin",
        type=Path,
        nargs="?",
        default=None,
        help="Path to llvm-project bin directory (optional if config sets \"llvm_bin\").",
    )
    ns = parser.parse_args()
    cfg = load_reduce_config(ns.config, llvm_bin_cli=ns.llvm_bin)

    current_file = Path(__file__).resolve()
    default_output_dir = (
        current_file.parent.parent
        / "data"
        / "output"
        / datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    output_dir = cfg.output_dir or default_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    t = cfg.test
    test = Test(t.original_test, t.interesting, f"/{t.file}", t.line)

    if cfg.action == "test":
        test.run()

    if cfg.action == "reduce":
        reducer = Reducer(cfg.llvm_bin, output_dir, test)
        reducer.reduce()

    if cfg.action == "get_interesting_address":
        raise SystemExit("action 'get_interesting_address' is not implemented yet.")


if __name__ == "__main__":
    main()
