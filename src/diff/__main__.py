from __future__ import annotations

import argparse
import csv
import io
from datetime import datetime
from pathlib import Path

from diff.added_lines import AddedLine, collect_added_lines
from diff.constants import ADDED_LINES_FILENAME, DEFAULT_OUTPUT_DIR


def add_shared_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--debug", action="store_true", default=False)


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
    sub = parser.add_subparsers(
        dest="subcmd",
        metavar="{added-lines}",
        required=True,
    )
    p_lines = sub.add_parser(
        "added-lines",
        help="Print every line introduced by the given commit (git show / unified diff).",
    )
    add_shared_arguments(p_lines)
    p_lines.add_argument(
        "--llvm-repo",
        type=Path,
        required=True,
        help="Path to the llvm-project (or any) git checkout.",
    )
    p_lines.add_argument(
        "--commit",
        type=str,
        required=True,
        help=(
            "Commit hash or revision accepted by git show (e.g. abc123, HEAD~1). "
            "Uses git show --first-parent so merge commits diff against the first parent."
        ),
    )

    args = parser.parse_args()

    if args.debug:
        print("Debug mode enabled", flush=True)

    if args.subcmd != "added-lines":
        print(f"Unknown subcommand: {args.subcmd}", flush=True)
        raise SystemExit(1)

    repo = args.llvm_repo.resolve()
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
