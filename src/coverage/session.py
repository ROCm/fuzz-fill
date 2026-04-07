"""Orchestrate test run + per-binary SanCov processing and outline output."""

from __future__ import annotations

import csv
import json
from contextlib import ExitStack
from pathlib import Path

from coverage.baseline_csv import (
    addresses_in_test_not_in_baseline,
    load_baseline_llc_addresses_by_source_line,
    load_baseline_llc_addresses_from_csv,
    load_llc_line_address_map_rows,
    normalize_llc_address_for_compare,
    novel_source_lines_vs_baseline,
)
from coverage.config import CoverageConfig
from coverage.runner import TestCommandRunner
from coverage.sancov import BinaryCoverageResult, SanCov


LLC_TEST_REPORT_CSV = "llc_test_report.csv"
LLC_TEST_NOVEL_SOURCE_LINES_CSV = "llc_test_novel_source_lines.csv"


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
        if self.config.new_tests_dir is not None:
            return self._run_new_tests()
        assert self.config.command is not None
        return self._runner.run(
            self.config.command,
            self.config.cwd,
            self.config.coverage_dir,
        )

    def _run_new_tests(self) -> int:
        """Run ``llc -o /dev/null`` on each ``*.ll`` / ``*.bc`` under ``new_tests_dir``; per-test addresses via ``sancov --print`` only (no merge/symbolize)."""
        d = self.config.new_tests_dir
        assert d is not None
        llc = self.san_cov.tool_binary("llc")
        if not llc.exists():
            raise FileNotFoundError(f"llc not found at {llc}")
        sancov_tool = self.san_cov.sancov_bin
        if not sancov_tool.exists():
            raise FileNotFoundError(f"sancov not found at {sancov_tool}")

        tests = _collect_llc_input_files(d)
        if not tests:
            raise RuntimeError(f"no .ll or .bc files under {d}")

        limit = self.config.new_tests_limit
        assert limit is not None
        src_prefix = self.config.new_tests_source_path_prefix

        z = len(tests)
        y = min(limit, z)
        to_run = tests[:y]

        cov = self.config.coverage_dir
        baseline_path = self.config.new_tests_baseline_csv
        baseline_norm: set[str] | None = None
        if baseline_path is not None:
            baseline_norm = load_baseline_llc_addresses_from_csv(
                baseline_path,
                source_path_prefix=src_prefix,
            )
            pfx_note = (
                f" (source path prefix {src_prefix!r})" if src_prefix is not None else ""
            )
            print(
                f"Loaded {len(baseline_norm)} unique llc address(es) from baseline CSV "
                f"{baseline_path}{pfx_note}"
            )

        line_map_path = self.config.new_tests_line_address_map
        line_map_rows: list[tuple[str, str, int, frozenset[str]]] | None = None
        baseline_by_line: dict[tuple[str, str, int], frozenset[str]] | None = None
        if line_map_path is not None:
            line_map_rows = load_llc_line_address_map_rows(
                line_map_path,
                source_path_prefix=src_prefix,
            )
            print(
                f"Loaded {len(line_map_rows)} source line row(s) from --line-address-map "
                f"{line_map_path}"
                + (f" (prefix {src_prefix!r})" if src_prefix is not None else "")
            )
            assert baseline_path is not None
            baseline_by_line = load_baseline_llc_addresses_by_source_line(
                baseline_path,
                source_path_prefix=src_prefix,
            )
            print(
                f"Loaded {len(baseline_by_line)} baseline (file,function,line) location(s) "
                f"for per-line comparison"
            )

        def raw_llc_sancov_names() -> set[str]:
            return {p.name for p in self.san_cov.collect_raw(cov, "llc")}

        report_path = cov / LLC_TEST_REPORT_CSV
        report_fields = [
            "test",
            "llc_exit_code",
            "raw_sancov_files",
            "baseline_unique_address_count",
            "test_unique_address_count",
            "test_only_address_count",
            "baseline_only_address_count",
            "both_address_count",
            "novel_source_line_count",
            "novel_vs_baseline_addresses",
        ]

        novel_path = cov / LLC_TEST_NOVEL_SOURCE_LINES_CSV
        any_failed = False
        with ExitStack() as stack:
            report_f = stack.enter_context(
                report_path.open("w", newline="", encoding="utf-8")
            )
            writer = csv.DictWriter(report_f, fieldnames=report_fields)
            writer.writeheader()
            report_f.flush()

            novel_f = None
            novel_writer: csv.DictWriter | None = None
            if line_map_rows is not None:
                novel_f = stack.enter_context(
                    novel_path.open("w", newline="", encoding="utf-8")
                )
                novel_writer = csv.DictWriter(
                    novel_f,
                    fieldnames=["test", "file", "function", "line"],
                )
                novel_writer.writeheader()
                novel_f.flush()

            for i, test_path in enumerate(to_run, start=1):
                print(f"running [{i}/{y}] out of {z} in directory {d}")
                rel = test_path.relative_to(d)
                test_key = rel.as_posix()
                before = raw_llc_sancov_names()
                argv = [str(llc), "-o", "/dev/null", str(rel)]
                rc = self._runner.run_argv(argv, d, cov)
                after = raw_llc_sancov_names()
                new_names = sorted(after - before)

                addr_strings: set[str] = set()
                for basename in new_names:
                    sp = cov / basename
                    if sp.is_file():
                        addr_strings |= self.san_cov.unique_addresses_from_print(sp)
                test_norm = {
                    normalize_llc_address_for_compare(a) for a in addr_strings
                }
                print(f"{len(test_norm)} addresses covered by test {test_key}")

                if baseline_norm is not None:
                    novel = addresses_in_test_not_in_baseline(addr_strings, baseline_norm)
                    print(
                        f"{len(novel)} address(es) from test {test_key} not in baseline CSV"
                    )
                    row_counts = {
                        "baseline_unique_address_count": len(baseline_norm),
                        "test_unique_address_count": len(test_norm),
                        "test_only_address_count": len(test_norm - baseline_norm),
                        "baseline_only_address_count": len(baseline_norm - test_norm),
                        "both_address_count": len(test_norm & baseline_norm),
                    }
                else:
                    novel = []
                    row_counts = {
                        "baseline_unique_address_count": "",
                        "test_unique_address_count": len(test_norm),
                        "test_only_address_count": "",
                        "baseline_only_address_count": "",
                        "both_address_count": "",
                    }

                novel_line_count: str | int = ""
                if line_map_rows is not None and baseline_by_line is not None:
                    novel_src = novel_source_lines_vs_baseline(
                        line_map_rows, baseline_by_line, test_norm
                    )
                    novel_line_count = len(novel_src)
                    print(
                        f"{novel_line_count} source line(s) for test {test_key} hit by new "
                        "coverage but no line id in baseline"
                    )
                    assert novel_writer is not None and novel_f is not None
                    for file_s, func_s, line_num in novel_src:
                        novel_writer.writerow(
                            {
                                "test": test_key,
                                "file": file_s,
                                "function": func_s,
                                "line": line_num,
                            }
                        )
                    novel_f.flush()

                writer.writerow(
                    {
                        "test": test_key,
                        "llc_exit_code": rc,
                        "raw_sancov_files": json.dumps(new_names),
                        "novel_vs_baseline_addresses": json.dumps(novel),
                        "novel_source_line_count": novel_line_count,
                        **row_counts,
                    }
                )
                report_f.flush()

                if rc != 0:
                    any_failed = True
                    print(f"FAILED: {rel} (exit {rc})")

        print(f"LLC test report CSV -> {report_path} ({y} row(s))")
        if line_map_rows is not None:
            print(f"Novel source lines (detail) -> {novel_path}")

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
        """Run tests (unless skipped), then merge/symbolize and write outlines (LIT path only)."""
        self.config.coverage_dir.mkdir(parents=True, exist_ok=True)
        run_returncode = self.run_tests()
        if self.config.new_tests_dir is not None:
            raw = self.san_cov.collect_raw(self.config.coverage_dir, "llc")
            print(
                f"({len(raw)} raw llc.*.sancov in {self.config.coverage_dir}; "
                "new-tests mode: no merge or symbolize; addresses from sancov --print per test.)"
            )
            return run_returncode if run_returncode is not None else 1

        results = self.process_binaries()
        self.write_outlines(results, run_returncode)
        return 0
