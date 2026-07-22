"""Tests for CLI path validation helpers."""

from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from fuzz_fill.env import existing_dir_path, existing_file_path


class ExistingPathValidationTest(unittest.TestCase):
    def test_existing_file_path_resolves(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv") as tmp:
            path = existing_file_path(tmp.name)
            self.assertTrue(path.is_file())
            self.assertTrue(path.is_absolute())

    def test_existing_file_path_rejects_missing(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            existing_file_path("/no/such/file.csv")
        self.assertIn("not a file", str(ctx.exception))

    def test_existing_dir_path_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = existing_dir_path(tmp)
            self.assertTrue(path.is_dir())
            self.assertTrue(path.is_absolute())

    def test_existing_dir_path_rejects_missing(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            existing_dir_path("/no/such/directory")
        self.assertIn("not a directory", str(ctx.exception))

    def test_existing_dir_path_rejects_file(self) -> None:
        with tempfile.NamedTemporaryFile() as tmp:
            with self.assertRaises(argparse.ArgumentTypeError) as ctx:
                existing_dir_path(tmp.name)
            self.assertIn("not a directory", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
