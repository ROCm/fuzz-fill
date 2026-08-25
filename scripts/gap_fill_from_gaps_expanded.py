#!/usr/bin/env python3
"""Prepare and aggregate gap-filling runs from completed pr-check artifacts.

When reading pr-check runs directly, skips ambiguous or low-interest uncovered lines
by default (for example debug logging or bare control-flow keywords). See
``coverage.gap_line_interest`` for the heuristics and ``--include-uninteresting`` to
disable filtering.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from coverage.gap_line_interest import classify_gap_line_interest  # noqa: E402
from coverage.line_rules import match_symcov_file  # noqa: E402
from coverage.pr_llc_settings import (  # noqa: E402
    abs_path_to_llvm_rel_path,
    default_exclude_completed_o_levels,
    derive_llc_flag_variants,
    join_llvm_abs_path,
    normalize_llvm_rel_path,
    write_derived_settings_csv,
)
from pr_check.gap_loader import iter_uncovered_gap_lines  # noqa: E402

DEFAULT_GITHUB_REPO = "llvm/llvm-project"

BACKEND_CORPUS = {
    "amdgpu": "amdgcn-amd-amdhsa",
    "spirv": "spirv64-amd-amdhsa",
}


@dataclass(frozen=True)
class GapRow:
    pr_number: str
    backend: str
    line: int
    rel_path: str
    location: str
    text: str = ""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize_backend(raw: str) -> str:
    value = raw.strip().lower()
    if value == "amdgpu":
        return "amdgpu"
    if value in ("spirv", "spir-v"):
        return "spirv"
    raise ValueError(f"unsupported backend: {raw!r}")


def pr_number_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def parse_gaps_expanded(path: Path) -> list[GapRow]:
    rows: list[GapRow] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise SystemExit(f"empty or invalid CSV: {path}")
        need = {"PR", "Backend", "Line", "Location"}
        if not need.issubset(set(reader.fieldnames)):
            raise SystemExit(
                f"{path}: expected columns {sorted(need)}, got {reader.fieldnames!r}"
            )
        for row in reader:
            location = row["Location"].strip()
            if ":" not in location:
                raise SystemExit(
                    f"{path}: invalid Location (expected path:line): {location!r}"
                )
            rel_path, line_text = location.rsplit(":", 1)
            try:
                line = int(row["Line"])
            except ValueError as exc:
                raise SystemExit(f"{path}: invalid Line {row['Line']!r}") from exc
            if int(line_text) != line:
                raise SystemExit(
                    f"{path}: Line column ({line}) does not match Location ({location})"
                )
            rows.append(
                GapRow(
                    pr_number=pr_number_from_url(row["PR"].strip()),
                    backend=normalize_backend(row["Backend"]),
                    line=line,
                    rel_path=rel_path,
                    location=location,
                    text=(row.get("Text") or "").strip(),
                )
            )
    return rows


def load_gaps_from_runs(
    pr_check_runs_root: Path,
    *,
    github_repo: str = DEFAULT_GITHUB_REPO,
    filter_uninteresting: bool = True,
) -> tuple[list[GapRow], list[dict[str, str]]]:
    """Load gap rows from completed pr-check runs, skipping low-interest lines by default."""
    included: list[GapRow] = []
    skipped: list[dict[str, str]] = []

    if not pr_check_runs_root.is_dir():
        raise SystemExit(f"pr-check runs root not found: {pr_check_runs_root}")

    for gap in iter_uncovered_gap_lines(pr_check_runs_root):
        pr_url = f"https://github.com/{github_repo}/pull/{gap.pr_number}"
        rel_path = abs_path_to_llvm_rel_path(gap.file_path)
        location = f"{rel_path}:{gap.line}"
        base = {
            "PR": pr_url,
            "Backend": gap.backend,
            "Line": str(gap.line),
            "Location": location,
            "Text": gap.text,
        }
        decision = (
            classify_gap_line_interest(gap.text) if filter_uninteresting else None
        )
        if decision is None or decision.include:
            included.append(
                GapRow(
                    pr_number=str(gap.pr_number),
                    backend=gap.backend,
                    line=gap.line,
                    rel_path=rel_path,
                    location=location,
                    text=gap.text,
                )
            )
        else:
            skipped.append({**base, "SkipReason": decision.reason})

    return included, skipped


def write_skipped_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["PR", "Backend", "Line", "Location", "Text", "SkipReason"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def load_address_map_files(llc_map_csv: Path) -> set[str]:
    files: set[str] = set()
    with llc_map_csv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "file" not in reader.fieldnames:
            raise SystemExit(f"{llc_map_csv}: expected a file column")
        for row in reader:
            files.add(row["file"].strip())
    return files


def load_address_map_line_keys(llc_map_csv: Path) -> set[tuple[str, int]]:
    keys: set[tuple[str, int]] = set()
    with llc_map_csv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise SystemExit(f"{llc_map_csv}: empty or invalid CSV")
        for row in reader:
            keys.add((row["file"].strip(), int(row["line"])))
    return keys


def infer_path_prefix(summary_files: set[str]) -> str:
    sample = next(iter(summary_files))
    marker = "/llvm/"
    idx = sample.find(marker)
    if idx == -1:
        raise SystemExit(f"could not infer llvm path prefix from address map file: {sample!r}")
    return sample[: idx + len("/llvm")]


def resolve_gap_path(
    gap: GapRow,
    *,
    summary_files: set[str],
    path_prefix: str,
) -> tuple[str, bool]:
    rel_path = normalize_llvm_rel_path(gap.rel_path)
    abs_file = match_symcov_file(rel_path, summary_files)
    if abs_file is not None:
        return abs_file, True
    return join_llvm_abs_path(path_prefix, rel_path), False


def run_key(row: GapRow) -> tuple[str, str]:
    return row.pr_number, row.backend


def pr_check_run_dir(pr_check_runs_root: Path, pr_number: str, backend: str) -> Path:
    return pr_check_runs_root / f"{pr_number}-{backend}"


def gap_input_dir(inputs_root: Path, pr_number: str, backend: str) -> Path:
    return inputs_root / f"{pr_number}-{backend}"


def gap_output_dir(outputs_root: Path, pr_number: str, backend: str) -> Path:
    return outputs_root / f"{pr_number}-{backend}"


def write_manifest(
    manifest: list[dict[str, str]],
    *,
    inputs_root: Path,
    outputs_root: Path,
) -> Path:
    manifest_path = inputs_root / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "pr_number",
                "backend",
                "gap_count",
                "gap_lines_csv",
                "llc_address_line_map_csv",
                "candidate_tests_subdir",
                "settings_csv",
                "output_dir",
            ],
        )
        writer.writeheader()
        for entry in manifest:
            writer.writerow(
                {
                    **entry,
                    "output_dir": str(
                        gap_output_dir(outputs_root, entry["pr_number"], entry["backend"])
                    ),
                }
            )
    return manifest_path


def prepare_command(args: argparse.Namespace) -> int:
    pr_check_runs_root = args.pr_check_runs_root.resolve()
    inputs_root = args.inputs_root.resolve()
    outputs_root = args.outputs_root.resolve()

    if args.gaps_expanded_csv is not None:
        gaps_expanded_csv = args.gaps_expanded_csv.resolve()
        if not gaps_expanded_csv.is_file():
            raise SystemExit(f"gaps-expanded CSV not found: {gaps_expanded_csv}")
        rows = parse_gaps_expanded(gaps_expanded_csv)
        skipped: list[dict[str, str]] = []
    else:
        rows, skipped = load_gaps_from_runs(
            pr_check_runs_root,
            github_repo=args.github_repo,
            filter_uninteresting=args.filter_uninteresting,
        )
        if args.skipped_output is not None and skipped:
            skipped_path = args.skipped_output.resolve()
            write_skipped_csv(skipped_path, skipped)
            print(
                f"wrote {skipped_path}: {len(skipped)} skipped low-interest gap line(s)",
                file=sys.stderr,
            )

    grouped: dict[tuple[str, str], list[GapRow]] = defaultdict(list)
    for row in rows:
        grouped[run_key(row)].append(row)

    manifest: list[dict[str, str]] = []
    inputs_root.mkdir(parents=True, exist_ok=True)

    for (pr_number, backend), gap_rows in sorted(grouped.items()):
        run_dir = pr_check_run_dir(pr_check_runs_root, pr_number, backend)
        llc_map = run_dir / "baseline" / "llc_address_line_map.csv"
        if not llc_map.is_file():
            raise SystemExit(
                f"missing baseline address map for PR {pr_number} ({backend}): {llc_map}"
            )

        summary_files = load_address_map_files(llc_map)
        address_map_lines = load_address_map_line_keys(llc_map)
        path_prefix = infer_path_prefix(summary_files)
        out_dir = gap_input_dir(inputs_root, pr_number, backend)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_csv = out_dir / "gap-lines.csv"
        warnings_csv = out_dir / "gap-lines-warnings.csv"

        resolved: list[tuple[str, int]] = []
        warnings: list[dict[str, str]] = []
        for gap in gap_rows:
            abs_file, matched_in_map = resolve_gap_path(
                gap,
                summary_files=summary_files,
                path_prefix=path_prefix,
            )
            resolved.append((abs_file, gap.line))
            if not matched_in_map:
                warnings.append(
                    {
                        "location": gap.location,
                        "file": abs_file,
                        "line": str(gap.line),
                        "warning": "file not present in llc_address_line_map.csv",
                    }
                )
            elif (abs_file, gap.line) not in address_map_lines:
                warnings.append(
                    {
                        "location": gap.location,
                        "file": abs_file,
                        "line": str(gap.line),
                        "warning": "line not present in llc_address_line_map.csv",
                    }
                )

        with out_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["file", "line"])
            for abs_file, line in sorted(set(resolved)):
                writer.writerow([abs_file, line])

        if warnings:
            with warnings_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=["location", "file", "line", "warning"]
                )
                writer.writeheader()
                writer.writerows(warnings)
            print(
                f"warning: PR {pr_number} ({backend}): "
                f"{len(warnings)} gap line(s) missing from llc_address_line_map -> {warnings_csv}",
                file=sys.stderr,
            )

        settings_csv = ""
        if args.derive_llc_settings:
            gap_rel_paths = sorted({gap.rel_path for gap in gap_rows})
            exclude_flags = (
                default_exclude_completed_o_levels()
                if args.exclude_completed_o_levels
                else None
            )
            variants, sources = derive_llc_flag_variants(
                pr_run_dir=run_dir,
                gap_target_paths=gap_rel_paths,
                exclude_flags=exclude_flags,
            )
            settings_path = out_dir / "candidate_test_settings.csv"
            if variants:
                write_derived_settings_csv(variants, settings_path, sources=sources)
                settings_csv = str(settings_path.resolve())
                print(
                    f"derived {len(variants)} llc flag variant(s) for PR {pr_number} "
                    f"({backend}) -> {settings_path}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"warning: PR {pr_number} ({backend}): no pending llc flag variants "
                    f"after derivation/exclusion",
                    file=sys.stderr,
                )
        elif args.settings_csv is not None:
            settings_csv = str(args.settings_csv.resolve())

        manifest.append(
            {
                "pr_number": pr_number,
                "backend": backend,
                "gap_count": str(len(resolved)),
                "gap_lines_csv": str(out_csv.resolve()),
                "llc_address_line_map_csv": str(llc_map.resolve()),
                "candidate_tests_subdir": BACKEND_CORPUS[backend],
                "settings_csv": settings_csv,
                "output_dir": str(gap_output_dir(outputs_root, pr_number, backend)),
            }
        )
        print(
            f"prepared PR {pr_number} ({backend}): {len(resolved)} gap line(s) -> {out_csv}",
            file=sys.stderr,
        )

    manifest_path = write_manifest(manifest, inputs_root=inputs_root, outputs_root=outputs_root)
    print(f"wrote manifest: {manifest_path}", file=sys.stderr)
    if not rows:
        print("warning: no gap lines found", file=sys.stderr)
    return 0


def aggregate_command(args: argparse.Namespace) -> int:
    manifest_path = args.manifest.resolve()
    report_path = args.report.resolve()
    outputs_root = args.outputs_root.resolve()

    if not manifest_path.is_file():
        raise SystemExit(f"missing manifest: {manifest_path}")

    filled_rows: list[dict[str, str]] = []
    target_rows: list[dict[str, str]] = []

    with manifest_path.open(encoding="utf-8", newline="") as handle:
        manifest = list(csv.DictReader(handle))

    for entry in manifest:
        pr_number = entry["pr_number"]
        backend = entry["backend"]
        out_dir = Path(
            entry.get("output_dir") or gap_output_dir(outputs_root, pr_number, backend)
        )
        new_coverage = out_dir / "incremental" / "new_coverage.csv"
        gap_lines = Path(entry["gap_lines_csv"])

        with gap_lines.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                target_rows.append(
                    {
                        "pr_number": pr_number,
                        "backend": backend,
                        "file": row["file"],
                        "line": row["line"],
                        "filled": "no",
                        "test_name": "",
                        "covered_points": "",
                    }
                )

        if not new_coverage.is_file():
            print(f"warning: missing {new_coverage}", file=sys.stderr)
            continue

        with new_coverage.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                continue
            for row in reader:
                filled_rows.append(
                    {
                        "pr_number": pr_number,
                        "backend": backend,
                        "test_name": row["test_name"],
                        "file": row["file"],
                        "line": row["line"],
                        "covered_points": row.get("covered-points", ""),
                    }
                )

    filled_keys = {(r["pr_number"], r["backend"], r["file"], r["line"]) for r in filled_rows}
    for target in target_rows:
        key = (target["pr_number"], target["backend"], target["file"], target["line"])
        if key in filled_keys:
            matches = [
                r
                for r in filled_rows
                if (r["pr_number"], r["backend"], r["file"], r["line"]) == key
            ]
            target["filled"] = "yes"
            target["test_name"] = ";".join(sorted({m["test_name"] for m in matches}))
            target["covered_points"] = ";".join(
                sorted({m["covered_points"] for m in matches})
            )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "pr_number",
                "backend",
                "file",
                "line",
                "filled",
                "test_name",
                "covered_points",
            ],
        )
        writer.writeheader()
        writer.writerows(target_rows)

    filled_count = sum(1 for row in target_rows if row["filled"] == "yes")
    print(
        f"wrote {report_path}: {filled_count}/{len(target_rows)} target gap line(s) filled",
        file=sys.stderr,
    )

    if filled_rows:
        combined_path = report_path.with_name("gaps-filled-details.csv")
        with combined_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "pr_number",
                    "backend",
                    "test_name",
                    "file",
                    "line",
                    "covered_points",
                ],
            )
            writer.writeheader()
            writer.writerows(filled_rows)
        print(f"wrote {combined_path}", file=sys.stderr)

    return 0


def build_parser() -> argparse.ArgumentParser:
    root = repo_root()
    default_runs = root / "data/pr-check/runs"
    default_inputs = root / "data/gap-fill/inputs"
    default_outputs = root / "data/gap-fill/runs"
    default_report = root / "data/gap-fill/reports/gaps-filled.csv"
    default_skipped = default_inputs / "gaps-skipped.csv"

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="write per-PR gap-lines.csv and manifest.csv")
    prepare.add_argument(
        "--gaps-expanded-csv",
        type=Path,
        default=None,
        help="optional legacy gaps-expanded CSV input (default: read pr-check runs directly)",
    )
    prepare.add_argument("--pr-check-runs-root", type=Path, default=default_runs)
    prepare.add_argument("--inputs-root", type=Path, default=default_inputs)
    prepare.add_argument("--outputs-root", type=Path, default=default_outputs)
    prepare.add_argument(
        "--skipped-output",
        type=Path,
        default=default_skipped,
        help=(
            "audit CSV for skipped low-interest gap lines "
            "(default: data/gap-fill/inputs/gaps-skipped.csv)"
        ),
    )
    prepare.add_argument(
        "--include-uninteresting",
        action="store_false",
        dest="filter_uninteresting",
        help=(
            "include ambiguous or low-interest uncovered lines "
            "(debug, control flow, declarations, returns, asserts)"
        ),
    )
    prepare.add_argument(
        "--github-repo",
        default=DEFAULT_GITHUB_REPO,
        help=f"GitHub repo for PR URLs when reading runs (default: {DEFAULT_GITHUB_REPO})",
    )
    prepare.add_argument(
        "--derive-llc-settings",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="derive per-PR candidate_test_settings.csv from pr-check metadata (default: on)",
    )
    prepare.add_argument(
        "--exclude-completed-o-levels",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="drop plain -O0..-O3 rows from derived settings (default: on)",
    )
    prepare.add_argument(
        "--settings-csv",
        type=Path,
        default=None,
        help="use this settings CSV for all PRs instead of deriving (requires --no-derive-llc-settings)",
    )
    prepare.set_defaults(func=prepare_command, filter_uninteresting=True)

    aggregate = sub.add_parser("aggregate", help="summarize incremental/new_coverage.csv outputs")
    aggregate.add_argument("--manifest", type=Path, default=default_inputs / "manifest.csv")
    aggregate.add_argument("--outputs-root", type=Path, default=default_outputs)
    aggregate.add_argument("--report", type=Path, default=default_report)
    aggregate.set_defaults(func=aggregate_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
