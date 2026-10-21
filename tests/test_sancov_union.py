"""TEMPORARY Python ``sancov -union`` replacement in ``coverage.sancov_union``."""

from __future__ import annotations

import io
import struct
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from coverage.sancov import Sancov, _quote_rsp_path
from coverage.sancov_union import (
    SANCOV_BITNESS32,
    SANCOV_BITNESS64,
    SANCOV_HEADER,
    SANCOV_MAGIC,
    main,
    union_sancov_files,
)


def _sancov_bytes(bitness: int, addrs: list[int]) -> bytes:
    width = "Q" if bitness == SANCOV_BITNESS64 else "I"
    payload = struct.pack(f"={len(addrs)}{width}", *addrs) if addrs else b""
    return SANCOV_HEADER.pack(bitness, SANCOV_MAGIC) + payload


class UnionSancovFilesTest(unittest.TestCase):
    def test_unions_sorted_unique_addresses_and_drops_zeros(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.sancov"
            b = root / "b.sancov"
            a.write_bytes(_sancov_bytes(SANCOV_BITNESS64, [0x30, 0, 0x10, 0x30]))
            b.write_bytes(_sancov_bytes(SANCOV_BITNESS64, [0x20, 0, 0x10]))
            out = root / "out.sancov"
            union_sancov_files([a, b], out)
            self.assertEqual(
                out.read_bytes(),
                _sancov_bytes(SANCOV_BITNESS64, [0x10, 0x20, 0x30]),
            )

    def test_32bit_union_uses_first_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.sancov"
            b = root / "b.sancov"
            a.write_bytes(_sancov_bytes(SANCOV_BITNESS32, [4, 2]))
            b.write_bytes(_sancov_bytes(SANCOV_BITNESS32, [2, 9]))
            out = root / "out.sancov"
            union_sancov_files([b, a], out)
            self.assertEqual(
                out.read_bytes(),
                _sancov_bytes(SANCOV_BITNESS32, [2, 4, 9]),
            )

    def test_wide_address_span_falls_back_to_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.sancov"
            b = root / "b.sancov"
            far = 0x7F00_0000_0000
            a.write_bytes(_sancov_bytes(SANCOV_BITNESS64, [0x1000, 0x2000]))
            b.write_bytes(_sancov_bytes(SANCOV_BITNESS64, [far, 0x1000]))
            out = root / "out.sancov"
            with patch("coverage.sancov_union.BITMAP_MAX_SPAN", 1 << 20):
                union_sancov_files([a, b], out)
            self.assertEqual(
                out.read_bytes(),
                _sancov_bytes(SANCOV_BITNESS64, [0x1000, 0x2000, far]),
            )


class MainTest(unittest.TestCase):
    def test_reads_quoted_response_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spaced = root / "dir with space"
            spaced.mkdir()
            a = spaced / "a.sancov"
            b = spaced / 'b"quote\\.sancov'
            a.write_bytes(_sancov_bytes(SANCOV_BITNESS64, [2]))
            b.write_bytes(_sancov_bytes(SANCOV_BITNESS64, [1]))
            rsp = root / "list.rsp"
            rsp.write_text(
                f"{_quote_rsp_path(str(a))}\n{_quote_rsp_path(str(b))}\n",
                encoding="utf-8",
            )
            out = root / "out.sancov"
            self.assertEqual(main([f"@{rsp}", "--output", str(out)]), 0)
            self.assertEqual(
                out.read_bytes(), _sancov_bytes(SANCOV_BITNESS64, [1, 2])
            )

    def test_bad_magic_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.sancov"
            b = root / "b.sancov"
            a.write_bytes(_sancov_bytes(SANCOV_BITNESS64, [1]))
            b.write_bytes(b"not-a-sancov-file")
            out = root / "out.sancov"
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main([str(a), str(b), "--output", str(out)])
            self.assertEqual(code, 1)
            self.assertIn("magic mismatch", stderr.getvalue())


class UnionFilesSubprocessTest(unittest.TestCase):
    def test_union_files_runs_python_utility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.sancov"
            b = root / "b.sancov"
            a.write_bytes(_sancov_bytes(SANCOV_BITNESS64, [0x30, 0x10]))
            b.write_bytes(_sancov_bytes(SANCOV_BITNESS64, [0x20, 0x10]))
            out = root / "nested" / "out.sancov"
            Sancov(root / "sancov").union_files([a, b], out)
            self.assertEqual(
                out.read_bytes(),
                _sancov_bytes(SANCOV_BITNESS64, [0x10, 0x20, 0x30]),
            )


if __name__ == "__main__":
    unittest.main()
