import argparse
from datetime import datetime
from pathlib import Path

from reduce.config import load_reduce_config
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
        "--llvm-bin",
        type=Path,
        required=True,
        help="Path to llvm-project bin directory (must contain llvm-reduce).",
    )
    parser.add_argument(
        "--only-pass",
        default=argparse.SUPPRESS,
        choices=sorted(known_pass_ids()),
        metavar="PASS_ID",
        help="Run a single pass by id (input is the original .ll). For debugging.",
    )
    ns = parser.parse_args()
    print("[main] loading config...", flush=True)
    cfg = load_reduce_config(ns.config, ns.llvm_bin.resolve())

    if getattr(ns, "only_pass", None) is not None:
        pass_ids = [ns.only_pass]
    else:
        pass_ids = list(cfg.pipeline)

    test = Test(cfg.original_test, cfg.interesting, f"/{cfg.file}", cfg.line)

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
    print(f"[main] action={cfg.action!r}", flush=True)

    # Run interesting script only (no llvm-reduce).
    if cfg.action == "test":
        print("[main] stage: test (interesting script)", flush=True)
        test.run()

    if cfg.action == "reduce":
        print(
            f"[main] stage: reduce ({len(pass_ids)} pass(es): {', '.join(pass_ids)})",
            flush=True,
        )
        reducer = Reducer(
            cfg.llvm_bin,
            output_dir,
            test,
            pass_ids=pass_ids,
            pass_under_test=cfg.pass_under_test,
        )
        reducer.reduce()


if __name__ == "__main__":
    main()
