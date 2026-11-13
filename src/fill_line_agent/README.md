# Gap-Filling Agent

LLM agent that writes LIT tests for uncovered LLVM source lines, implemented in the `fill-line` CLI.

## fill-line

`fill-line` receives one or more target lines.
Each LLM session still aims at a single line. Over a series of rounds it
proposes `opt` or `llc` tests aimed at that line, uses nearby coverage to
guide the next attempt, and picks the tool and flags from the PR diff and
source.

### What it needs

- Instrumented `opt` and/or `llc` binaries plus `sancov`.
- An LLVM source tree and a PR/commit diff
  for context.
- An LLM gateway subscription key (`--api-key`, `--key-file`, or
  `FUZZ_FILL_API_KEY`).
- An LLM gateway base URL (`--base-url`, `--base-url-file`, or
  `FUZZ_FILL_BASE_URL`).
- An NTID for the gateway `user` header (`--user-ntid` or `USER_NTID`).

To gather those inputs from a prior `PR gap analysis` run:

```bash
scripts/fill-line/setup-context.sh --pr 12345 --out ./context/pr-12345
# Reuse objects from an existing llvm-project clone (optional):
scripts/fill-line/setup-context.sh --pr 12345 --out ./context/pr-12345 \
  --reference /path/to/llvm-project
source ./context/pr-12345/context.env
```

That leaves an LLVM checkout, PR diff, instrumented tools, and uncovered
targets under `--out`. `context.env` sets `LLVM_SRC`, `DIFF`, and
`INSTRUMENTED_BIN_DIR` for `--llvm-src`, `--diff`, and
`--instrumented-bin-dir`.

### Session flow

The agent loops:

1. Choose `opt` or `llc` and its flags for the next test attempt (or stop if
   neither can help).
2. Write a path-conditions analysis for the reachability of the target line,
   by reading the source around it. Each condition must hold to execute the
   line. For each one the agent records:
   - whether it currently looks satisfied, unsatisfied, or unknown
   - why — for example “unknown: not tried yet” or “unsatisfied: line 133
     hit, line 134 missed”
3. Propose a candidate that tries to make one of those conditions true, and
   run it.
4. Use nearby coverage to refresh the status of the path conditions, then 
   revise the analysis and the next attempt.

The loop ends when the line is covered, when the agent concludes it cannot
cover it with the available tools, or when the budget is exhausted. When the
agent accepts a test, a final step re-runs that test on the instrumented
binary and confirms the target line, independently of the LLM.

### Multiple targets

Repeat `--target` for several lines. Each gets its own LLM session; after a
session ends, any remaining line already covered by a prior run is skipped.
Several targets write `summary.json` and `lines/<index>-…/`; optional
`--max-*-total` caps apply across the whole batch.

### Tools (MCP)

The agent has the following tools/actions available at each round.

| Tool | Purpose |
|---|---|
| `read_diff` / `read_source` / `grep_source` | Inspect PR and LLVM sources |
| `instrumented_lines` | Static instrumented lines in a range |
| `select_tool` | Choose `opt`, `llc`, or `none` |
| `record_analysis` | Save the current path-conditions analysis |
| `run_candidate` | Run a proposed `opt`/`llc` test; report target and nearby coverage |
| `compare_output` / `show_streams` | Inspect the latest run |
| `accept` / `give_up` | End the session (`accept` can pick any covering run) |

Once a run covers the target, the agent accepts it if it is a positive test.
Otherwise it gets up to 5 more runs to find a positive variant before
accepting the best covering run. If the session ends on budget without an
accept, the harness accepts the best covering run itself.

If the agent gives up, it can leave feedback on what would have helped, so
later sessions can improve.

### Outputs

Written under `--out-dir`. Re-running into the same directory clears previous
session artifacts first.

