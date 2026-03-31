"""Load reduce settings from JSON (see README)."""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from reduce.pass_registry import known_pass_ids

# Top-level keys always allowed (general job parameters).
_GENERAL_TOP_LEVEL_KEYS = frozenset(
    {
        "input",
        "file",
        "line",
        "replacement",
        "output_dir",
        "pipeline",
    }
)

# Allowed only when ``pipeline`` is a list of strings (legacy flat pass options).
_LEGACY_PASS_OPTION_KEYS = frozenset(
    {
        "pass_under_test",
        "mtriple",
        "llc_O",
        "extract_mir_output",
        "extract_ir_before_output",
        "interesting_mir",
    }
)

# Per-pass option keys (excluding ``id``) when using structured pipeline steps.
_KNOWN_OPTIONS_BY_PASS: dict[str, frozenset[str]] = {
    "snapshot": frozenset(),
    "llvm_reduce_ir": frozenset({"interesting"}),
    "creduce": frozenset({"interesting", "n"}),
    "llvm_reduce_mir": frozenset({"interesting_mir"}),
    "extract_mir_before_pass": frozenset(
        {"pass_under_test", "mtriple", "llc_O", "extract_mir_output"}
    ),
    "extract_ir_before_pass": frozenset(
        {"pass_under_test", "mtriple", "llc_O", "extract_ir_before_output"}
    ),
}


def _allowed_top_level_keys(*, legacy_flat_pass_keys: bool) -> frozenset[str]:
    if legacy_flat_pass_keys:
        return _GENERAL_TOP_LEVEL_KEYS | _LEGACY_PASS_OPTION_KEYS
    return _GENERAL_TOP_LEVEL_KEYS


def _warn_unknown_keys(
    *,
    config_file: Path,
    keys: set[str],
    allowed: frozenset[str],
    where: str,
) -> None:
    for key in sorted(keys - allowed):
        warnings.warn(
            f"{config_file}: unknown {where} key {key!r} (ignored)",
            UserWarning,
            stacklevel=3,
        )


def _resolve_relative_to_config(config_file: Path, raw: str) -> Path:
    """Absolute paths unchanged; otherwise resolve relative to the config file's directory."""
    p = Path(raw)
    if p.is_absolute():
        return p
    return (config_file.resolve().parent / p).resolve()


def _parse_llc_O(config_file: Path, raw: dict) -> str | None:
    llc_O_raw = raw.get("llc_O")
    if llc_O_raw is None:
        return None
    if isinstance(llc_O_raw, bool):
        raise SystemExit(f'{config_file}: "llc_O" must be a string (not boolean).')
    if isinstance(llc_O_raw, int):
        raise SystemExit(
            f'{config_file}: "llc_O" must be a string such as "-O1" or "" (omit -O); got integer.'
        )
    if isinstance(llc_O_raw, str):
        return llc_O_raw
    raise SystemExit(f'{config_file}: "llc_O" must be a string or omitted.')


def _warn_unknown_step_options(
    config_file: Path,
    pass_id: str,
    opts: dict[str, Any],
    *,
    step_index: int,
) -> None:
    known = _KNOWN_OPTIONS_BY_PASS.get(pass_id)
    if known is None:
        return
    for k in sorted(set(opts) - known):
        warnings.warn(
            f"{config_file}: pipeline[{step_index}] ({pass_id!r}) parameters: unknown key {k!r} (ignored)",
            UserWarning,
            stacklevel=3,
        )


def _resolve_step_option_paths(
    config_file: Path,
    pass_id: str,
    opts: dict[str, Any],
) -> dict[str, Any]:
    out = dict(opts)
    if pass_id == "llvm_reduce_mir" and "interesting_mir" in out:
        v = out["interesting_mir"]
        if v is not None and isinstance(v, str):
            out["interesting_mir"] = _resolve_relative_to_config(config_file, v)
        elif v is not None and not isinstance(v, Path):
            raise SystemExit(
                f'{config_file}: "interesting_mir" in pipeline step must be a string path.'
            )
    if pass_id == "llvm_reduce_ir" and "interesting" in out:
        v = out["interesting"]
        if v is not None and isinstance(v, str):
            out["interesting"] = _resolve_relative_to_config(config_file, v)
        elif v is not None and not isinstance(v, Path):
            raise SystemExit(
                f'{config_file}: "interesting" in pipeline step must be a string path.'
            )
    if pass_id == "creduce" and "interesting" in out:
        v = out["interesting"]
        if v is not None and isinstance(v, str):
            out["interesting"] = _resolve_relative_to_config(config_file, v)
        elif v is not None and not isinstance(v, Path):
            raise SystemExit(
                f'{config_file}: "interesting" in pipeline step must be a string path.'
            )
    return out


