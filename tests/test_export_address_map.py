"""Unit tests for export-address-map helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from coverage.export_address_map import default_address_map_output, export_address_map


class ExportAddressMapTest(unittest.TestCase):
    def test_canonicalizes_paths_and_drops_outside_source_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            llvm_src = root / "llvm-project"
            source = llvm_src / "llvm" / "lib" / "Foo.cpp"
            source.parent.mkdir(parents=True)
            source.write_text("x\n", encoding="utf-8")
            outside = root / "outside.cpp"
            outside.write_text("x\n", encoding="utf-8")
            tool = root / "llc"
            sancov = root / "sancov"
            tool.write_text("#!/bin/sh\n", encoding="utf-8")
            sancov.write_text("#!/bin/sh\n", encoding="utf-8")
            tool.chmod(0o755)
            sancov.chmod(0o755)
            output = root / "map.csv"

            def fake_run(_logger, _cmd, **kwargs):
                raw_dir = Path(kwargs["env"]["UBSAN_OPTIONS"].split("coverage_dir=", 1)[1].split(":", 1)[0])
                (raw_dir / "llc.1.sancov").write_bytes(b"raw")

                class Result:
                    returncode = 0

                return Result()

            with (
                patch("coverage.export_address_map.run_subprocess", side_effect=fake_run),
                patch("coverage.sancov.Sancov.union_files", lambda _self, _inputs, out: out.write_bytes(b"merged")),
                patch("coverage.sancov.Sancov.symbolize", lambda _self, _src, out: out.write_text("{}", encoding="utf-8")),
                patch(
                    "coverage.sancov.Sancov.load_coverage_dfs",
                    return_value=[
                        pd.DataFrame(
                            [
                                [str(source), 10, "0x1", 1],
                                ["llvm/lib/Foo.cpp", 11, "0x2", 0],
                                [str(outside), 1, "0x3", 1],
                            ],
                            columns=["file", "line", "point", "covered"],
                        )
                    ],
                ),
            ):
                export_address_map(
                    tool=tool,
                    sancov=sancov,
                    llvm_src=llvm_src,
                    output=output,
                )

            rows = pd.read_csv(output)
            self.assertEqual(rows["file"].tolist(), ["llvm/lib/Foo.cpp", "llvm/lib/Foo.cpp"])
            self.assertEqual(rows["line"].tolist(), [10, 11])

    def test_default_output_uses_tool_name(self) -> None:
        self.assertEqual(default_address_map_output(Path("/tmp/llc")).name, "llc_address_line_map.csv")


if __name__ == "__main__":
    unittest.main()
