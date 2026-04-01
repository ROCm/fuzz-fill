"""Orchestrate test run + per-binary SanCov processing and outline output."""

from __future__ import annotations

import json
from pathlib import Path

from coverage.config import CoverageConfig
from coverage.runner import TestCommandRunner
from coverage.sancov import BinaryCoverageResult, SanCov


class CoverageSession:
    """One llvm-lit (or custom) run plus merge/symbolize for configured binaries."""

    def __init__(self, config: CoverageConfig) -> None:
        self.config = config
        self.san_cov = SanCov(
            config.build_bin_dir,
            merged_suffix_id=config.merged_suffix_id,
            union_batch=config.union_batch,
        )
        self._runner = TestCommandRunner()

    def run_tests(self) -> int | None:
        if self.config.skip_run:
            print("(--skip-run: not executing tests)")
            return None
        assert self.config.command is not None
        return self._runner.run(
            self.config.command,
            self.config.cwd,
            self.config.coverage_dir,
        )

    def process_binaries(self) -> list[BinaryCoverageResult]:
        if not self.san_cov.sancov_bin.exists():
            raise FileNotFoundError(
                f"sancov not found at {self.san_cov.sancov_bin}"
            )

        results: list[BinaryCoverageResult] = []
        for binary_name in self.config.binaries:
            tool = self.san_cov.tool_binary(binary_name)
            if not tool.exists():
                raise FileNotFoundError(f"binary not found at {tool}")

            raw = self.san_cov.collect_raw(self.config.coverage_dir, binary_name)
            print(
                f"Found {len(raw)} raw .sancov file(s) for {binary_name}"
            )
            if not raw:
                print(
                    f"WARNING: skipping {binary_name}: no raw "
                    f"<{binary_name}>.<digits>.sancov in {self.config.coverage_dir}"
                )
                continue

            result = self.san_cov.process_binary_from_raw(
                self.config.coverage_dir, binary_name, raw
            )

            print(f"Merged raw coverage -> {result.merged_sancov}")
            print(f"Symbolized -> {result.merged_symcov}")
            print()
            print(result.stats_text)
            results.append(result)

        if not results:
            raise RuntimeError(
                "no binaries produced coverage (no raw .sancov inputs)"
            )
        return results

    def write_outlines(
        self,
        results: list[BinaryCoverageResult],
        run_returncode: int | None,
    ) -> None:
        sections: list[str] = []
        per_binary: dict[str, dict[str, object]] = {}
        for r in results:
            sections.append(
                f"=== {r.binary_name} ===\n"
                + r.stats_text.rstrip()
                + "\n---\n"
                + f"merged_sancov: {r.merged_sancov}\n"
                + f"merged_symcov: {r.merged_symcov}\n"
                + f"raw_sancov_count: {r.raw_sancov_count}\n"
            )
            per_binary[r.binary_name] = {
                "merged_sancov": str(r.merged_sancov),
                "merged_symcov": str(r.merged_symcov),
                "raw_sancov_count": r.raw_sancov_count,
                "stats": r.stats,
                "stats_raw": r.stats_text.strip(),
            }

        outline_txt = self.config.coverage_dir / "coverage_outline.txt"
        outline_txt.write_text("\n".join(sections).rstrip() + "\n")
        print(f"Outline -> {outline_txt}")

        if self.config.outline_json is not None:
            payload = {
                "binaries": per_binary,
                "run_summary": {
                    "command": self.config.command,
                    "returncode": run_returncode,
                },
            }
            self.config.outline_json.write_text(json.dumps(payload, indent=2))
            print(f"JSON outline -> {self.config.outline_json}")

    def run(self) -> int:
        """Run tests (unless skipped), then merge/symbolize and write outlines. Exit 0 on success."""
        self.config.coverage_dir.mkdir(parents=True, exist_ok=True)
        run_returncode = self.run_tests()
        results = self.process_binaries()
        self.write_outlines(results, run_returncode)
        return 0
