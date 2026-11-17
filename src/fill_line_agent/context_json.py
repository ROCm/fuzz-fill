# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Write/read fill-line context.json (filepath fields only; never secrets)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ALLOWED_KEYS = frozenset(
    {
        "llvm_src",
        "diff",
        "instrumented_bin_dir",
        "tools_runner",
        "tools_image",
    }
)


def write_context_json(
    out_dir: Path,
    *,
    llvm_src: Path,
    diff: Path,
    instrumented_bin_dir: Path,
    tools_runner: str | None = None,
    tools_image: str | None = None,
) -> Path:
    """Write filepath-only context for usher-test. Never write secrets."""
    payload: dict[str, Any] = {
        "llvm_src": str(llvm_src.resolve()),
        "diff": str(diff.resolve()),
        "instrumented_bin_dir": str(instrumented_bin_dir.resolve()),
    }
    if tools_runner:
        payload["tools_runner"] = tools_runner
    if tools_image:
        # Image name/tag only — not a secret registry credential.
        payload["tools_image"] = tools_image
    path = out_dir / "context.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def read_context_json(path: Path) -> dict[str, Any]:
    """Load context.json, dropping unknown / forbidden keys."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("context.json must be an object")
    forbidden = {
        "api_key",
        "base_url",
        "user_ntid",
        "key",
        "token",
        "password",
        "secret",
    }
    out: dict[str, Any] = {}
    for key, value in raw.items():
        low = str(key).lower()
        if low in forbidden or any(f in low for f in ("key", "token", "secret", "password")):
            continue
        if key not in ALLOWED_KEYS:
            continue
        out[key] = value
    return out
