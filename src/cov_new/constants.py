from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Default for llvm-lit ``--filter=`` when none is passed (matches ``coverage.constants``).
DEFAULT_LIT_FILTER = "CodeGen/AMDGPU"
DEFAULT_PATH_FILTER = "llvm/lib/Target/AMDGPU"

DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "coverage_output" / f"cov_<timestamp>"

# CSV file names
CSV_FILE_NAME_COVERED = "covered_by_opt_or_llc.csv"
DEFAULT_LLC_ADDRESS_LINE_MAP_FILE = "llc_address_line_map.csv"
DEFAULT_JOINT_LLC_AND_OPT_COVERAGE_FILE = "joint_llc_and_opt_coverage.csv"

# Sancov constants
UNION_BATCH_SIZE = 200