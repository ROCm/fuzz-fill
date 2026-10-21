"""TEMPORARY stand-in for ``sancov -union``.

Run as ``python -m coverage.sancov_union @<list> --output <out.sancov>``, the
same arguments ``sancov -union`` takes, so ``Sancov.union_files`` can run it
as a subprocess. Remove this module once the upstream ``sancov -union`` fix is
in the toolchain fuzz-fill builds.
"""

from __future__ import annotations

import argparse
import shlex
import struct
import sys
from collections.abc import Sequence
from pathlib import Path

import numpy as np

# Binary .sancov header, matching llvm/tools/sancov RawCoverage.
SANCOV_MAGIC = 0xC0BFFFFF
SANCOV_BITNESS64 = 0xFFFFFF64
SANCOV_BITNESS32 = 0xFFFFFF32
SANCOV_HEADER = struct.Struct("=II")

# Widest address span tracked with a one-byte-per-address bitmap before
# _AddressUnion falls back to a Python set.
BITMAP_MAX_SPAN = 256 * 1024 * 1024


def read_addresses(path: Path) -> tuple[int, np.ndarray]:
    """Return ``(bitness, nonzero addresses)`` from one binary ``.sancov`` file."""
    data = path.read_bytes()
    if len(data) < SANCOV_HEADER.size:
        raise ValueError(f"sancov file too small ({len(data)} bytes): {path}")
    bitness, magic = SANCOV_HEADER.unpack_from(data)
    if magic != SANCOV_MAGIC:
        raise ValueError(f"sancov magic mismatch ({magic:#x}): {path}")
    if bitness == SANCOV_BITNESS64:
        width = 8
        dtype = np.uint64
    elif bitness == SANCOV_BITNESS32:
        width = 4
        dtype = np.uint32
    else:
        raise ValueError(f"unsupported sancov bitness ({bitness:#x}): {path}")
    count = (len(data) - SANCOV_HEADER.size) // width
    if count == 0:
        return bitness, np.empty(0, dtype=dtype)
    addrs = np.frombuffer(data, dtype=dtype, count=count, offset=SANCOV_HEADER.size)
    return bitness, addrs[addrs != 0]


class _AddressUnion:
    """Set of coverage addresses, stored as a bitmap over their span.

    Coverage PCs of one binary sit in a narrow text range, so marking them in a
    byte array is much cheaper than inserting each one into a Python set.
    """

    def __init__(self) -> None:
        self._base = 0
        self._bitmap: np.ndarray | None = None
        self._overflow: set[int] | None = None

    def add(self, addrs: np.ndarray) -> None:
        if not addrs.size:
            return
        if self._overflow is not None:
            self._overflow.update(addrs.tolist())
            return
        lo = int(addrs.min())
        hi = int(addrs.max())
        if self._bitmap is None:
            new_base, new_end = lo, hi + 1
        else:
            end = self._base + self._bitmap.size
            new_base, new_end = min(lo, self._base), max(hi + 1, end)
        if new_end - new_base > BITMAP_MAX_SPAN:
            self._overflow = set(self.sorted().tolist())
            self._bitmap = None
            self._overflow.update(addrs.tolist())
            return
        if self._bitmap is None:
            self._base = new_base
            self._bitmap = np.zeros(new_end - new_base, dtype=np.bool_)
        elif new_base != self._base or new_end != self._base + self._bitmap.size:
            grown = np.zeros(new_end - new_base, dtype=np.bool_)
            offset = self._base - new_base
            grown[offset:offset + self._bitmap.size] = self._bitmap
            self._base, self._bitmap = new_base, grown
        self._bitmap[addrs.astype(np.uint64) - np.uint64(self._base)] = True

    def sorted(self) -> np.ndarray:
        if self._overflow is not None:
            ordered = np.fromiter(
                self._overflow, dtype=np.uint64, count=len(self._overflow)
            )
            ordered.sort()
            return ordered
        if self._bitmap is None:
            return np.empty(0, dtype=np.uint64)
        return np.flatnonzero(self._bitmap).astype(np.uint64) + np.uint64(self._base)


def union_sancov_files(inputs: Sequence[str | Path], output: Path) -> None:
    """Union *inputs* into *output*, like ``sancov -union``.

    Addresses are written sorted under the first file's header. Zero slots are
    dropped, matching ``RawCoverage::read``.
    """
    if not inputs:
        raise ValueError("union requires at least one input sancov file")
    union = _AddressUnion()
    out_bitness: int | None = None
    first = Path(inputs[0])
    for raw in inputs:
        path = Path(raw)
        bitness, addrs = read_addresses(path)
        if out_bitness is None:
            out_bitness = bitness
        elif bitness != out_bitness:
            print(
                f"WARNING: Input files have different bitness ({first}: "
                f"{out_bitness:#x}, {path}: {bitness:#x}). Using bitness from "
                f"{first}.",
                file=sys.stderr,
            )
        union.add(addrs)

    assert out_bitness is not None
    ordered = union.sorted()
    with Path(output).open("wb") as out:
        out.write(SANCOV_HEADER.pack(out_bitness, SANCOV_MAGIC))
        if out_bitness == SANCOV_BITNESS32:
            out.write(ordered.astype(np.uint32).tobytes())
        else:
            out.write(ordered.tobytes())


def expand_response_files(args: Sequence[str]) -> list[str]:
    """Replace ``@file`` arguments with the quoted paths listed in them."""
    expanded: list[str] = []
    for arg in args:
        if arg.startswith("@"):
            text = Path(arg[1:]).read_text(encoding="utf-8")
            expanded.extend(shlex.split(text))
        else:
            expanded.append(arg)
    return expanded


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help=".sancov files or @response-file")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        union_sancov_files(expand_response_files(args.inputs), args.output)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
