"""Derive candidate-test llc flag variants from pr-check PR metadata."""

from __future__ import annotations

import csv
import re
import shlex
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from coverage.candidate_test_settings import (
    DEFAULT_LLC_FLAG_VARIANTS,
    write_settings_csv,
)

_RUN_LLC_RE = re.compile(r"RUN:\s*(?:not\s+)?(?:.*?\|\s*)?llc\s+", re.IGNORECASE)
_O_LEVEL_RE = re.compile(r"^-O[0123s]$")
_DROP_FLAG_PREFIXES = ("-filetype=",)
_KEEP_IF_PREFIX = (
    "-O",
    "-global-isel",
    "-mtriple=",
    "-mcpu=",
    "-mattr=",
    "-tailcallopt",
    "-global-isel-abort=",
)

_SI_PATH_MARKERS = (
    "SIISelLowering",
    "SIInsertWaitcnts",
    "SIInstrInfo",
    "SIFoldOperands",
    "/SI",
)
_GISEL_PATH_MARKERS = (
    "CallLowering",
    "Legalizer",
    "GlobalISel",
    "GISel",
)
_IR_PATH_MARKERS = (
    "InstCombine",
    "PromoteAlloca",
    "AMDGPULibFunc",
    "UniformIntrinsicCombine",
    "Utils/",
)


@dataclass(frozen=True)
class DerivedFlag:
    llc_flags: str
    source: str


def _normalize_global_isel_flags(flags: list[str]) -> list[str]:
    out: list[str] = []
    for flag in flags:
        if flag == "-global-isel":
            out.append("-global-isel=1")
        else:
            out.append(flag)
    return out


def _is_kept_flag(token: str) -> bool:
    if not token.startswith("-"):
        return False
    if any(token.startswith(prefix) for prefix in _DROP_FLAG_PREFIXES):
        return False
    if _O_LEVEL_RE.match(token):
        return True
    return any(token == prefix or token.startswith(prefix) for prefix in _KEEP_IF_PREFIX)


def parse_run_llc_flags(run_line: str) -> list[str] | None:
    """Return llc argv tokens (flags only) from a LIT RUN line, or None if not an llc run."""
    match = _RUN_LLC_RE.search(run_line)
    if match is None:
        return None

    tail = run_line[match.end() :]
    for stop in ("<", "|", "2>&1", " FileCheck", "\tFileCheck"):
        idx = tail.find(stop)
        if idx >= 0:
            tail = tail[:idx]
    tail = tail.strip()
    if not tail:
        return []

    try:
        parts = shlex.split(tail)
    except ValueError:
        parts = tail.split()

    flags = [p for p in parts if _is_kept_flag(p)]
    return _normalize_global_isel_flags(flags)


def extract_run_llc_flag_sets_from_added_lines(
    added_lines_csv: Path,
) -> list[DerivedFlag]:
    """Collect unique llc flag sets from RUN lines in added-lines.csv."""
    if not added_lines_csv.is_file():
        return []

    seen: set[str] = set()
    out: list[DerivedFlag] = []
    with added_lines_csv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "text" not in reader.fieldnames:
            return []
        for row in reader:
            text = row.get("text", "")
            if "llc" not in text or "RUN:" not in text:
                continue
            flags = parse_run_llc_flags(text)
            if flags is None:
                continue
            key = " ".join(flags)
            if not key or key in seen:
                continue
            seen.add(key)
            path = row.get("path", "")
            out.append(DerivedFlag(llc_flags=key, source=f"RUN:{path}"))
    return out


def _classify_path(path: str) -> set[str]:
    """Return heuristic flag suffix sets implied by a source path."""
    kinds: set[str] = set()
    if any(marker in path for marker in _SI_PATH_MARKERS):
        kinds.add("si")
    if any(marker in path for marker in _GISEL_PATH_MARKERS):
        kinds.add("gisel")
    if any(marker in path for marker in _IR_PATH_MARKERS):
        kinds.add("ir")
    if "SPIRV" in path or "/SPIRV/" in path:
        kinds.add("spirv")
    return kinds


