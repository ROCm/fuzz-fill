from __future__ import annotations

import io
import logging
import sys
import tempfile
import unittest
from pathlib import Path

from fuzz_fill.log import (
    DEFAULT_LOG_FILENAME,
    configure_logging,
    disable_log_file,
    enable_log_file,
    get_logger,
    log_timing,
)


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(self.format(record))


class ConfigureLoggingTests(unittest.TestCase):
    def test_sets_root_level(self) -> None:
        configure_logging("warning")
        self.assertEqual(logging.getLogger("fuzz_fill").level, logging.WARNING)

        configure_logging("debug")
        self.assertEqual(logging.getLogger("fuzz_fill").level, logging.DEBUG)


class LogTimingTests(unittest.TestCase):
    def setUp(self) -> None:
        configure_logging("debug")
        self.logger = get_logger("test")
        self.handler = _ListHandler()
        self.handler.setFormatter(
            logging.Formatter("%(levelname)s [%(name)s] %(message)s")
        )
        logging.getLogger("fuzz_fill").addHandler(self.handler)

    def tearDown(self) -> None:
        logging.getLogger("fuzz_fill").removeHandler(self.handler)

    def test_emits_start_and_elapsed_finish(self) -> None:
        with log_timing(self.logger, "example-op"):
            pass

        messages = "\n".join(self.handler.records)
        self.assertIn("example-op: starting", messages)
        self.assertRegex(messages, r"example-op finished in \d+\.\d{2}s")


class LogFileTests(unittest.TestCase):
    def setUp(self) -> None:
        disable_log_file()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.terminal_stdout = io.StringIO()
        self.terminal_stderr = io.StringIO()
        self.saved_stdout = sys.stdout
        self.saved_stderr = sys.stderr
        sys.stdout = self.terminal_stdout
        sys.stderr = self.terminal_stderr

    def tearDown(self) -> None:
        disable_log_file()
        sys.stdout = self.saved_stdout
        sys.stderr = self.saved_stderr
        self._tmpdir.cleanup()

    def test_creates_log_file_with_expected_name(self) -> None:
        out_dir = Path(self._tmpdir.name)
        log_path = enable_log_file(out_dir)

        self.assertEqual(log_path, out_dir / DEFAULT_LOG_FILENAME)
        self.assertTrue(log_path.exists())
        disable_log_file()

    def test_print_and_logging_go_to_file_and_terminal(self) -> None:
        out_dir = Path(self._tmpdir.name)
        log_path = enable_log_file(out_dir)
        configure_logging("info")
        logger = get_logger("test")

        print("hello stdout")
        logger.info("hello logger")
        disable_log_file()

        log_text = log_path.read_text(encoding="utf-8")
        self.assertIn("hello stdout", log_text)
        self.assertIn("hello logger", log_text)
        self.assertIn("hello stdout", self.terminal_stdout.getvalue())
        self.assertIn("hello logger", self.terminal_stderr.getvalue())

    def test_disable_restores_original_streams(self) -> None:
        out_dir = Path(self._tmpdir.name)
        stdout_before = sys.stdout
        enable_log_file(out_dir)

        self.assertIsNot(sys.stdout, stdout_before)
        disable_log_file()
        self.assertIs(sys.stdout, stdout_before)

    def test_enable_twice_raises(self) -> None:
        out_dir = Path(self._tmpdir.name)
        enable_log_file(out_dir)

        with self.assertRaises(RuntimeError):
            enable_log_file(out_dir)

        disable_log_file()

    def test_disable_when_not_enabled_is_noop(self) -> None:
        disable_log_file()


if __name__ == "__main__":
    unittest.main()
