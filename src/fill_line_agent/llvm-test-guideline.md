# Guideline for contributing new tests

When you add a test for a line the existing suite never hits, follow these steps in order.

1. **Choose an existing test file that already covers this code, and reuse a run command that file already has.**
   - On a pull request, look first at the test files that pull request already changes. If none of those fit, look at other existing tests.
   - In the chosen file, look for the pass and for similar cases. Write your new case for that file, and let it run under a command the file already uses.
   - Add a new run command only when no existing one can reach the line. Suggest a new file only when no suitable file exists.

2. **Hit the line with the same kind of input and run command nearby tests already use.**
   - Prefer the host file’s existing form (usually `.ll` through the normal `llc` / `opt` pipeline).
   - Use a single-pass invocation (`-run-pass` / `-passes=`) or IR/MIR taken from just before that pass only when neighboring tests for that pass already do so, or when a full-pipeline IR test cannot reach the line without awkward extra flags.
   - Keep the input small in that established style — do not invent a new MIR or single-pass harness.

3. **Change only your new case.** Do not rewrite shared run commands or invent a one-off mode just for your function. Prefer the same triples, CPUs, opt levels, and CHECK prefixes that nearby cases in the host file already use. If your case needs different expected output for another CPU (or another RUN / FileCheck prefix the file already uses), add checks only for that case.

4. **Keep the test small, and name it for the case.** Cut it down until it is the smallest input that still hits the line. Name the function for that case, for example `test_bool_v16_eq`.

5. **Write expected results for your new case with the tool meant for that file.** Keep the note that says the checks were generated when the host file uses one. Only your new case needs CHECKs here.

6. **Copy the style of the host file you chose.** Match how nearby tests pass their input, declare functions, pick targets, and run extra checks.
