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

### Workflow
- test-suite 
    - run tests
    - merge sancov files to get aggregated coverage sancovs
        - for llc
        - for opt
    - get symcovs
    - get the union of llc and opt coverage using the llc address-line mapping
    - output:
        - raw_sancov:
            - individual sancov file for each test
        - processed_sancov:
            - merged sancov and symcov for llc
            - merged sancov and symcov for opt
        - .csv list of all addresses covered by either llc or opt using the llc address-line mapping
        - .csv mapping of all llc addresses to lines (point-symbol-info from the llc symcov) 

- new-tests
    - run tests
    - output:
        - sancov file for each new test