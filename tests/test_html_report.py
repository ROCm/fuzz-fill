# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Unit tests for the self-contained HTML coverage report writer."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from coverage.html_report import write_html_report


def _write_summary(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


class WriteHtmlReportTest(unittest.TestCase):
    def test_report_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_root = root / "llvm-src"
            dir_a = src_root / "llvm" / "lib" / "Foo"
            dir_a.mkdir(parents=True)
            file_high = dir_a / "High.cpp"
            file_low = dir_a / "Low.cpp"
            file_high.write_text(
                "line1\nline2\nline3\nline4\nline5\n",
                encoding="utf-8",
            )
            file_low.write_text("only\n", encoding="utf-8")

            summary = root / "line_coverage_summary.csv"
            _write_summary(
                summary,
                [
                    ["file", "line", "coverage"],
                    [str(file_high), 1, "covered"],
                    [str(file_high), 2, "covered"],
                    [str(file_high), 3, "uncovered"],
                    [str(file_high), 4, "uncovered"],
                    [str(file_low), 1, "covered"],
                ],
            )

            out = root / "html"
            write_html_report(
                summary,
                out,
                strip_prefix=src_root,
                github_repo="llvm/llvm-project",
                llvm_ref="main",
                commit="abc123def",
                projects="clang",
                backends="X86;AMDGPU",
                tests=["llvm/test", "clang/test"],
            )

            index = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn("<h2>Run</h2>", index)
            self.assertIn("Repository: llvm/llvm-project", index)
            self.assertIn("Ref: main", index)
            self.assertIn("Commit: abc123def", index)
            self.assertIn("Projects: clang", index)
            self.assertIn("Backends: X86;AMDGPU", index)
            self.assertIn("Tests: llvm/test, clang/test", index)
            high_page = (
                out / "llvm" / "lib" / "Foo" / "High.cpp.html"
            ).read_text(encoding="utf-8")

            self.assertIn("Instrumented lines: 5", index)
            self.assertIn("Covered: 3 (60.0%)", index)
            self.assertIn("Uncovered: 2 (40.0%)", index)
            self.assertNotIn("Partially:", index)

            self.assertIn("Directory Tree", index)
            self.assertIn("Coverage Gaps Report", index)
            self.assertIn("Statistics", index)
            self.assertIn('<span class="dir-name">llvm/</span>', index)
            self.assertIn('<span class="dir-name">Foo/</span>', index)
            self.assertIn("unc=2 (40.0%)", index)
            self.assertIn("cov=3 (60.0%)", index)
            self.assertNotIn("part=", index)

            # Nested tree: High (more uncovered) before Low at the same level.
            high_pos = index.find(">High.cpp</a>")
            low_pos = index.find(">Low.cpp</a>")
            self.assertGreater(high_pos, 0)
            self.assertGreater(low_pos, high_pos)
            self.assertIn('href="llvm/lib/Foo/High.cpp.html"', index)

            self.assertIn("designed to highlight", index)
            self.assertIn("coverage gaps", index)
            self.assertIn("this test-suite run.", index)
            self.assertNotIn("as explained", index)
            self.assertIn("source-based coverage instrumentation", index)
            self.assertIn("-fprofile-instr-generate", index)
            self.assertIn("-fcoverage-mapping", index)
            self.assertIn("LCOV <code>DA</code>", index)
            self.assertNotIn("SanitizerCoverage", index)
            self.assertIn('class="status-list"', index)
            self.assertIn(
                "<strong>uncovered</strong> (zero execution count)",
                index,
            )
            # Index keeps a high-level intro; per-line legend is on file pages.
            self.assertNotIn("Green — covered.", index)
            self.assertNotIn(
                "when a dominator already implies they ran",
                index,
            )

            self.assertIn('id="L1"', high_page)
            self.assertIn('id="L2"', high_page)
            self.assertIn('id="L3"', high_page)
            self.assertIn('href="#L1"', high_page)
            self.assertIn('class="line covered"', high_page)
            self.assertNotIn('class="line partially-covered"', high_page)
            self.assertIn('class="line not-covered"', high_page)
            self.assertIn('class="code"', high_page)
            self.assertIn('<div class="source">', high_page)
            self.assertNotIn("highlight.min.js", high_page)
            self.assertIn("Green — covered.", high_page)
            self.assertIn("non-zero execution count", high_page)
            self.assertIn("zero execution count", high_page)
            self.assertIn("LCOV <code>DA</code>", high_page)
            self.assertNotIn("when a dominator already implies they ran", high_page)
            self.assertNotIn("SanitizerCoverage", high_page)
            self.assertIn('href="../../../index.html"', high_page)
            self.assertIn('id="jump-next"', high_page)
            self.assertIn('id="jump-bar"', high_page)
            self.assertIn('data-mode="uncovered"', high_page)
            self.assertNotIn('data-mode="partially"', high_page)
            self.assertIn('data-mode="covered"', high_page)
            self.assertIn('data-mode="instrumented"', high_page)
            self.assertIn("<kbd>n</kbd> next", high_page)
            self.assertIn("<kbd>j</kbd> previous", high_page)
            self.assertIn("<kbd>m</kbd> mode", high_page)
            self.assertIn("div.line.not-covered", high_page)
            self.assertNotIn("div.line.partially-covered", high_page)
            self.assertIn("div.line.covered", high_page)

            # Line 5 is uninstrumented: present with no status class.
            self.assertIn('id="L5" class="line"', high_page)

            # Covered-only file still gets the jump bar (covered + instrumented).
            low_page = (
                out / "llvm" / "lib" / "Foo" / "Low.cpp.html"
            ).read_text(encoding="utf-8")
            self.assertIn('id="jump-next"', low_page)
            self.assertIn('data-mode="covered"', low_page)
            self.assertIn('data-mode="instrumented"', low_page)
            self.assertNotIn('data-mode="uncovered"', low_page)
            self.assertIn("a.gutter", low_page)
            self.assertIn('block: "center"', low_page)
            self.assertIn("jump-flash", low_page)
            self.assertIn("jump-current", low_page)


if __name__ == "__main__":
    unittest.main()
