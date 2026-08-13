"""Load llc invocation variants for ``coverage candidate-test``."""

from __future__ import annotations

import csv
from pathlib import Path

LLC_FLAGS_COLUMN = "llc_flags"

_DEFAULT_OPT_LEVELS = ("-O0", "-O1", "-O2", "-O3")


def default_llc_flag_variants() -> tuple[str, ...]:
    """Built-in default: four optimization levels."""
    return _DEFAULT_OPT_LEVELS


DEFAULT_LLC_FLAG_VARIANTS = default_llc_flag_variants()


def load_llc_flag_variants(settings_csv: Path | None) -> list[str]:
    """Return llc flag strings from ``settings_csv`` or the built-in default."""
    if settings_csv is None:
        return list(DEFAULT_LLC_FLAG_VARIANTS)
    return _load_llc_flag_variants_csv(settings_csv)


def _load_llc_flag_variants_csv(settings_csv: Path) -> list[str]:
    path = settings_csv.resolve()
    if not path.is_file():
        raise SystemExit(f"error: settings CSV not found: {path}")

    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise SystemExit(f"error: empty or invalid settings CSV: {path}")
        if LLC_FLAGS_COLUMN not in reader.fieldnames:
            raise SystemExit(
                f"error: {path}: expected column {LLC_FLAGS_COLUMN!r}, "
                f"got {reader.fieldnames!r}"
            )

        variants: list[str] = []
        seen: set[str] = set()
        for line_no, row in enumerate(reader, start=2):
            raw = row.get(LLC_FLAGS_COLUMN)
            if raw is None:
                continue
            flags = raw.strip()
            if not flags:
                raise SystemExit(
                    f"error: {path}: blank {LLC_FLAGS_COLUMN} on line {line_no}"
                )
            if flags in seen:
                raise SystemExit(
                    f"error: {path}: duplicate {LLC_FLAGS_COLUMN} on line {line_no}: "
                    f"{flags!r}"
                )
            seen.add(flags)
            variants.append(flags)

    if not variants:
        raise SystemExit(f"error: no llc flag variants in settings CSV: {path}")

    return variants


MANIFEST_COLUMNS = ("test_id", "source_file", "llc_flags", "test_dir")


def write_settings_csv(variants: list[str], path: Path) -> None:
    """Write llc flag variants to a settings CSV under the candidate-test output dir."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([LLC_FLAGS_COLUMN])
        for flags in variants:
            writer.writerow([flags])


def write_manifest_csv(
    work: list[tuple[Path, Path, str]],
    path: Path,
) -> None:
    """Write one manifest row per planned standalone run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for test_dir, test_path, llc_flags in work:
            rest = test_dir.name.removeprefix("test_")
            test_id, _ = rest.split("_", 1)
            writer.writerow(
                {
                    "test_id": test_id,
                    "source_file": str(test_path.resolve()),
                    "llc_flags": llc_flags,
                    "test_dir": test_dir.name,
                }
            )
