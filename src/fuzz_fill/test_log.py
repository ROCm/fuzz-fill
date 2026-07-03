from __future__ import annotations

import logging
import unittest

from fuzz_fill.log import configure_logging, get_logger, log_timing


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


if __name__ == "__main__":
    unittest.main()
