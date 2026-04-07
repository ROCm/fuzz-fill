"""Orchestrate test run + per-binary SanCov processing and outline output."""

from __future__ import annotations

import json
from pathlib import Path

from coverage.config import CoverageConfig
from coverage.runner import TestCommandRunner
from coverage.sancov import BinaryCoverageResult, SanCov


LLC_TEST_SANCOV_MAP_JSON = "llc_test_sancov_map.json"


def _collect_llc_input_files(test_root: Path) -> list[Path]:
    """Sorted unique paths under ``test_root`` with suffix ``.ll`` or ``.bc``."""
    paths: set[Path] = set()
    for pattern in ("*.ll", "*.bc"):
        paths.update(p for p in test_root.rglob(pattern) if p.is_file())
    return sorted(paths)


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
        if self.config.llc_tests_dir is not None:
            return self._run_llc_tests_dir()
        assert self.config.command is not None
        return self._runner.run(
            self.config.command,
            self.config.cwd,
            self.config.coverage_dir,
        )

    def _run_llc_tests_dir(self) -> int:
        """Run ``llc -o /dev/null`` on each ``*.ll`` / ``*.bc`` under ``llc_tests_dir``; raw ``llc.*.sancov`` only."""
        d = self.config.llc_tests_dir
        assert d is not None
        llc = self.san_cov.tool_binary("llc")
        if not llc.exists():
            raise FileNotFoundError(f"llc not found at {llc}")

        tests = _collect_llc_input_files(d)
        if not tests:
            raise RuntimeError(f"no .ll or .bc files under {d}")

        limit = self.config.llc_tests_limit
        assert limit is not None
        z = len(tests)
        y = min(limit, z)
        to_run = tests[:y]

        cov = self.config.coverage_dir
        test_to_sancov: dict[str, str | list[str] | None] = {}

        def raw_llc_sancov_names() -> set[str]:
            return {p.name for p in self.san_cov.collect_raw(cov, "llc")}

        any_failed = False
        for i, test_path in enumerate(to_run, start=1):
            print(f"running [{i}/{y}] out of {z} in directory {d}")
            rel = test_path.relative_to(d)
            test_key = rel.as_posix()
            before = raw_llc_sancov_names()
            argv = [str(llc), "-o", "/dev/null", str(rel)]
            rc = self._runner.run_argv(argv, d, cov)
            after = raw_llc_sancov_names()
            new_names = sorted(after - before)
            if len(new_names) == 1:
                test_to_sancov[test_key] = new_names[0]
            elif not new_names:
                test_to_sancov[test_key] = None
            else:
                test_to_sancov[test_key] = new_names
            if rc != 0:
                any_failed = True
                print(f"FAILED: {rel} (exit {rc})")

        map_path = cov / LLC_TEST_SANCOV_MAP_JSON
        map_path.write_text(json.dumps(test_to_sancov, indent=2, sort_keys=True) + "\n")
        print(f"Test → sancov map -> {map_path}")

        return 1 if any_failed else 0

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
        if self.config.llc_tests_dir is not None:
            raw = self.san_cov.collect_raw(self.config.coverage_dir, "llc")
            print(
                f"({len(raw)} raw llc.*.sancov in {self.config.coverage_dir}; "
                "no merge/symbolize in --llc-tests-dir mode)"
            )
            return run_returncode if run_returncode is not None else 1

        results = self.process_binaries()
        self.write_outlines(results, run_returncode)
        return 0
