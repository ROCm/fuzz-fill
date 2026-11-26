from __future__ import annotations

from pathlib import Path


def canonicalize_source_path(raw: str | Path, llvm_src: Path) -> str | None:
    path = Path(raw)
    if not path.is_absolute():
        path = llvm_src / path

    p = path.resolve()
    root = llvm_src.resolve()
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return None
