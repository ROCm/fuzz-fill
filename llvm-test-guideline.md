# Guideline for contributing new tests

When you add a test for a line the existing suite never hits, follow these steps in order.

1. **Add the case to a test file that already covers this code, and reuse a run command that file already has.**
   - On a pull request, look first at the test files that pull request already changes. If none of those fit, look at other existing tests.
   - In the chosen file, look for the pass and for similar cases. Put a new function there, and let it run under a command the file already uses.
   - Add a new run command only when no existing one can reach the line. Start a new file only when no suitable file exists.

2. **Cover the gap by running the related pass directly, with the same kind of input those tests already use.**
   - If that pass can be invoked on its own, take the IR or MIR from just before it runs in the pipeline, and write the test in that form.
   - Use the shortest path that still hits the line.

3. **Change only your new case.** Leave the other functions, their run commands, and their expected results as they are. If your case behaves differently for another CPU, give it its own expected results. If the file mixes compiler modes, pin the mode the nearby cases use.

4. **Keep the test small, and name it for the case.** Cut it down until it is the smallest input that still hits the line. Name the function for that case, for example `test_bool_v16_eq`.

5. **Update the expected results with the tool meant for that file.** Keep the note that says the checks were generated. Afterward, check that every existing function still has its results.

6. **Copy the style of the file you are editing.** Match how nearby tests pass their input, declare functions, pick targets, and run extra checks.
