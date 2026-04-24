### Coverage

- Build LLVM with coverage
- Steps within the coverage module:
    - Get baseline coverage of the test suite
    - Get coverage of new tests
    - Identify new tests that have additional coverage relative to the baseline


### Arguments
Coverage module has 3 subcommands:
- test-suite - gets baseline coverage for the test suite
- new-tests - gets coverage for the new test(s)
- diff - gets incremental coverage for new test(s) relative to the baseline test suite