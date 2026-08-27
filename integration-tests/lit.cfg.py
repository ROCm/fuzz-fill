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
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_venv_cmd = f". {shlex.quote(_venv_activate)}"
_venv_python = shlex.quote(os.path.join(_venv_dir, "bin", "python"))

config.name = "fuzz-fill-integration-tests"
config.suffixes = [".test"]
config.test_format = lit.formats.ShTest()
config.environment["VIRTUAL_ENV"] = _venv_dir
config.environment["FUZZ_FILL_VENV_DIR"] = _venv_dir
config.substitutions.extend(
    [
        ("%sancov-llc", _tool(_llvm_sancov_bin_dir, "llc")),
        ("%sancov-opt", _tool(_llvm_sancov_bin_dir, "opt")),
        ("%llvm-reduce", _tool(_llvm_sancov_bin_dir, "llvm-reduce")),
        ("%llvm-dis", _tool(_llvm_sancov_bin_dir, "llvm-dis")),
        ("%llvm-sancov-bin", shlex.quote(_llvm_sancov_bin_dir)),
        ("%sancov", _tool(_llvm_bin_dir, "sancov")),
        ("%llvm-lit", _tool(_llvm_sancov_bin_dir, "llvm-lit")),
        ("%FileCheck", _tool(_llvm_bin_dir, "FileCheck")),
        ("%not", _tool(_llvm_bin_dir, "not")),
        ("%llvm-build-dir", shlex.quote(_llvm_build_dir)),
        ("%llvm-repo", shlex.quote(_llvm_src_dir)),
        ("%repo-root", shlex.quote(_repo_root)),
        ("%venv", _venv_cmd),
        ("%coverage", f"{_venv_python} -m coverage"),
        ("%reduce", f"{_venv_python} -m reduce"),
        ("%added-lines", f"{_venv_python} -m added_lines"),
        ("%gap-pruner", f"{_venv_python} -m gap_pruner"),
    ]
)

# E2E tests are opt-in: pass --param e2e=1 to enable them.
if lit_config.params.get("e2e"):
    config.available_features.add("e2e")
    _e2e_bootstrap = os.environ.get("FUZZ_FILL_E2E_BOOTSTRAP_BIN")
    if _e2e_bootstrap and os.path.isfile(
        os.path.join(os.path.abspath(os.path.expanduser(_e2e_bootstrap)), "clang")
    ):
        _e2e_bootstrap = os.path.abspath(os.path.expanduser(_e2e_bootstrap))
        config.available_features.add("e2e-bootstrap")
        config.environment["FUZZ_FILL_E2E_BOOTSTRAP_BIN"] = _e2e_bootstrap
        config.substitutions.append(
            ("%e2e-bootstrap-bin", shlex.quote(_e2e_bootstrap))
        )

    # E2e PR prepare: CI sets FUZZ_FILL_E2E_LLVM_MIRROR to a cached filtered
    # llvm-project git mirror; local runs leave it unset and use plain-clone.
    _e2e_mirror = os.environ.get("FUZZ_FILL_E2E_LLVM_MIRROR")
    if _e2e_mirror:
        _e2e_mirror = os.path.abspath(os.path.expanduser(_e2e_mirror))
        if os.path.isdir(os.path.join(_e2e_mirror, "llvm")):
            config.available_features.add("e2e-llvm-mirror")
            config.environment["FUZZ_FILL_E2E_LLVM_MIRROR"] = _e2e_mirror
            config.substitutions.append(
                ("%e2e-llvm-mirror", shlex.quote(_e2e_mirror))
            )
        else:
            config.available_features.add("e2e-no-llvm-mirror")
    else:
        config.available_features.add("e2e-no-llvm-mirror")

# PR prepare uses gh api; tests that clone by PR id require GH_TOKEN (e.g. CI:
# GH_TOKEN: ${{ github.token }}).
_gh_token = os.environ.get("GH_TOKEN")
if _gh_token:
    config.available_features.add("gh-token")
    config.environment["GH_TOKEN"] = _gh_token