def normalize_llvm_rel_path(rel_path: str) -> str:
    """Normalize git-relative paths from gaps-expanded (collapse duplicate llvm/ prefix)."""
    rel = Path(rel_path).as_posix().lstrip("/")
    while rel.startswith("llvm/llvm/"):
        rel = rel[len("llvm/") :]
    return rel


def join_llvm_abs_path(path_prefix: str, rel_path: str) -> str:
    """Join pr-check path prefix with a gaps-expanded relative path without doubling llvm/."""
    rel = normalize_llvm_rel_path(rel_path)
    prefix = path_prefix.rstrip("/")
    if rel.startswith("llvm/") and prefix.endswith("/llvm"):
        rel = rel[len("llvm/") :]
    return f"{prefix}/{rel}"


def gap_isel_suffixes(gap_target_paths: Iterable[str]) -> list[list[str]]:
    """Return -global-isel flag groups required by gap target file paths."""
    kinds: set[str] = set()
    for path in gap_target_paths:
        kinds |= _classify_path(normalize_llvm_rel_path(path))

    suffixes: list[list[str]] = []
    if "si" in kinds:
        suffixes.append(["-global-isel=0"])
    if "gisel" in kinds:
        suffixes.append(["-global-isel=1"])
    if "ir" in kinds:
        for suffix in (["-global-isel=0"], ["-global-isel=1"]):
            if suffix not in suffixes:
                suffixes.append(suffix)
    if not suffixes and "spirv" in kinds and kinds == {"spirv"}:
        return [[]]
    return suffixes


def _has_global_isel_flag(flags: Iterable[str]) -> bool:
    return any(flag.startswith("-global-isel") for flag in flags)


def merge_run_bases_with_gap_isel(
    run_bases: list[str],
    gap_target_paths: Iterable[str],
) -> list[str]:
    """Augment RUN-derived flag sets with gap-target ISel requirements."""
    isel_suffixes = gap_isel_suffixes(gap_target_paths)
    if not isel_suffixes:
        return list(run_bases)

    bases = run_bases if run_bases else [""]
    expanded: set[str] = set()
    for base in bases:
        parts = base.split()
        if _has_global_isel_flag(parts):
            expanded.add(base.strip())
            continue
        for suffix in isel_suffixes:
            merged_parts = list(parts)
            for flag in suffix:
                if not _has_global_isel_flag(merged_parts):
                    merged_parts.append(flag)
            expanded.add(" ".join(merged_parts).strip())
    return sorted(expanded)


def path_heuristic_flag_sets(file_paths: Iterable[str]) -> list[DerivedFlag]:
    """Infer llc flags from gap/changed source file paths."""
    kinds: set[str] = set()
    for path in file_paths:
        kinds |= _classify_path(path)

    if not kinds:
        return []

    suffix_sets: list[list[str]] = []
    if "si" in kinds:
        suffix_sets.append(["-global-isel=0"])
    if "gisel" in kinds:
        suffix_sets.append(["-global-isel=1"])
    if "ir" in kinds:
        suffix_sets.extend([["-global-isel=0"], ["-global-isel=1"]])
    if "spirv" in kinds and not suffix_sets:
        suffix_sets.append([])
    if "spirv" in kinds and kinds == {"spirv"}:
        return [DerivedFlag(llc_flags="", source="heuristic:spirv-o-only")]

    if not suffix_sets and "spirv" not in kinds:
        suffix_sets = [["-global-isel=0"], ["-global-isel=1"]]

    seen: set[str] = set()
    out: list[DerivedFlag] = []
    for suffix in suffix_sets:
        key = " ".join(suffix)
        if key in seen:
            continue
        seen.add(key)
        out.append(DerivedFlag(llc_flags=key, source=f"heuristic:{key or 'default'}"))
    return out


