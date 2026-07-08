# -*- Python -*-
"""llvm-lit configuration for fuzz-fill integration tests."""

import os
import shlex
import sys

import lit.formats

def _require_dir(env_var: str, human_label: str) -> str:
    raw = os.environ.get(env_var)
    if not raw:
        print(
            f"error: {env_var} must be set ({human_label})",
            file=sys.stderr,
        )
        raise SystemExit(1)
    path = os.path.abspath(os.path.expanduser(raw))
    if not os.path.exists(path):
        print(
            f"error: {env_var} does not exist: {path!r}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if not os.path.isdir(path):
        print(
            f"error: {env_var} must be a directory, not a file: {path!r}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return path


_llvm_bin_dir = _require_dir(
    "FUZZ_FILL_LLVM_BIN_DIR",
    "LLVM build bin directory (FileCheck, sancov)",
)
_llvm_sancov_bin_dir = _require_dir(
    "FUZZ_FILL_LLVM_SANCOV_BIN_DIR",
    "SanitizerCoverage-instrumented LLVM build bin directory (llc, opt)",
)
_llvm_src_dir = _require_dir(
    "FUZZ_FILL_LLVM_SRC_DIR",
    "llvm-project checkout root (directory containing llvm/)",
)
if not os.path.isdir(os.path.join(_llvm_src_dir, "llvm")):
    print(
        f"error: FUZZ_FILL_LLVM_SRC_DIR must contain llvm/: {_llvm_src_dir!r}",
        file=sys.stderr,
    )
    raise SystemExit(1)
_venv_dir = os.environ.get("FUZZ_FILL_VENV_DIR")
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

def _tool(bin_dir: str, name: str) -> str:
    return shlex.quote(os.path.join(bin_dir, name))


_llvm_build_dir = os.path.dirname(_llvm_bin_dir)
_venv_cmd = f". {shlex.quote(_venv_activate)}"
_venv_python = shlex.quote(os.path.join(_venv_dir, "bin", "python"))

config.name = "fuzz-fill-integration-tests"
config.suffixes = [".test"]
config.test_format = lit.formats.ShTest(execute_external=True)
config.environment["VIRTUAL_ENV"] = _venv_dir
config.substitutions.extend(
    [
        ("%sancov-llc", _tool(_llvm_sancov_bin_dir, "llc")),
        ("%sancov-opt", _tool(_llvm_sancov_bin_dir, "opt")),
        ("%sancov", _tool(_llvm_bin_dir, "sancov")),
        ("%llvm-lit", _tool(_llvm_sancov_bin_dir, "llvm-lit")),
        ("%FileCheck", _tool(_llvm_bin_dir, "FileCheck")),
        ("%llvm-build-dir", shlex.quote(_llvm_build_dir)),
        ("%llvm-repo", shlex.quote(_llvm_src_dir)),
        ("%venv", _venv_cmd),
        ("%coverage", f"{_venv_python} -m coverage"),
        ("%reduce", f"{_venv_python} -m reduce"),
    ]
)
