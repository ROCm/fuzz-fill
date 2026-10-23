# -*- Python -*-
"""llvm-lit configuration for fuzz-fill integration tests."""

import os
import shlex
import sys

import lit.formats

# lit.cfg.py is executed with this directory as the config root; import helpers.
sys.path.insert(0, os.path.dirname(__file__))
import lit_common  # noqa: E402

_llvm_bin_dir = lit_common.require_dir(
    "FUZZ_FILL_LLVM_BIN_DIR",
    "LLVM build bin directory (FileCheck, sancov)",
)
_llvm_sancov_bin_dir = lit_common.require_dir(
    "FUZZ_FILL_LLVM_SANCOV_BIN_DIR",
    "SanitizerCoverage-instrumented LLVM build bin directory (llc, opt)",
)
_llvm_src_dir = lit_common.require_llvm_src_dir()
_venv_dir = lit_common.require_venv_dir()

_llvm_build_dir = os.path.dirname(_llvm_bin_dir)
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

config.name = "fuzz-fill-integration-tests"
config.suffixes = [".test"]
config.test_format = lit.formats.ShTest()
lit_common.apply_venv_environment(config, _venv_dir)
config.substitutions.extend(
    [
        ("%sancov-llc", lit_common.tool(_llvm_sancov_bin_dir, "llc")),
        ("%sancov-opt", lit_common.tool(_llvm_sancov_bin_dir, "opt")),
        ("%llvm-reduce", lit_common.tool(_llvm_sancov_bin_dir, "llvm-reduce")),
        ("%llvm-dis", lit_common.tool(_llvm_sancov_bin_dir, "llvm-dis")),
        ("%llvm-sancov-bin", shlex.quote(_llvm_sancov_bin_dir)),
        ("%sancov", lit_common.tool(_llvm_bin_dir, "sancov")),
        ("%llvm-lit", lit_common.tool(_llvm_sancov_bin_dir, "llvm-lit")),
        ("%FileCheck", lit_common.tool(_llvm_bin_dir, "FileCheck")),
        ("%not", lit_common.tool(_llvm_bin_dir, "not")),
        ("%llvm-build-dir", shlex.quote(_llvm_build_dir)),
        ("%llvm-repo", shlex.quote(_llvm_src_dir)),
        ("%repo-root", shlex.quote(_repo_root)),
    ]
)
config.substitutions.extend(lit_common.venv_module_substitutions(_venv_dir))

# Clang lit tests need an instrumented build configured with LLVM_ENABLE_PROJECTS=clang.
# The AMDGPU allowlist does not instrument clang/lib; the suite only has to exist.
_clang_lit_site = os.path.join(
    os.path.dirname(_llvm_sancov_bin_dir),
    "tools",
    "clang",
    "test",
    "lit.site.cfg.py",
)
if os.path.isfile(_clang_lit_site):
    config.available_features.add("clang-lit")
    config.substitutions.append(("%clang-lit-site", shlex.quote(_clang_lit_site)))

lit_common.apply_gh_token_feature(config)
