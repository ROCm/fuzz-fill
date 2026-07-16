from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Default for llvm-lit ``--filter=`` when none is passed.
DEFAULT_LIT_FILTER = "CodeGen/AMDGPU"
DEFAULT_RUN_CONFIG_FILE = "run_config.json"

DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "coverage_output" / f"cov_<timestamp>"

# CSV file names
CSV_FILE_NAME_COVERED = "covered_by_opt_or_llc.csv"
DEFAULT_LLC_ADDRESS_LINE_MAP_FILE = "llc_address_line_map.csv"
DEFAULT_OPT_ADDRESS_LINE_MAP_FILE = "opt_address_line_map.csv"
DEFAULT_LINE_COVERAGE_SUMMARY_FILE = "line_coverage_summary.csv"
DEFAULT_NEW_COVERAGE_CSV = "new_coverage.csv"
DEFAULT_TARGET_LINES_REPORT = "target_lines_uncovered.csv"
DEFAULT_LIT_FAILURES_REPORT = "lit_failures.json"
DEFAULT_TIMINGS_FILE = "timings.csv"

# Sancov constants
UNION_BATCH_SIZE = 200

# llvm-lit parallelism cap (workaround for high core-count Docker hosts)
MAX_LIT_JOBS = 384

# New test flags
TEST_FLAGS = ["-O0", "-O1", "-O2", "-O3"]