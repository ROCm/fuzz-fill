"""Run the test command with UBSAN SanitizerCoverage env."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from coverage.stage_log import stage_line


def display_path_for_log(path: Path) -> str:
    """Best-effort path relative to cwd for terminal messages."""
    try:
        return path.resolve().relative_to(Path.cwd()).as_posix()
    except ValueError:
        return str(path)


def ubsan_environ_with_coverage(coverage_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    cov_opts = f"coverage=1:coverage_dir={coverage_dir}"
    prev = env.get("UBSAN_OPTIONS", "").strip()
    env["UBSAN_OPTIONS"] = f"{cov_opts}:{prev}" if prev else cov_opts
    return env


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
        env = ubsan_environ_with_coverage(coverage_dir)
        cov_opts_display = f"coverage=1:coverage_dir={display_path_for_log(coverage_dir)}"
        prev_raw = os.environ.get("UBSAN_OPTIONS", "").strip()
        ubsan_display = f"{cov_opts_display}:{prev_raw}" if prev_raw else cov_opts_display
        stage_line(
            "tests",
            f"Running: UBSAN_OPTIONS={ubsan_display!r} "
            f"{' '.join(shlex.quote(x) for x in cmd)} (cwd={display_path_for_log(cwd)})",
        )
        result = subprocess.run(cmd, cwd=cwd, env=env)
        return result.returncode

    def run_argv(
        self,
        argv: list[str],
        cwd: Path,
        coverage_dir: Path,
        *,
        log_per_test: bool = False,
    ) -> int:
        if not argv:
            raise ValueError("empty argv")
        env = ubsan_environ_with_coverage(coverage_dir)
        if log_per_test:
            stage_line("test", "Running llc for test")
        else:
            cov_opts_display = f"coverage=1:coverage_dir={display_path_for_log(coverage_dir)}"
            prev_raw = os.environ.get("UBSAN_OPTIONS", "").strip()
            ubsan_display = f"{cov_opts_display}:{prev_raw}" if prev_raw else cov_opts_display
            stage_line(
                "tests",
                f"Running: UBSAN_OPTIONS={ubsan_display!r} "
                f"{' '.join(shlex.quote(x) for x in argv)} (cwd={display_path_for_log(cwd)})",
            )
        result = subprocess.run(argv, cwd=cwd, env=env)
        return result.returncode
