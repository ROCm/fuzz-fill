"""Run the test command with UBSAN SanitizerCoverage env."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


class TestCommandRunner:
    """Execute a shell-style command with ``coverage_dir`` wired into UBSAN_OPTIONS."""

    def run(
        self,
        command: str,
        cwd: Path,
        coverage_dir: Path,
    ) -> int:
        cmd = shlex.split(command)
        if not cmd:
            raise ValueError("empty command after shlex.split")
        env = os.environ.copy()
        cov_opts = f"coverage=1:coverage_dir={coverage_dir}"
        prev = env.get("UBSAN_OPTIONS", "").strip()
        env["UBSAN_OPTIONS"] = f"{cov_opts}:{prev}" if prev else cov_opts
        print(
            f"Running: UBSAN_OPTIONS={env['UBSAN_OPTIONS']!r} "
            f"{' '.join(shlex.quote(x) for x in cmd)} (cwd={cwd})"
        )
        result = subprocess.run(cmd, cwd=cwd, env=env)
        print(f"Exit code: {result.returncode}")
        return result.returncode
