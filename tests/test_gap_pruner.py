from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gap_pruner.__main__ import prune_noncoverable_lines
from gap_pruner.noncoverable_spans import find_noncoverable_lines


class TestGapPrunerControlFlow(unittest.TestCase):
    def test_control_flow_is_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.cpp"
            source.write_text(
                "\n".join(
                    [
                        "if (flag)",
                        "  return;",
                        "while (flag)",
                        "  --flag;",
                        "for (int i = 0; i < 1; ++i)",
                        "  foo();",
                        "assert(",
                        "    flag);",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(find_noncoverable_lines(source), {7, 8})
            self.assertEqual(
                find_noncoverable_lines(source, prune_control_flow=True),
                {1, 3, 5, 7, 8},
            )

    def test_prune_noncoverable_lines_threads_control_flow_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.cpp"
            source.write_text("if (flag)\nassert(flag)\ncovered();\n", encoding="utf-8")
            rows = [
                {"file": str(source), "line": "1"},
                {"file": str(source), "line": "2"},
                {"file": str(source), "line": "3"},
            ]

            self.assertEqual(
                prune_noncoverable_lines(rows, None),
                [
                    {"file": str(source), "line": "1"},
                    {"file": str(source), "line": "3"},
                ],
            )
            self.assertEqual(
                prune_noncoverable_lines(rows, None, prune_control_flow=True),
                [{"file": str(source), "line": "3"}],
            )


if __name__ == "__main__":
    unittest.main()