def _parse_legacy_default_pass_options(config_file: Path, raw: dict) -> dict[str, Any]:
    """Build merged options from flat top-level keys (legacy pipeline list of strings)."""
    out: dict[str, Any] = {}

    put = raw.get("pass_under_test")
    if put is not None:
        if not isinstance(put, str):
            raise SystemExit(
                f'{config_file}: "pass_under_test" must be a string (LLVM pass name) or omitted.'
            )
        out["pass_under_test"] = put

    mt = raw.get("mtriple")
    if mt is not None:
        if not isinstance(mt, str):
            raise SystemExit(f'{config_file}: "mtriple" must be a string or omitted.')
        out["mtriple"] = mt

    llc_O = _parse_llc_O(config_file, raw)
    if llc_O is not None:
        out["llc_O"] = llc_O

    emo = raw.get("extract_mir_output")
    if emo is not None:
        if not isinstance(emo, str):
            raise SystemExit(
                f'{config_file}: "extract_mir_output" must be a string filename or omitted.'
            )
        out["extract_mir_output"] = emo

    eio = raw.get("extract_ir_before_output")
    if eio is not None:
        if not isinstance(eio, str):
            raise SystemExit(
                f'{config_file}: "extract_ir_before_output" must be a string filename or omitted.'
            )
        out["extract_ir_before_output"] = eio

    im = raw.get("interesting_mir")
    if im is not None:
        if not isinstance(im, str):
            raise SystemExit(f'{config_file}: "interesting_mir" must be a string path or omitted.')
        out["interesting_mir"] = _resolve_relative_to_config(config_file, im)

    return out


@dataclass(frozen=True)
class PipelineStep:
    """One pipeline entry: pass id and pass-local options (immutable mapping)."""

    id: str
    options: Mapping[str, Any]


@dataclass(frozen=True)
class ReduceConfig:
    """One reduction job: IR input and an ordered pass pipeline."""

    llvm_bin: Path
    output_dir: Path | None
    original_test: Path
    file: str
    line: int
    replacement: str | None
    pipeline: tuple[PipelineStep, ...]
    """Ordered steps; each step carries options for that invocation only."""
    default_pass_options: Mapping[str, Any]
    """
    Merged before each step's ``options`` (legacy: from flat top-level pass keys).
    New-style configs use an empty mapping.
    """


def _parse_structured_pipeline(config_file: Path, pl: list) -> tuple[PipelineStep, ...]:
    steps: list[PipelineStep] = []
    for i, item in enumerate(pl):
        if not isinstance(item, dict):
            raise SystemExit(
                f"{config_file}: pipeline[{i}] must be an object with an \"id\" field "
                f'(e.g. {{"id": "llvm_reduce_ir"}}), not {type(item).__name__}.'
            )
        if "id" not in item:
            raise SystemExit(f'{config_file}: pipeline[{i}] is missing required field "id".')
        pid = item["id"]
        if not isinstance(pid, str):
            raise SystemExit(f'{config_file}: pipeline[{i}]."id" must be a string.')
        valid = known_pass_ids()
        if pid not in valid:
            known = ", ".join(sorted(valid))
            raise SystemExit(
                f'{config_file}: unknown pass id {pid!r} in pipeline[{i}]. Known ids: {known}'
            )
        if "parameters" in item:
            extra = set(item) - {"id", "parameters"}
            if extra:
                raise SystemExit(
                    f'{config_file}: pipeline[{i}] may only include "id" and "parameters"; '
                    f"move pass options into \"parameters\": {sorted(extra)!r}."
                )
            params = item["parameters"]
            if not isinstance(params, dict):
                raise SystemExit(
                    f'{config_file}: pipeline[{i}]."parameters" must be a JSON object, '
                    f"not {type(params).__name__}."
                )
            opts = dict(params)
        else:
            opts = {k: v for k, v in item.items() if k != "id"}
        _warn_unknown_step_options(config_file, pid, opts, step_index=i)
        opts = _resolve_step_option_paths(config_file, pid, opts)
        steps.append(PipelineStep(pid, MappingProxyType(opts)))
    return tuple(steps)


