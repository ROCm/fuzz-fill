from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "diff_output" / "run_<timestamp>"

ADDED_LINES_FILENAME = "added_lines.csv"
