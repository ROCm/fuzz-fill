#!/usr/bin/env python3
# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Generate an SBOM for fuzz-fill using the pinned trivy release.

Downloads and caches the same trivy version used in CI when a local
binary is unavailable. Writes the SBOM plus a small metadata sidecar
for audit trails.

Examples:
  ./scripts/compile-requirements.sh && ./scripts/generate-sbom.py
  ./scripts/generate-sbom.py --format cyclonedx --output sbom/cyclonedx.json
  ./scripts/generate-sbom.py --image fuzz-fill-test:latest
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_TRIVY_RUNNER_PATH = _SCRIPT_DIR / "github_actions" / "scan_tools" / "trivy.py"
_CONFIG_PATH = _REPO_ROOT / "trivy.yaml"
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "sbom"
_SUPPORTED_FORMATS: dict[str, str] = {
    "cyclonedx": "cdx.json",
    "spdx-json": "spdx.json",
}
# Large vendored trees are not fuzz-fill runtime dependencies.
_DEFAULT_SKIP_DIRS: tuple[str, ...] = (
    "llvm-project",
    ".llvm-docker-staging",
    ".fuzz-fill-llvm-pr-worktrees",
    "venv*",
    "**/venv*",
)


def _load_trivy_runner():
    spec = importlib.util.spec_from_file_location(
        "fuzz_fill_trivy_runner", _TRIVY_RUNNER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load trivy runner from {_TRIVY_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git_sha(repo_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    sha = completed.stdout.strip()
    return sha or None


def _default_output_path(fmt: str, repo_root: Path) -> Path:
    ext = _SUPPORTED_FORMATS[fmt]
    sha = _git_sha(repo_root)
    suffix = sha[:12] if sha else datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return _DEFAULT_OUTPUT_DIR / f"fuzz-fill-{suffix}.{ext}"


def _resolve_config_path() -> Path:
    if not _CONFIG_PATH.is_file():
        raise FileNotFoundError(
            f"trivy config not found at '{_CONFIG_PATH}'. Run from the repo root."
        )
    return _CONFIG_PATH


def _trivy_version(binary: Path, env: dict[str, str]) -> str:
    completed = subprocess.run(
        [str(binary), "--version"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    first_line = completed.stdout.strip().splitlines()
    return first_line[0] if first_line else "trivy"


def _run_trivy_sbom(
    binary: Path,
    *,
    config_path: Path,
    scan_type: str,
    scan_target: str,
    output: Path,
    fmt: str,
    scanners: list[str],
    skip_dirs: list[str],
    subprocess_env: dict[str, str],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd: list[str] = [
        str(binary),
        scan_type,
        "--config",
        str(config_path),
        "--format",
        fmt,
        "--output",
        str(output),
        "--exit-code",
        "0",
        "--quiet",
    ]
    if scanners:
        cmd.extend(["--scanners", ",".join(scanners)])
    for skip_dir in skip_dirs:
        cmd.extend(["--skip-dirs", skip_dir])
    cmd.append(scan_target)

    log.info("Running: %s", " ".join(cmd))
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            env=subprocess_env,
        )
    except OSError as exc:
        raise RuntimeError(f"trivy failed to start: {exc}") from exc
    if completed.returncode != 0:
        raise RuntimeError(
            "trivy exited unexpectedly "
            f"(code {completed.returncode}); stderr: "
            f"{completed.stderr.strip() if completed.stderr else '<empty>'}"
        )


def _sbom_base_name(sbom_path: Path) -> str:
    name = sbom_path.name
    if name.endswith(".cdx.json"):
        return name[: -len(".cdx.json")]
    if name.endswith(".spdx.json"):
        return name[: -len(".spdx.json")]
    return sbom_path.stem


def _meta_path_for(sbom_path: Path) -> Path:
    return sbom_path.parent / f"{_sbom_base_name(sbom_path)}.meta.json"


def _requirements_path_for(sbom_path: Path) -> Path:
    return sbom_path.parent / f"{_sbom_base_name(sbom_path)}.requirements.txt"


def _stage_requirements_lockfile(
    sbom_path: Path,
) -> Path | None:
    """Copy repo-root requirements.txt beside the SBOM for audit bundles."""
    source = _REPO_ROOT / "requirements.txt"
    if not source.is_file():
        log.warning(
            "requirements.txt not found at repo root; run ./scripts/compile-requirements.sh "
            "first for a pinned Python dependency lockfile in the SBOM bundle"
        )
        return None

    dest = _requirements_path_for(sbom_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    log.info("Staged requirements lockfile: %s", dest)
    return dest


def _relative_to_repo(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(_REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def _write_metadata(
    meta_path: Path,
    *,
    sbom_path: Path,
    fmt: str,
    scanners: list[str],
    scan_target: str,
    trivy_version: str,
    git_sha: str | None,
    requirements_path: Path | None = None,
) -> None:
    meta = {
        "project": "fuzz-fill",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha,
        "sbom_format": fmt,
        "sbom_path": _relative_to_repo(sbom_path),
        "scanners": scanners,
        "scan_target": scan_target,
        "trivy_version": trivy_version,
    }
    if requirements_path is not None:
        meta["requirements_path"] = _relative_to_repo(requirements_path)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    log.info("Wrote metadata: %s", meta_path)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--format",
        choices=sorted(_SUPPORTED_FORMATS),
        default="spdx-json",
        help="SBOM output format (default: spdx-json)",
    )
    p.add_argument(
        "--output",
        type=Path,
        help=(
            "SBOM output path (default: sbom/fuzz-fill-<git-sha>.<ext> "
            "under the repo root)"
        ),
    )
    p.add_argument(
        "--source-dir",
        type=Path,
        default=_REPO_ROOT,
        help="Repository path to scan (default: repo root)",
    )
    p.add_argument(
        "--image",
        help=(
            "Generate an SBOM for a Docker image (e.g. fuzz-fill-test:latest) "
            "instead of the repository filesystem"
        ),
    )
    p.add_argument(
        "--with-vulns",
        action="store_true",
        help="Include vulnerability findings in the SBOM (adds the vuln scanner)",
    )
    p.add_argument(
        "--skip-dir",
        action="append",
        default=[],
        dest="extra_skip_dirs",
        help="Additional directory names to skip (repeatable)",
    )
    p.add_argument(
        "--no-default-skips",
        action="store_true",
        help="Do not skip vendored llvm-project trees by default",
    )
    return p


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    args = build_parser().parse_args(argv)

    try:
        config_path = _resolve_config_path()
        trivy_runner = _load_trivy_runner()
        binary = trivy_runner._ensure_trivy()
        subprocess_env = trivy_runner._trivy_subprocess_env()
    except (FileNotFoundError, RuntimeError) as exc:
        log.error("%s", exc)
        return 2

    output = args.output or _default_output_path(args.format, _REPO_ROOT)
    if output.is_dir():
        output = output / _default_output_path(args.format, _REPO_ROOT).name

    scanners = ["license"]
    if args.with_vulns:
        scanners.append("vuln")

    skip_dirs = [] if args.no_default_skips else list(_DEFAULT_SKIP_DIRS)
    skip_dirs.extend(args.extra_skip_dirs)

    source_dir = args.source_dir.resolve()
    if not source_dir.is_dir():
        log.error("source path '%s' does not exist or is not a directory", source_dir)
        return 2

    scan_target = args.image if args.image else str(source_dir)
    git_sha = _git_sha(_REPO_ROOT)

    try:
        _run_trivy_sbom(
            binary,
            config_path=config_path,
            scan_type="image" if args.image else "fs",
            scan_target=scan_target,
            output=output,
            fmt=args.format,
            scanners=scanners,
            skip_dirs=[] if args.image else skip_dirs,
            subprocess_env=subprocess_env,
        )
        trivy_ver = _trivy_version(binary, subprocess_env)
        requirements_path = None
        if not args.image:
            requirements_path = _stage_requirements_lockfile(output)
        meta_path = _meta_path_for(output)
        _write_metadata(
            meta_path,
            sbom_path=output,
            fmt=args.format,
            scanners=scanners,
            scan_target=_relative_to_repo(Path(scan_target)),
            trivy_version=trivy_ver,
            git_sha=git_sha,
            requirements_path=requirements_path,
        )
    except RuntimeError as exc:
        log.error("%s", exc)
        return 2

    log.info("SBOM written to %s", output)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
