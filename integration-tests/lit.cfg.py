# -*- Python -*-
"""llvm-lit configuration for fuzz-fill integration tests."""

import os
import shlex
import sys

import lit.formats

_sancov_bin = os.environ.get("FUZZ_FILL_SANCOV_LLVM_BIN_DIR")
_venv_dir = os.environ.get("FUZZ_FILL_VENV_DIR")
if not _sancov_bin:
    print(
        "error: FUZZ_FILL_SANCOV_LLVM_BIN_DIR must be set to the LLVM build bin directory",
        file=sys.stderr,
    )
    raise SystemExit(1)
_sancov_bin = os.path.abspath(os.path.expanduser(_sancov_bin))
if not os.path.exists(_sancov_bin):
    print(
        f"error: FUZZ_FILL_SANCOV_LLVM_BIN_DIR does not exist: {_sancov_bin!r}",
        file=sys.stderr,
    )
    raise SystemExit(1)
if not os.path.isdir(_sancov_bin):
    print(
        f"error: FUZZ_FILL_SANCOV_LLVM_BIN_DIR must be a directory, not a file: "
        f"{_sancov_bin!r}",
        file=sys.stderr,
    )
    raise SystemExit(1)
if not _venv_dir:
    print(
        "error: FUZZ_FILL_VENV_DIR must be set to a Python virtualenv directory",
        file=sys.stderr,
    )
    raise SystemExit(1)
_venv_dir = os.path.abspath(os.path.expanduser(_venv_dir))
if not os.path.exists(_venv_dir):
    print(
        f"error: FUZZ_FILL_VENV_DIR does not exist: {_venv_dir!r}",
        file=sys.stderr,
    )
    raise SystemExit(1)
if not os.path.isdir(_venv_dir):
    print(
        f"error: FUZZ_FILL_VENV_DIR must be a directory, not a file: {_venv_dir!r}",
        file=sys.stderr,
    )
    raise SystemExit(1)

_venv_activate = os.path.join(_venv_dir, "bin", "activate")
if not os.path.exists(_venv_activate):
    print(
        f"error: FUZZ_FILL_VENV_DIR does not contain bin/activate: {_venv_activate!r}",
        file=sys.stderr,
    )
    raise SystemExit(1)

def _tool(name: str) -> str:
    return shlex.quote(os.path.join(_sancov_bin, name))


_llvm_build_dir = os.path.dirname(_sancov_bin)
_venv_cmd = f". {shlex.quote(_venv_activate)}"

config.name = "fuzz-fill-integration-tests"
config.suffixes = [".test"]
config.test_format = lit.formats.ShTest(execute_external=True)
config.environment["VIRTUAL_ENV"] = _venv_dir
config.substitutions.extend(
    [
        ("%sancov-llc", _tool("llc")),
        ("%sancov-opt", _tool("opt")),
        ("%clang", _tool("clang")),
        ("%llvm-build-dir", shlex.quote(_llvm_build_dir)),
        ("%venv", _venv_cmd),
        ("%coverage", f"{_venv_cmd} && python -m coverage"),
        ("%reduce", f"{_venv_cmd} && python -m reduce"),
    ]
)
