# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Run instrumented opt/llc/sancov on the host or inside a Docker image.

The agent never sees this choice. CLI/env select host vs docker; paths are
bind-mounted at the same absolute locations so commands stay unchanged.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from fuzz_fill.log import get_logger

logger = get_logger("fill_line_agent.runner")

RunnerMode = Literal["host", "docker"]
DEFAULT_IMAGE = "fuzz-fill-instrumented-tools:ubuntu24.04"
ENV_MODE = "FUZZ_FILL_TOOLS_RUNNER"
ENV_IMAGE = "FUZZ_FILL_TOOLS_IMAGE"


@dataclass(frozen=True)
class ToolRunner:
    """Opaque process runner for instrumented LLVM tools."""

    mode: RunnerMode = "host"
    image: str = DEFAULT_IMAGE
    docker_bin: str = "docker"

    @classmethod
    def from_cli(
        cls,
        *,
        mode: str | None = None,
        image: str | None = None,
    ) -> ToolRunner:
        resolved = (mode or os.environ.get(ENV_MODE) or "host").strip().lower()
        if resolved not in ("host", "docker"):
            raise SystemExit(f"tools runner must be host or docker, got {resolved!r}")
        img = (image or os.environ.get(ENV_IMAGE) or DEFAULT_IMAGE).strip()
        return cls(mode=resolved, image=img)  # type: ignore[arg-type]

    def host_callable_tool(
        self,
        real_tool: Path,
        *,
        shim_dir: Path,
        bind_paths: Sequence[Path] = (),
    ) -> Path:
        """Return a host path that runs *real_tool* via this runner.

        Host mode returns *real_tool*. Docker mode writes a small bash shim
        under *shim_dir* so host-side helpers (e.g. ``update_*_test_checks.py``)
        can still invoke instrumented ``llc``/``opt`` without needing a new
        enough host glibc.
        """
        real = real_tool.expanduser().resolve()
        if self.mode == "host":
            return real
        shim_dir = shim_dir.expanduser().resolve()
        shim_dir.mkdir(parents=True, exist_ok=True)
        shim = shim_dir / f"{real.name}.docker-shim"
        fixed_mounts: list[str] = [str(real.parent)]
        for path in bind_paths:
            resolved = path.expanduser().resolve()
            if resolved.is_file():
                resolved = resolved.parent
            fixed_mounts.append(str(resolved))
        # Unique while preserving order.
        seen: set[str] = set()
        mounts: list[str] = []
        for mount in fixed_mounts:
            if mount not in seen:
                seen.add(mount)
                mounts.append(mount)
        # Paths are absolute; quote for the generated bash script.
        mounts_lit = " ".join(shlex.quote(m) for m in mounts)
        script = f"""#!/usr/bin/env bash
set -euo pipefail
REAL={shlex.quote(str(real))}
IMAGE={shlex.quote(self.image)}
DOCKER_BIN={shlex.quote(self.docker_bin)}
FIXED_MOUNTS=({mounts_lit})
uid="$(id -u)"
gid="$(id -g)"
cmd=("$DOCKER_BIN" run --rm -i --network=none --user "${{uid}}:${{gid}}")
declare -A seen_mounts=()
add_mount() {{
  local d="$1"
  [[ -n "${{seen_mounts[$d]:-}}" ]] && return
  seen_mounts[$d]=1
  cmd+=(-v "${{d}}:${{d}}")
}}
for d in "${{FIXED_MOUNTS[@]}}"; do
  add_mount "$d"
done
for arg in "$@"; do
  if [[ -e "$arg" ]]; then
    if [[ -d "$arg" ]]; then
      add_mount "$(cd -- "$arg" && pwd)"
    else
      add_mount "$(cd -- "$(dirname -- "$arg")" && pwd)"
    fi
  fi
done
cmd+=("$IMAGE" "$REAL" "$@")
exec "${{cmd[@]}}"
"""
        shim.write_text(script, encoding="utf-8")
        shim.chmod(0o755)
        return shim

    def run(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        timeout_s: float | None = None,
        bind_paths: Sequence[Path] = (),
        check: bool = False,
        input: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if not argv:
            raise ValueError("argv must be non-empty")
        label = f"{self.mode}:{' '.join(str(a) for a in argv[:3])}"
        logger.info("exec start: %s", label)
        start = time.perf_counter()
        try:
            if self.mode == "host":
                return subprocess.run(
                    list(argv),
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                    env=dict(env) if env is not None else None,
                    check=check,
                    input=input,
                )
            return self._run_docker(
                argv,
                env=env,
                timeout_s=timeout_s,
                bind_paths=bind_paths,
                check=check,
                input=input,
            )
        finally:
            logger.info("exec done:  %s in %.2fs", label, time.perf_counter() - start)

    def _run_docker(
        self,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None,
        timeout_s: float | None,
        bind_paths: Sequence[Path],
        check: bool,
        input: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if shutil.which(self.docker_bin) is None:
            raise RuntimeError(f"{self.docker_bin} not found on PATH")

        cmd = [
            self.docker_bin,
            "run",
            "--rm",
            "--network=none",
            "-i",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
        ]
        # Same absolute paths inside the container as on the host.
        mounts: list[Path] = []
        for path in bind_paths:
            resolved = path.expanduser().resolve()
            if resolved.is_file():
                resolved = resolved.parent
            mounts.append(resolved)
        # Always mount the executable's parent directory.
        exe = Path(argv[0]).expanduser().resolve()
        mounts.append(exe.parent)
        seen: set[str] = set()
        for mount in mounts:
            key = str(mount)
            if key in seen:
                continue
            seen.add(key)
            cmd.extend(["-v", f"{key}:{key}"])

        if env:
            for key, value in env.items():
                # Keep the job small: only forward coverage-related vars plus PATH.
                if key in ("UBSAN_OPTIONS", "ASAN_OPTIONS", "PATH", "HOME", "TMPDIR"):
                    cmd.extend(["-e", f"{key}={value}"])

        cmd.append(self.image)
        cmd.extend(str(a) for a in argv)
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=check,
            input=input,
        )
