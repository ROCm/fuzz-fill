# Default coverage output folder names under <repo>/data/coverage_output/ (see _config_from_*_args).
_COVERAGE_DIR_PREFIX_RUN = "test_suite"
_COVERAGE_DIR_PREFIX_NEW_TESTS = "new_tests"
_COVERAGE_DEFAULT_FOLDER_RUN = f"{_COVERAGE_DIR_PREFIX_RUN}_<timestamp>"
_COVERAGE_DEFAULT_FOLDER_NEW_TESTS = f"{_COVERAGE_DIR_PREFIX_NEW_TESTS}_<timestamp>"
# Subdirectory under --existing-sancov-dir for report CSVs (unique id avoids collisions).
_NEW_TESTS_OUTPUT_IN_SANCOV_PREFIX = "new_tests_output"