def _parse_string_pipeline_steps(config_file: Path, pl: list) -> tuple[PipelineStep, ...]:
    valid = known_pass_ids()
    steps: list[PipelineStep] = []
    for i, x in enumerate(pl):
        if not isinstance(x, str):
            raise SystemExit(
                f"{config_file}: pipeline must be either all strings or all objects; "
                f"found {type(x).__name__} at index {i}."
            )
        if x not in valid:
            known = ", ".join(sorted(valid))
            raise SystemExit(f'{config_file}: unknown pass id {x!r} in "pipeline". Known: {known}')
        steps.append(PipelineStep(x, MappingProxyType({})))
    return tuple(steps)


def _parse_pipeline(
    config_file: Path,
    raw: dict,
) -> tuple[tuple[PipelineStep, ...], dict[str, Any], bool]:
    try:
        pl = raw["pipeline"]
    except KeyError as e:
        raise SystemExit(
            f'{config_file}: missing required top-level field "pipeline" '
            '(non-empty JSON array of pass steps).'
        ) from e
    if not isinstance(pl, list) or not pl:
        raise SystemExit(
            f'{config_file}: "pipeline" must be a non-empty JSON array (strings or objects with "id", '
            f'and optional "parameters").'
        )

    if all(isinstance(x, str) for x in pl):
        steps = _parse_string_pipeline_steps(config_file, pl)
        defaults = _parse_legacy_default_pass_options(config_file, raw)
        return steps, defaults, True
    if all(isinstance(x, dict) for x in pl):
        steps = _parse_structured_pipeline(config_file, pl)
        return steps, {}, False

    raise SystemExit(
        f"{config_file}: \"pipeline\" entries must be all strings (legacy) or all objects "
        f'with an "id" field (and optionally "parameters": {{}}); mixed types are not allowed.'
    )


def load_reduce_config(path: Path, llvm_bin: Path) -> ReduceConfig:
    config_file = path.expanduser()

    with open(config_file, encoding="utf-8") as f:
        raw: dict = json.load(f)

    if not isinstance(raw, dict):
        raise SystemExit(f"{config_file}: config must be a JSON object.")

    pipeline_steps, default_opts_dict, legacy_pipeline = _parse_pipeline(config_file, raw)

    allowed = _allowed_top_level_keys(legacy_flat_pass_keys=legacy_pipeline)
    _warn_unknown_keys(
        config_file=config_file,
        keys=set(raw),
        allowed=allowed,
        where="top-level",
    )

    if not legacy_pipeline:
        stray = set(raw) & _LEGACY_PASS_OPTION_KEYS
        if stray:
            warnings.warn(
                f"{config_file}: top-level pass option keys {sorted(stray)!r} are ignored when "
                'using structured pipeline objects; put them in that step\'s "parameters".',
                UserWarning,
                stacklevel=2,
            )

    try:
        input_raw = raw["input"]
        file = raw["file"]
        line = raw["line"]
    except KeyError as e:
        raise SystemExit(
            f"{config_file}: missing required top-level field {e.args[0]!r} "
            '(need "input" path to .ll, "file", "line").'
        ) from e

    if not isinstance(input_raw, str):
        raise SystemExit(f'{config_file}: "input" must be a string path to the .ll file.')
    if not isinstance(file, str):
        raise SystemExit(f'{config_file}: "file" must be a string.')
    if not isinstance(line, int):
        raise SystemExit(f'{config_file}: "line" must be an integer.')

    output_dir = raw.get("output_dir")
    if output_dir is not None and not isinstance(output_dir, str):
        raise SystemExit(f'{config_file}: "output_dir" must be a string or omitted.')
    replacement = raw.get("replacement")
    if replacement is not None and not isinstance(replacement, str):
        raise SystemExit(f'{config_file}: "replacement" must be a string or omitted.')

    return ReduceConfig(
        llvm_bin=llvm_bin,
        output_dir=Path(output_dir) if output_dir else None,
        original_test=_resolve_relative_to_config(config_file, input_raw),
        file=file,
        line=line,
        replacement=replacement,
        pipeline=pipeline_steps,
        default_pass_options=MappingProxyType(dict(default_opts_dict)),
    )


def pipeline_steps_for_only_pass(
    full_pipeline: tuple[PipelineStep, ...],
    only_pass_id: str,
) -> tuple[PipelineStep, ...]:
    """Use options from the first step in ``full_pipeline`` whose id matches ``only_pass_id``."""
    for step in full_pipeline:
        if step.id == only_pass_id:
            return (step,)
    return (PipelineStep(only_pass_id, MappingProxyType({})),)
