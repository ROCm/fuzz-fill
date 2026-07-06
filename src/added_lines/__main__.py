from __future__ import annotations

import argparse
import csv
import io
from datetime import datetime
from pathlib import Path

from added_lines.added_lines import AddedLine, collect_added_lines
from added_lines.constants import ADDED_LINES_FILENAME, DEFAULT_OUTPUT_DIR
from fuzz_fill.env import FUZZ_FILL_LLVM_REPO, path_from_flag_or_env
from fuzz_fill.log import add_log_level_argument, configure_logging


def resolve_output_dir(path: Path) -> Path:
    s = str(path)
    if "<timestamp>" in s:
        return Path(
            s.replace("<timestamp>", datetime.now().strftime("%Y%m%d-%H%M%S"))
        )
    return path


def format_added_lines_csv(rows: list[AddedLine]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["path", "line_no", "text"])
    for row in rows:
        w.writerow([row.path, row.line_no, row.text])
    return buf.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List source lines added in a single LLVM git commit."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--debug", action="store_true", default=False)
    parser.add_argument(
        "--llvm-repo",
        type=Path,
        default=None,
        help=f"Path to the llvm-project (or any) git checkout (or set {FUZZ_FILL_LLVM_REPO}).",
    )
    parser.add_argument(
        "--commit",
        type=str,
        required=True,
        help=(
            "Commit hash or revision accepted by git show (e.g. abc123, HEAD~1). "
            "Uses git show --first-parent so merge commits diff against the first parent."
        ),
    )
    add_log_level_argument(parser)

    args = parser.parse_args()
    configure_logging(args.log_level)

    if args.debug:
        print("Debug mode enabled", flush=True)

    repo = path_from_flag_or_env(
        args.llvm_repo, FUZZ_FILL_LLVM_REPO, flag_name="--llvm-repo"
    )
    out_dir = resolve_output_dir(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = collect_added_lines(repo, args.commit)
    csv_text = format_added_lines_csv(rows)

    out_file = out_dir / ADDED_LINES_FILENAME
    out_file.write_text(csv_text, encoding="utf-8")

    if args.debug:
        print(f"Wrote {len(rows)} added lines to {out_file}", flush=True)

    print(csv_text, end="")


if __name__ == "__main__":
    main()
