from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reduce.reducer import ReducePass


def _pass_by_id() -> dict[str, type[ReducePass]]:
    """Built lazily so ``reducer`` can import this module without a cycle."""
    from reduce import reducer as r

    return {
        "snapshot": r.SnapshotPass,
        "llvm_reduce_ir": r.LlvmReduceIrPass,
        "llvm_reduce_mir": r.LlvmReduceMirPass,
        "extract_mir_before_pass": r.ExtractMirBeforePass,
        "extract_ir_after_pass": r.ExtractIrAfterPass,
    }


def known_pass_ids() -> frozenset[str]:
    """Ids valid in JSON ``pipeline`` and ``--only-pass``."""
    return frozenset(_pass_by_id())


def passes_from_ids(pass_ids: list[str]) -> list[ReducePass]:
    reg = _pass_by_id()
    out: list[ReducePass] = []
    for pid in pass_ids:
        cls = reg.get(pid)
        if cls is None:
            known = ", ".join(sorted(reg))
            raise SystemExit(f"Unknown pass id {pid!r}. Known ids: {known}")
        out.append(cls())
    return out