| Path | Contents |
|---|---|
| `result.json` | Status, history, analysis, quota, stats, usage |
| `analysis.json` | Latest analysis plus every earlier one |
| `responses.jsonl` | Per-LLM-response timing, tokens, text, tool calls |
| `attempts/run_NNN.{ll,mir}` | Every candidate (with `Testing:` header) |
| `test.{ll,mir}` | Accepted lit test (on success) |
| `fuzz_fill.log` | Session log (`--log-to-file`) |
| `summary.json` | Multi-target batch result |
| `lines/<index>-…/` | Per-line outputs when several targets are given |

Terminal statuses / exit codes (single target):

| Status | Exit | Meaning |
|---|---|---|
| `covered` | 0 | Accepted and check-line passed |
| `gave_up` | 1 | Budget / agent give-up / validation fail |
| `not_instrumented` | 2 | No tool instruments the target |
| `likely_unreachable` | 3 | Unreachable with current tools (evidence-backed) |

Multi-target exit codes: `0` if every line is covered (session or collateral),
`2` if none are instrumented, `3` if every instrumented line is
`likely_unreachable`, otherwise `1`. Each summary entry may set
`covered_by` to `session` or `collateral`.

### Example

```bash
./venv/bin/fill-line \
  --target llvm/lib/Transforms/Scalar/StructurizeCFG.cpp:134 \
  --target llvm/lib/Transforms/Scalar/StructurizeCFG.cpp:1381 \
  --llvm-src /path/to/llvm-project \
  --diff /path/to/pr.diff \
  --api-key "$KEY" \
  --base-url "$GATEWAY_URL" \
  --user-ntid "$USER_NTID" \
  --instrumented-bin-dir /path/to/instrumented-tools/bin \
  --out-dir ./out-structurize \
  --work-dir ./work-structurize \
  --tools-runner docker \
  --model sonnet \
  --effort low \
  --thinking-tokens 0 \
  --max-runs 40 \
  --max-turns 200 \
  --max-wall-s 1800 \
  --max-wall-s-total 7200 \
  --log-level info \
  --log-to-file
```

`--tools-runner docker` matters when the instrumented binaries come from a CI
artifact (for example via `setup-context.sh`): they are built on Ubuntu 24.04
and may not run on an older host glibc.

To keep sessions short:

- `--effort low` / `--thinking-tokens 0` — shorter replies
- `--model haiku` — faster model for easy lines
- `--max-wall-s` / `--max-wall-s-total` — per-session and batch time limits
  (recommended; USD cost may not report through a custom gateway)

`check-line` re-runs an accepted test on the instrumented binary and checks
whether a given line is covered, without calling the LLM. Useful when one test
may cover several lines:

```bash
./venv/bin/check-line \
  --test ./out-134/test.ll \
  --target llvm/lib/Transforms/Scalar/StructurizeCFG.cpp:1381 \
  --instrumented-bin-dir /path/to/instrumented-tools/bin \
```

### Running instrumented binaries in Docker

CI-built `opt` / `llc` / `sancov` may not run on the host if shared libraries
(especially glibc) are too old. `scripts/fill-line/instrumented-tools/` is a
small Ubuntu image for that case. Build it once, then pass
`--tools-runner docker` to `fill-line` or `check-line`:

```bash
scripts/fill-line/instrumented-tools/build.sh
```

### Layout

```
src/fill_line_agent/
  __main__.py             # fill-line CLI
  batch.py                # multi-target loop helpers + total budgets
  check_line.py           # check-line CLI
  session.py              # SDK session loop + system prompt
  session_state.py        # quotas, analysis, budgets
  tools.py                # MCP tools closed over session state
  oracle.py               # run opt/llc + measure coverage
  instrumented.py         # load binaries, build symcov indexes
  responses.py            # per-response timing / content log
  render.py               # attempts, analysis.json, result.json
  tool_runner.py          # host or Docker execution
  args_policy.py          # argv allowlist for opt/llc
  ping.py                 # LLM gateway preflight

scripts/fill-line/
  setup-context.sh        # download PR gap artifacts + checkout for fill-line
  instrumented-tools/     # Docker image to run instrumented opt/llc/sancov
```