def _split_o_level(flags: list[str]) -> tuple[str | None, list[str]]:
    o_level: str | None = None
    rest: list[str] = []
    for flag in flags:
        if _O_LEVEL_RE.match(flag):
            o_level = flag
        else:
            rest.append(flag)
    return o_level, rest


def cross_with_o_levels(flag_sets: list[str]) -> list[str]:
    """Expand flag sets with -O0..-O3 when no explicit -O level is present."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in flag_sets:
        parts = raw.split()
        o_level, rest = _split_o_level(parts)
        rest_key = " ".join(rest)
        if o_level is not None:
            combined = " ".join(part for part in (o_level, rest_key) if part)
            if combined not in seen:
                seen.add(combined)
                out.append(combined)
            continue
        for o in DEFAULT_LLC_FLAG_VARIANTS:
            combined = " ".join(part for part in (o, rest_key) if part)
            if combined not in seen:
                seen.add(combined)
                out.append(combined)
    return out


def exclude_variants(variants: list[str], exclude: set[str]) -> list[str]:
    return [v for v in variants if v not in exclude]


def derive_llc_flag_variants(
    *,
    pr_run_dir: Path,
    gap_target_paths: Iterable[str],
    exclude_flags: set[str] | None = None,
) -> tuple[list[str], list[DerivedFlag]]:
    """Derive llc flag variants from pr-check run metadata."""
    added_lines = pr_run_dir / "added-lines" / "added-lines.csv"
    sources: list[DerivedFlag] = []

    run_flags = extract_run_llc_flag_sets_from_added_lines(added_lines)
    sources.extend(run_flags)

    gap_paths = [normalize_llvm_rel_path(path) for path in gap_target_paths]
    gap_heuristics = path_heuristic_flag_sets(gap_paths)
    if gap_heuristics:
        sources.extend(gap_heuristics)

    changed_paths = set(gap_paths)
    if added_lines.is_file():
        with added_lines.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames and "path" in reader.fieldnames:
                for row in reader:
                    path = row.get("path", "").strip()
                    if path and not path.startswith("llvm/test/"):
                        changed_paths.add(normalize_llvm_rel_path(path))

    run_bases = [d.llc_flags for d in run_flags]
    if run_bases:
        base_sets = merge_run_bases_with_gap_isel(run_bases, gap_paths)
    elif gap_heuristics:
        base_sets = [d.llc_flags for d in gap_heuristics if d.llc_flags or d.source == "heuristic:spirv-o-only"]
    else:
        sources.extend(path_heuristic_flag_sets(changed_paths))
        base_sets = [
            d.llc_flags
            for d in sources
            if d.llc_flags or d.source == "heuristic:spirv-o-only"
        ]

    if not base_sets and not run_flags:
        base_sets = ["-global-isel=0", "-global-isel=1"]

    variants = cross_with_o_levels(base_sets)
    if exclude_flags:
        variants = exclude_variants(variants, exclude_flags)

    return variants, sources


def write_derived_settings_csv(
    variants: list[str],
    path: Path,
    *,
    sources: list[DerivedFlag] | None = None,
) -> None:
    write_settings_csv(variants, path)
    if not sources:
        return
    sources_path = path.with_name("candidate_test_settings_sources.csv")
    by_base = {d.llc_flags: d.source for d in sources}
    with sources_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["llc_flags", "source"])
        writer.writeheader()
        for flags in variants:
            parts = flags.split()
            _, rest = _split_o_level(parts)
            rest_key = " ".join(rest)
            source = by_base.get(rest_key, by_base.get(flags, "derived"))
            writer.writerow({"llc_flags": flags, "source": source})


def default_exclude_completed_o_levels() -> set[str]:
    return set(DEFAULT_LLC_FLAG_VARIANTS)
