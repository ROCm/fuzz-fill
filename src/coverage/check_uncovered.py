"""Compare analysed novel lines with original vs replacement snippets (WIP).

The input CSV is ``coverage analyse`` stacked output
(``per_test_csv``, ``file``, ``function``, ``line``) plus ``line_original`` and
``line_replacement`` (or ``original_line`` / ``replacement_line``).

An optional column ``skip`` may be present: if its cell is ``1`` (after strip), that
row is skipped; ``0``, empty, or any other value processes the row as usual.
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

from coverage.stage_log import stage_line


def row_lit_summary_path(dest_dir: Path, csv_stem: str, row_num: int) -> Path:
    """Path written when ``ninja check-all`` fails and a lit excerpt is extracted."""
    return dest_dir / f"{csv_stem}_row{row_num}_lit_summary.txt"


def row_done_path(dest_dir: Path, csv_stem: str, row_num: int) -> Path:
    """Marker touched after a row finishes (patch, ninja, restore) without aborting."""
    return dest_dir / f"{csv_stem}_row{row_num}.done"


def _cell(row: dict[str, str], *keys: str) -> str | None:
    for k in keys:
        if k not in row:
            continue
        v = row[k]
        if v is None:
            continue
        if isinstance(v, str) and v == "":
            continue
        return v
    return None


def _csv_row_marked_skip(row: dict[str, str]) -> bool:
    """True when the CSV header includes ``skip`` and the cell is ``1`` (after strip)."""
    if "skip" not in row:
        return False
    v = row["skip"]
    if v is None:
        return False
    return str(v).strip() == "1"


def _apply_line_replacement(
    file_path: Path,
    line_1based: int,
    replacement: str,
) -> str:
    """Replace the 1-based line in ``file_path`` with ``replacement`` (may be multi-line).

    ``replacement`` is split on line breaks; those segments replace the single original line.
    Returns the original file text for restoration.
    """
    original = file_path.read_text(encoding="utf-8", errors="replace")
    ends_with_nl = original.endswith("\n")
    lines = original.splitlines()
    idx = line_1based - 1
    if idx < 0 or idx >= len(lines):
        raise ValueError(
            f"{file_path}: line {line_1based} out of range (file has {len(lines)} lines)"
        )
    new_lines = lines[:idx] + replacement.splitlines() + lines[idx + 1 :]
    new_text = "\n".join(new_lines)
    if ends_with_nl:
        new_text += "\n"
    file_path.write_text(new_text, encoding="utf-8")
    return original


def _run_ninja(build_dir: Path, *extra_args: str) -> int:
    cmd = ["ninja", *extra_args]
    stage_line("check-uncovered", f"run: {' '.join(cmd)} (cwd={build_dir})")
    proc = subprocess.run(cmd, cwd=build_dir, check=False)
    return int(proc.returncode)


def extract_lit_failed_tests_section(text: str) -> str | None:
    """Slice llvm-lit output from the ``****`` / ``Failed Tests`` block through the summary.

    Returns ``None`` if no ``Failed Tests`` line is present.
    """
    lines = text.splitlines()
    failed_i = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("Failed Tests"):
            failed_i = i
            break
    if failed_i is None:
        return None

    start = failed_i
    while start > 0:
        s = lines[start - 1].strip()
        if s and all(c == "*" for c in s):
            start -= 1
        else:
            break

    total_i = None
    for i in range(failed_i, len(lines)):
        if lines[i].startswith("Total Discovered Tests:"):
            total_i = i
            break
    if total_i is None:
        return "\n".join(lines[start:])

    end = total_i
    j = total_i + 1
    while j < len(lines):
        line = lines[j]
        if line.startswith("  ") and ":" in line:
            end = j
            j += 1
            continue
        if re.match(r"^\d+ warning\(s\) in tests\s*$", line.strip()):
            end = j
            break
        if line.strip() == "":
            j += 1
            continue
        break

    return "\n".join(lines[start : end + 1])


def _run_ninja_check_all_captured(build_dir: Path) -> tuple[int, str]:
    """Run ``ninja check-all``; merge stdout/stderr, stream to terminal, return full text.

    Uses a pipe plus chunked reads so output appears live. ``subprocess.run(..., PIPE)``
    would buffer the entire run until exit, which hides progress for long ``check-all``
    invocations.
    """
    cmd = ["ninja", "check-all"]
    stage_line("check-uncovered", f"run: {' '.join(cmd)} (cwd={build_dir})")
    proc = subprocess.Popen(
        cmd,
        cwd=build_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    chunks: list[bytes] = []
    assert proc.stdout is not None
    try:
        out_sink = sys.stdout.buffer
    except AttributeError:
        out_sink = None
    while True:
        chunk = proc.stdout.read(65536)
        if not chunk:
            break
        chunks.append(chunk)
        if out_sink is not None:
            out_sink.write(chunk)
            out_sink.flush()
        else:
            sys.stdout.write(chunk.decode("utf-8", errors="replace"))
            sys.stdout.flush()
    rc = int(proc.wait())
    text = b"".join(chunks).decode("utf-8", errors="replace")
    return rc, text


def _run_full_ninja_then_check_all(build_dir: Path) -> tuple[int, int, str]:
    """Run ``ninja``, then ``ninja check-all`` (captured for lit summary extraction).

    Returns ``(rc_build, rc_check, check_all_output)``.
    """
    rc_build = _run_ninja(build_dir)
    rc_check, check_out = _run_ninja_check_all_captured(build_dir)
    return rc_build, rc_check, check_out


def verify_original_lines_only(csv_path: Path) -> int:
    """Check each row: ``file`` line ``line`` equals ``original_line`` / ``line_original``."""
    stage_line("check-uncovered", "mode: verify original lines only (no patch, no ninja)")
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            stage_line("check-uncovered", "error: CSV has no header row")
            return 1

        for row_num, row in enumerate(reader, start=2):
            if _csv_row_marked_skip(row):
                stage_line(
                    "check-uncovered",
                    f"row {row_num}: skip (CSV skip column is 1)",
                )
                continue

            file_s = _cell(row, "file")
            line_s = _cell(row, "line")
            original_expect = _cell(row, "line_original", "original_line")

            if not file_s or not line_s or original_expect is None:
                stage_line(
                    "check-uncovered",
                    f"error: row {row_num}: missing file, line, or original_line",
                )
                return 1

            try:
                line_no = int(line_s)
            except ValueError:
                stage_line(
                    "check-uncovered",
                    f"error: row {row_num}: bad line number {line_s!r}",
                )
                return 1

            src_path = Path(file_s)
            if not src_path.is_file():
                stage_line(
                    "check-uncovered",
                    f"error: row {row_num}: source not found: {src_path}",
                )
                return 1

            try:
                disk = src_path.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                stage_line(
                    "check-uncovered",
                    f"error: row {row_num}: could not read {src_path}: {e}",
                )
                return 1

            lines = disk.splitlines()
            li = line_no - 1
            if li < 0 or li >= len(lines):
                stage_line(
                    "check-uncovered",
                    f"error: row {row_num}: line {line_no} out of range "
                    f"({src_path} has {len(lines)} lines)",
                )
                return 1

            actual = lines[li]
            if actual != original_expect:
                stage_line(
                    "check-uncovered",
                    f"error: row {row_num}: line {line_no} in {src_path} does not match CSV "
                    f"original_line",
                )
                return 1

            stage_line("check-uncovered", f"row {row_num}: ok {src_path}:{line_no}")

    stage_line("check-uncovered", "all rows: original lines match")
    return 0


def _write_lit_summary_excerpt(
    check_all_output: str,
    dest_dir: Path,
    csv_stem: str,
    row_num: int,
) -> Path | None:
    excerpt = extract_lit_failed_tests_section(check_all_output)
    if excerpt is None:
        stage_line(
            "check-uncovered",
            "no Failed Tests section in check-all output; lit summary file not written",
        )
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = row_lit_summary_path(dest_dir, csv_stem, row_num)
    out_path.write_text(excerpt + ("\n" if not excerpt.endswith("\n") else ""), encoding="utf-8")
    stage_line("check-uncovered", f"wrote lit summary excerpt: {out_path}")
    return out_path


def check_uncovered_main(args: Namespace) -> int:
    csv_path = Path(args.csv).resolve()
    stage_line("check-uncovered", f"csv: {csv_path}")

    if not csv_path.is_file():
        stage_line("check-uncovered", f"error: CSV not found: {csv_path}")
        return 1

    if args.verify_originals_only:
        return verify_original_lines_only(csv_path)

    if args.llvm_build is None:
        stage_line(
            "check-uncovered",
            "error: LLVM-BUILD is required unless ``--verify-originals-only``",
        )
        return 1

    build_dir = Path(args.llvm_build).resolve()
    summary_dir = (
        Path(args.lit_summary_dir).resolve()
        if args.lit_summary_dir is not None
        else csv_path.parent
    )
    stage_line("check-uncovered", f"llvm-build: {build_dir}")
    stage_line("check-uncovered", f"lit-summary-dir: {summary_dir}")

    if not build_dir.is_dir():
        stage_line("check-uncovered", f"error: LLVM build directory not found: {build_dir}")
        return 1

    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            stage_line("check-uncovered", "error: CSV has no header row")
            return 1

        # One CSV row at a time: patch → full `ninja` → full `ninja check-all` → restore.
        for row_num, row in enumerate(reader, start=2):
            if row_num < args.start_csv_row:
                stage_line(
                    "check-uncovered",
                    f"row {row_num}: skip (before --start-csv-row {args.start_csv_row})",
                )
                continue

            if args.resume:
                summary_p = row_lit_summary_path(summary_dir, csv_path.stem, row_num)
                done_p = row_done_path(summary_dir, csv_path.stem, row_num)
                if summary_p.is_file():
                    stage_line(
                        "check-uncovered",
                        f"row {row_num}: skip (--resume: lit summary exists: {summary_p})",
                    )
                    continue
                if done_p.is_file():
                    stage_line(
                        "check-uncovered",
                        f"row {row_num}: skip (--resume: marker exists: {done_p})",
                    )
                    continue

            if _csv_row_marked_skip(row):
                stage_line(
                    "check-uncovered",
                    f"row {row_num}: skip (CSV skip column is 1)",
                )
                continue

            file_s = _cell(row, "file")
            line_s = _cell(row, "line")
            replacement = _cell(row, "line_replacement", "replacement_line")
            original_expect = _cell(row, "line_original", "original_line")

            if not file_s or not line_s or replacement is None:
                stage_line(
                    "check-uncovered",
                    f"error: row {row_num}: missing file, line, or replacement",
                )
                return 1

            try:
                line_no = int(line_s)
            except ValueError:
                stage_line(
                    "check-uncovered",
                    f"error: row {row_num}: bad line number {line_s!r}",
                )
                return 1

            src_path = Path(file_s)
            if not src_path.is_file():
                stage_line(
                    "check-uncovered",
                    f"error: row {row_num}: source not found: {src_path}",
                )
                return 1

            stage_line(
                "check-uncovered",
                f"row {row_num}: patch {src_path}:{line_no}",
            )

            try:
                prior = _apply_line_replacement(src_path, line_no, replacement)
            except (OSError, ValueError) as e:
                stage_line("check-uncovered", f"error: row {row_num}: patch failed: {e}")
                return 1

            rc_build_result: int | None = None
            rc_check_result: int | None = None
            try:
                if original_expect is not None:
                    current_lines = prior.splitlines()
                    li = line_no - 1
                    if 0 <= li < len(current_lines) and current_lines[li] != original_expect:
                        stage_line(
                            "check-uncovered",
                            f"error: row {row_num}: line {line_no} does not match "
                            f"original_line from CSV",
                        )
                        return 1

                try:
                    rc_build_result, rc_check_result, check_all_out = (
                        _run_full_ninja_then_check_all(build_dir)
                    )
                except OSError as e:
                    stage_line(
                        "check-uncovered",
                        f"error: row {row_num}: could not run ninja: {e}",
                    )
                    return 1

                if rc_build_result != 0:
                    stage_line(
                        "check-uncovered",
                        f"error: row {row_num}: ninja failed ({rc_build_result})",
                    )
                    return 1
                if rc_check_result != 0:
                    _write_lit_summary_excerpt(
                        check_all_out,
                        summary_dir,
                        csv_path.stem,
                        row_num,
                    )
                    stage_line(
                        "check-uncovered",
                        f"row {row_num}: ninja check-all exited {rc_check_result} (non-fatal; continuing)",
                    )
            finally:
                try:
                    src_path.write_text(prior, encoding="utf-8")
                except OSError as e:
                    stage_line(
                        "check-uncovered",
                        f"error: row {row_num}: restoring {src_path} failed: {e}",
                    )
                    return 1

            if (
                args.resume
                and rc_build_result == 0
                and rc_check_result == 0
            ):
                summary_dir.mkdir(parents=True, exist_ok=True)
                row_done_path(summary_dir, csv_path.stem, row_num).touch()

    return 0
