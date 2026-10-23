# -*- Python -*-
"""llvm-lit configuration for fuzz-fill e2e integration tests."""

import os
import shlex
import sys

import lit.formats

_integration_tests_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _integration_tests_dir)
import lit_common  # noqa: E402

_llvm_bin_dir = lit_common.require_dir(
    "FUZZ_FILL_LLVM_BIN_DIR",
    "LLVM build bin directory (FileCheck)",
)
_llvm_src_dir = lit_common.require_llvm_src_dir()
_venv_dir = lit_common.require_venv_dir()

_repo_root = os.path.abspath(os.path.join(_integration_tests_dir, ".."))

config.name = "fuzz-fill-e2e-tests"
config.suffixes = [".test"]
config.test_format = lit.formats.ShTest()
lit_common.apply_venv_environment(config, _venv_dir)
config.substitutions.extend(
    [
        ("%FileCheck", lit_common.tool(_llvm_bin_dir, "FileCheck")),
        ("%llvm-repo", shlex.quote(_llvm_src_dir)),
        ("%repo-root", shlex.quote(_repo_root)),
    ]
)
config.substitutions.extend(lit_common.venv_module_substitutions(_venv_dir))

# E2E tests are opt-in: pass --param e2e=1 to enable them.
if lit_config.params.get("e2e"):
    lit_common.require_git_checkout(_llvm_src_dir)
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

lit_common.apply_gh_token_feature(config)
