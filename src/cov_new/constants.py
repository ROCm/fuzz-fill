from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Default for llvm-lit ``--filter=`` when none is passed (matches ``coverage.constants``).
DEFAULT_LIT_FILTER = "CodeGen/AMDGPU"

DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "coverage_output" / f"cov_<timestamp>"

# CSV file names
CSV_FILE_NAME_COVERED = "covered_by_opt_or_llc.csv"

# Sancov constants
UNION_BATCH_SIZE = 200