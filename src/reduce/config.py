"""Load reduce settings from JSON (see README)."""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path

from reduce.reducer import known_pass_ids

_TOP_LEVEL_KEYS = frozenset(
    {
        "input",
        "file",
        "line",
        "replacement",
        "interesting",
        "output_dir",
        "action",
        "pipeline",
        "pass_under_test",
        "mtriple",
        "llc_O",
        "extract_mir_output",
    }
)


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


def _parse_pipeline(config_file: Path, raw: dict) -> list[str]:
    try:
        pl = raw["pipeline"]
    except KeyError as e:
        raise SystemExit(
            f'{config_file}: missing required top-level field "pipeline" '
            '(JSON array of pass id strings, e.g. ["snapshot", "llvm_reduce_ir"]).'
        ) from e
    if not isinstance(pl, list) or not pl:
        raise SystemExit(
            f'{config_file}: "pipeline" must be a non-empty JSON array of pass id strings.'
        )
    if not all(isinstance(x, str) for x in pl):
        raise SystemExit(f'{config_file}: "pipeline" must contain only strings.')
    valid = known_pass_ids()
    for x in pl:
        if x not in valid:
            known = ", ".join(sorted(valid))
            raise SystemExit(f'{config_file}: unknown pass id {x!r} in "pipeline". Known: {known}')
    return list(pl)


@dataclass(frozen=True)
class ReduceConfig:
    """One reduction job: IR input and an ordered pass pipeline."""

    llvm_bin: Path
    output_dir: Path | None
    action: str
    original_test: Path
    file: str
    line: int
    replacement: str | None
    interesting: Path | None
    pipeline: list[str]
    pass_under_test: str | None
    mtriple: str | None
    llc_O: str | None
    extract_mir_output: str | None


def load_reduce_config(path: Path, llvm_bin: Path) -> ReduceConfig:
    config_file = path.expanduser()

    with open(config_file, encoding="utf-8") as f:
        raw: dict = json.load(f)

    if not isinstance(raw, dict):
        raise SystemExit(f"{config_file}: config must be a JSON object.")

    _warn_unknown_keys(
        config_file=config_file,
        keys=set(raw),
        allowed=_TOP_LEVEL_KEYS,
        where="top-level",
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

    interesting_raw = raw.get("interesting")
    if interesting_raw is not None and not isinstance(interesting_raw, str):
        raise SystemExit(f'{config_file}: "interesting" must be a string path or omitted.')

    pipeline = _parse_pipeline(config_file, raw)

    output_dir = raw.get("output_dir")
    if output_dir is not None and not isinstance(output_dir, str):
        raise SystemExit(f'{config_file}: "output_dir" must be a string or omitted.')
    action = raw.get("action", "reduce")
    if not isinstance(action, str):
        raise SystemExit(f'{config_file}: "action" must be a string.')

    replacement = raw.get("replacement")
    if replacement is not None and not isinstance(replacement, str):
        raise SystemExit(f'{config_file}: "replacement" must be a string or omitted.')

    pass_under_test = raw.get("pass_under_test")
    if pass_under_test is not None and not isinstance(pass_under_test, str):
        raise SystemExit(
            f'{config_file}: "pass_under_test" must be a string (LLVM pass name) or omitted.'
        )

    mtriple = raw.get("mtriple")
    if mtriple is not None and not isinstance(mtriple, str):
        raise SystemExit(f'{config_file}: "mtriple" must be a string or omitted.')

    llc_O_raw = raw.get("llc_O")
    if llc_O_raw is None:
        llc_O = None
    elif isinstance(llc_O_raw, bool):
        raise SystemExit(f'{config_file}: "llc_O" must be a string (not boolean).')
    elif isinstance(llc_O_raw, int):
        raise SystemExit(
            f'{config_file}: "llc_O" must be a string such as "-O1" or "" (omit -O); got integer.'
        )
    elif isinstance(llc_O_raw, str):
        llc_O = llc_O_raw
    else:
        raise SystemExit(f'{config_file}: "llc_O" must be a string or omitted.')

    extract_mir_output = raw.get("extract_mir_output")
    if extract_mir_output is not None and not isinstance(extract_mir_output, str):
        raise SystemExit(f'{config_file}: "extract_mir_output" must be a string filename or omitted.')

    return ReduceConfig(
        llvm_bin=llvm_bin,
        output_dir=Path(output_dir) if output_dir else None,
        action=action,
        original_test=_resolve_relative_to_config(config_file, input_raw),
        file=file,
        line=line,
        replacement=replacement,
        interesting=(
            _resolve_relative_to_config(config_file, interesting_raw)
            if interesting_raw
            else None
        ),
        pipeline=pipeline,
        pass_under_test=pass_under_test,
        mtriple=mtriple,
        llc_O=llc_O,
        extract_mir_output=extract_mir_output,
    )
