from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "coverage_output" / f"cov_<timestamp>"

COVERAGE_DIR_PREFIX_TEST_SUITE = "test_suite"
COVERAGE_DIR_PREFIX_NEW_TESTS = "new_tests"
COVERAGE_DIR_PREFIX_DIFF = "diff"
COVERAGE_DEFAULT_FOLDER_TEST_SUITE = f"{COVERAGE_DIR_PREFIX_TEST_SUITE}_<timestamp>"
COVERAGE_DEFAULT_FOLDER_NEW_TESTS = f"{COVERAGE_DIR_PREFIX_NEW_TESTS}_<timestamp>"
COVERAGE_DEFAULT_FOLDER_DIFF = f"{COVERAGE_DIR_PREFIX_DIFF}_<timestamp>"

# CSV file names
CSV_FILE_NAME_COVERED = "covered_by_opt_or_llc.csv"

# Sancov constants
UNION_BATCH_SIZE = 200