"""Build and validate config.json pipeline steps for batch reduction."""

from __future__ import annotations

from pathlib import Path

from reduce.batch.templates import mir_template_basename
from reduce.pass_registry import known_pass_ids

_PASSES_NEEDING_EXTRACT_OPTS = frozenset(
    {"extract_mir_before_pass", "extract_ir_before_pass"}
)
_PASSES_NEEDING_INTERESTING_MIR = frozenset({"llvm_reduce_mir"})


def parse_pipeline_arg(value: str) -> list[str]:
    ids = [p.strip() for p in value.split(",") if p.strip()]
    if not ids:
        raise ValueError("--pipeline must list at least one pass id.")
    known = known_pass_ids()
    bad = [p for p in ids if p not in known]
    if bad:
        raise ValueError(
            f"Unknown pipeline pass id(s): {', '.join(bad)}. "
            f"Known ids: {', '.join(sorted(known))}."
        )
    return ids


def creduce_interesting_script(pass_ids: list[str], creduce_index: int) -> str:
    """Interesting script for creduce: match the artifact produced by the prior step."""
    if creduce_index <= 0:
        return "interesting_ir.sh"
    prev = pass_ids[creduce_index - 1]
    if prev == "llvm_reduce_mir":
        return "interesting_mir.sh"
    return "interesting_ir.sh"


def build_pipeline_steps(
    pass_ids: list[str],
    *,
    pass_under_test: str | None,
    mtriple: str | None,
    llc_flags: tuple[str, ...],
    extract_mir_output: str | None,
    extract_ir_output: str | None,
    creduce_n: int | None,
) -> list[dict]:
    steps: list[dict] = []
    llc_O = " ".join(llc_flags)
    for i, pid in enumerate(pass_ids):
        if pid == "llvm_reduce_ir":
            steps.append(
                {
                    "id": "llvm_reduce_ir",
                    "parameters": {"interesting": "interesting_ir.sh"},
                }
            )
        elif pid == "llvm_reduce_mir":
            steps.append(
                {
                    "id": "llvm_reduce_mir",
                    "parameters": {"interesting_mir": "interesting_mir.sh"},
                }
            )
        elif pid == "extract_mir_before_pass":
            params: dict[str, str] = {
                "pass_under_test": pass_under_test or "",
                "mtriple": mtriple or "",
                "llc_O": llc_O,
            }
            if extract_mir_output:
                params["extract_mir_output"] = extract_mir_output
            steps.append({"id": pid, "parameters": params})
        elif pid == "extract_ir_before_pass":
            params = {
                "pass_under_test": pass_under_test or "",
                "mtriple": mtriple or "",
                "llc_O": llc_O,
            }
            if extract_ir_output:
                params["extract_ir_before_output"] = extract_ir_output
            steps.append({"id": pid, "parameters": params})
        elif pid == "creduce":
            params: dict[str, str | int] = {
                "interesting": creduce_interesting_script(pass_ids, i),
            }
            if creduce_n is not None:
                params["n"] = creduce_n
            steps.append({"id": "creduce", "parameters": params})
        elif pid == "snapshot":
            steps.append({"id": "snapshot"})
        else:
            raise ValueError(f"Unhandled pass id: {pid}")
    return steps


def validate_pipeline_cli(
    pass_ids: list[str],
    *,
    pass_under_test: str | None,
    mtriple: str | None,
    template_dir: Path,
    mir_codegen_only: bool,
) -> None:
    needs_extract = _PASSES_NEEDING_EXTRACT_OPTS & set(pass_ids)
    if needs_extract:
        if not pass_under_test:
            raise ValueError(
                f"--pass-under-test is required when the pipeline includes "
                f"{', '.join(sorted(needs_extract))}."
            )
        if not mtriple:
            raise ValueError(
                f"--mtriple is required when the pipeline includes "
                f"{', '.join(sorted(needs_extract))}."
            )
    if _PASSES_NEEDING_INTERESTING_MIR & set(pass_ids):
        if not pass_under_test:
            raise ValueError(
                "--pass-under-test is required when the pipeline includes llvm_reduce_mir."
            )
        mir_name = mir_template_basename(mir_codegen_only=mir_codegen_only)
        mir_template = template_dir / mir_name
        if not mir_template.is_file():
            raise ValueError(
                f"Pipeline includes llvm_reduce_mir but {mir_template} is missing. "
                f"Use --template-dir with {mir_name} (e.g. example/amd/new-test-1)."
            )
