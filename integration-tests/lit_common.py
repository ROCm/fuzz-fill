# -*- Python -*-
"""Shared helpers for fuzz-fill lit.cfg.py suites."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys


def require_dir(env_var: str, human_label: str) -> str:
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


def require_llvm_src_dir() -> str:
    llvm_src_dir = require_dir(
        "FUZZ_FILL_LLVM_SRC_DIR",
        "llvm-project checkout root (directory containing llvm/)",
    )
    if not os.path.isdir(os.path.join(llvm_src_dir, "llvm")):
        print(
            f"error: FUZZ_FILL_LLVM_SRC_DIR must contain llvm/: {llvm_src_dir!r}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return llvm_src_dir


def require_venv_dir() -> str:
    venv_dir = os.environ.get("FUZZ_FILL_VENV_DIR")
    if not venv_dir:
        print(
            "error: FUZZ_FILL_VENV_DIR must be set to a Python virtualenv directory",
            file=sys.stderr,
        )
        raise SystemExit(1)
    venv_dir = os.path.abspath(os.path.expanduser(venv_dir))
    if not os.path.exists(venv_dir):
        print(
            f"error: FUZZ_FILL_VENV_DIR does not exist: {venv_dir!r}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if not os.path.isdir(venv_dir):
        print(
            f"error: FUZZ_FILL_VENV_DIR must be a directory, not a file: {venv_dir!r}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    venv_activate = os.path.join(venv_dir, "bin", "activate")
    if not os.path.exists(venv_activate):
        print(
            f"error: FUZZ_FILL_VENV_DIR does not contain bin/activate: {venv_activate!r}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return venv_dir


def require_git_checkout(path: str, env_var: str = "FUZZ_FILL_LLVM_SRC_DIR") -> None:
    result = subprocess.run(
        ["git", "-C", path, "rev-parse", "--git-dir"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        print(
            f"error: {env_var} must be a git checkout when e2e=1: {path!r}",
            file=sys.stderr,
        )
        raise SystemExit(1)


def tool(bin_dir: str, name: str) -> str:
    return shlex.quote(os.path.join(bin_dir, name))


def apply_venv_environment(config, venv_dir: str) -> None:
    config.environment["VIRTUAL_ENV"] = venv_dir
    config.environment["FUZZ_FILL_VENV_DIR"] = venv_dir


def venv_module_substitutions(venv_dir: str) -> list[tuple[str, str]]:
    venv_activate = os.path.join(venv_dir, "bin", "activate")
    venv_cmd = f". {shlex.quote(venv_activate)}"
    venv_python = shlex.quote(os.path.join(venv_dir, "bin", "python"))
    return [
        ("%venv", venv_cmd),
        ("%coverage", f"{venv_python} -m coverage"),
        ("%reduce", f"{venv_python} -m reduce"),
        ("%added-lines", f"{venv_python} -m added_lines"),
        ("%gap-pruner", f"{venv_python} -m gap_pruner"),
        ("%gap-scope", f"{venv_python} -m gap_scope"),
    ]


def apply_gh_token_feature(config) -> None:
    # PR prepare uses gh api; tests that clone by PR id require GH_TOKEN
    # (e.g. CI: GH_TOKEN: ${{ github.token }}).
    gh_token = os.environ.get("GH_TOKEN")
    if gh_token:
        config.available_features.add("gh-token")
        config.environment["GH_TOKEN"] = gh_token
