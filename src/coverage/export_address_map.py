"""Export a SanitizerCoverage PC→line map for one instrumented tool."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from coverage.paths import canonicalize_source_path
from coverage.sancov import Sancov
from fuzz_fill.log import get_logger, run_subprocess

logger = get_logger("coverage.export_address_map")


def export_address_map(
    *,
    tool: Path,
    sancov: Path,
    llvm_src: Path,
    output: Path,
    tool_args: list[str] | None = None,
) -> Path:
    """Run ``tool`` once, symbolize with ``--no-skip-dead-files``, write the map CSV.

    Default ``tool_args`` is ``["--version"]``. ``file`` columns are canonicalized
    relative to ``llvm_src``; rows outside the tree are dropped.
    """
    tool = tool.resolve()
    sancov = sancov.resolve()
    llvm_src = llvm_src.resolve()
    output = output.resolve()
    args = list(tool_args) if tool_args is not None else ["--version"]

    if not tool.is_file() or not os.access(tool, os.X_OK):
        raise SystemExit(f"--tool is not executable: {tool}")
    if not sancov.is_file() or not os.access(sancov, os.X_OK):
        raise SystemExit(f"--sancov is not executable: {sancov}")

    with tempfile.TemporaryDirectory(prefix="export-address-map-") as tmp:
        tmp_dir = Path(tmp)
        raw_dir = tmp_dir / "raw"
        raw_dir.mkdir()
        env = os.environ.copy()
        # SanitizerCoverage dumps via UBSAN_OPTIONS when the binary is instrumented
        # that way (fuzz-fill sancov builds).
        env["UBSAN_OPTIONS"] = (
            f"coverage=1:coverage_dir={raw_dir}:print_coverage_summary=0"
        )
        env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "")
        run_subprocess(
            logger,
            [str(tool), *args],
            label=f"{tool.name} {' '.join(args)}",
            check=False,
            env=env,
            capture_output=True,
            text=True,
        )
        dumps = sorted(raw_dir.glob("*.sancov"))
        if not dumps:
            raise SystemExit(
                f"no .sancov dumps under {raw_dir} after running {tool} {' '.join(args)}"
            )
        # sancov matches the dump basename prefix to the binary name, so the
        # merged file must be named ``<tool>.<n>.sancov`` (not a generic name).
        helper = Sancov(
            sancov,
            symbolize_target=tool,
            raw_sancov_dir=raw_dir,
            suffix=tool.name,
        )
        # Sancov stores outputs next to raw_sancov_dir by default; force tmp.
        helper.output_dir = tmp_dir
        merged = tmp_dir / f"{tool.name}.0.sancov"
        helper.union_files(dumps, merged)
        symcov = tmp_dir / f"{tool.name}.0.symcov"
        helper.symbolize(merged, symcov)
        df = Sancov.load_coverage_dfs([symcov], "")[0]
        address_map = Sancov.build_address_line_map(df)

    # Canonicalize file paths; drop outside-tree rows.
    rel_files: list[str | None] = [
        canonicalize_source_path(str(f), llvm_src) for f in address_map["file"]
    ]
    address_map = address_map.copy()
    address_map["file"] = rel_files
    address_map = address_map[address_map["file"].notna()].reset_index(drop=True)
    if address_map.empty:
        raise SystemExit(
            "address map has no rows under --llvm-src after path canonicalization"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    address_map.to_csv(output, index=False)
    logger.info("wrote address map (%d rows) to %s", len(address_map), output)
    return output


def default_address_map_output(tool: Path) -> Path:
    return Path(Sancov.tool_address_line_map_filename(tool.name))
