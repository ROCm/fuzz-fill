"""Run a single reduction job from a config.json."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fuzz_fill.llvm_tools import ReduceTools
from fuzz_fill.log import configure_logging, get_logger, resolve_log_file
from reduce.config import load_reduce_config, pipeline_steps_for_only_pass
from reduce.reducer import Reducer
from reduce.test import Test

logger = get_logger("reduce")


def run_single_reduce(
    *,
    config: Path,
    tools: ReduceTools,
    only_pass: str | None = None,
    log_level: str = "INFO",
    log_to_file: bool = False,
) -> None:
    """Load *config* and run the configured reduction pipeline."""
    print("[main] loading config...", flush=True)
    cfg = load_reduce_config(config)

    if only_pass is not None:
        pipeline_steps = pipeline_steps_for_only_pass(cfg.pipeline, only_pass)
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

    configure_logging(
        log_level,
        log_file=resolve_log_file(output_dir, log_to_file),
    )

    pass_ids = [s.id for s in pipeline_steps]
    logger.info("reduce (%d pass(es): %s)", len(pass_ids), ", ".join(pass_ids))
    reducer = Reducer(
        tools,
        output_dir,
        test,
        pipeline_steps=pipeline_steps,
    )
    reducer.reduce()
