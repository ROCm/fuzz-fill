# fuzz-fill

Fuzzing to fill test suite coverage gaps in LLVM.

fuzz-fill supports two main workflows:

1. **Find coverage gaps in the existing LLVM test suite and fill them with fuzz-generated tests** — measure what the suite already covers, run a fuzz corpus, and identify which tests hit lines the suite misses; then reduce those tests into minimal LIT cases.
2. **Find uncovered lines in a commit** — list source lines added by a patch that the regression suite still does not fully cover.

## Setup

### Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### LLVM builds

You need **two** builds of the **same** LLVM revision:

| Build | Purpose | How |
|-------|---------|-----|
| **Uninstrumented** | `sancov` merge/symbolize, `llvm-reduce`, LIT helper tools | `./scripts/build-llvm.sh /path/to/clang /path/to/clang++ llvm-project llvm-project/build-uninstrumented` |
| **SanitizerCoverage** | Run `llvm-lit`, instrumented `llc`/`opt` | `./scripts/build-llvm-sancov.sh ./scripts/allowlist-amdgpu.txt llvm-project llvm-project/build-uninstrumented llvm-project/build-sancov` |

Run `build-llvm.sh` first. The sancov build is compiled with `clang`/`clang++` from the uninstrumented `bin/`.

**`python -m coverage test-suite`** patches **`<instrumented-build>/test/lit.site.cfg.py`** so LIT forwards **`UBSAN_OPTIONS`** to every test subprocess. The patch is idempotent and is re-applied if CMake regenerates that file.

The example scripts below assume paths like:

- `$LLVM/build/bin` — uninstrumented tools (including `sancov`)
- `$LLVM/build-amdgpu-bb/bin` — instrumented `llvm-lit`, `llc`, and `opt`

Adjust these to match your trees before running.

---

## Workflow 1: Fill suite coverage gaps with fuzz-generated tests

**When to use this:** you want to improve LLVM test coverage in a target area (e.g. AMDGPU `CodeGen`) by finding lines the regression suite does not hit, then checking whether fuzz-generated tests can cover those gaps.

**Reference script:** [`scripts/test_coverage.sh`](scripts/test_coverage.sh)

### What it does

```text
test-suite  →  new-tests  →  diff  →  reduce
(suite baseline)  (fuzz corpus)  (gaps filled)  (minimal LIT tests)
```

1. **`test-suite`** — run a filtered slice of the LLVM LIT suite with SanitizerCoverage to establish baseline coverage: which source lines the existing tests already hit.
2. **`new-tests`** — run a directory of fuzz-generated tests (`.ll` / `.bc`) through instrumented `llc` and collect their coverage.
3. **`diff`** — compare fuzz-test coverage against the suite baseline and report which fuzz tests cover lines the suite misses — these are candidate gap-fillers.
4. **`reduce`** — shrink promising tests into minimal cases suitable for adding to the suite (see [Reduce interesting tests](#reduce-interesting-tests) below).

### Configure and run

Edit the variables at the top of `scripts/test_coverage.sh`:

| Variable | Meaning |
|----------|---------|
| `LLVM` | Path to your `llvm-project` checkout |
| `LLVM_BIN` | Uninstrumented `bin` directory |
| `INSTRUMENTED_BIN_DIR` | Instrumented `bin` directory |
| `OUTPUT_DIR` | Root for all artifacts from this workflow |
| `TESTS_DIR` | Directory of fuzz-generated `.ll` / `.bc` files to scan |
| `FILTER` | LIT `--filter=` prefix (e.g. `CodeGen/AMDGPU`) |

Then run from the fuzz-fill repo root:

```bash
./scripts/test_coverage.sh
```

By default the script runs only **`test-suite`**. Uncomment the **`new-tests`** and **`diff`** blocks when you are ready for the full pipeline.

### Key outputs

Under `$OUTPUT_DIR`:

| Path | Contents |
|------|----------|
| `test_suite/test_coverage.csv` | Suite baseline: source lines the LIT run covers (joint llc + opt, full-line mode) |
| `test_suite/processed_sancov/` | Merged, symbolized symcov files — reuse these if you re-run `diff` with different new tests |
| `new_tests/raw_sancov/` | Per-test raw sancov shards |
| `diff/new_coverage.csv` | **Main result** — columns `test`, `file`, `line`, `covered-points`: fuzz tests that fill suite coverage gaps |

`new_coverage.csv` is the input for testcase reduction in step 4.

---

## Workflow 2: Uncovered lines in a commit

**When to use this:** you landed a patch and want a precise list of **added** source lines that the regression suite still does not fully cover.

**Reference script:** [`scripts/test_coverage_commit_lines.sh`](scripts/test_coverage_commit_lines.sh)

### What it does

```text
added-lines  →  test-suite  →  target-lines
(from git)     (baseline)      (uncovered added lines)
```

1. **`added-lines`** — parse `git show` for a commit and list every line added on the right-hand side of the diff.
2. **`test-suite`** — same baseline coverage run as Workflow 1 (produces symcov under `processed_sancov/`).
3. **`target-lines`** — for each line in the target CSV, check whether **every** SanitizerCoverage point on that line is off under the suite run. Fully uncovered lines go into the report; partially covered lines are counted but omitted from the CSV.

Step 3 does **not** re-run LIT, so you can repeat it with different `added-lines.csv` inputs as long as the `test-suite` symcov artifacts are still present.

### Configure and run

Edit the variables at the top of `scripts/test_coverage_commit_lines.sh`:

| Variable | Meaning |
|----------|---------|
| `LLVM` | `llvm-project` checkout (same tree `added-lines` diffs against) |
| `LLVM_BIN` / `INSTRUMENTED_BIN_DIR` | Same as Workflow 1 |
| `OUTPUT_DIR` | Root for all artifacts |
| `FILTER` | LIT filter for the baseline run |
| `COMMIT` | Revision to analyse (`HEAD`, a hash, `main~3`, …) |

Then run from the fuzz-fill repo root:

```bash
./scripts/test_coverage_commit_lines.sh
```

### Key outputs

Under `$OUTPUT_DIR`:

| Path | Contents |
|------|----------|
| `added-lines/added-lines.csv` | Added lines from the commit (`path`, `line_no`, `text`) |
| `test_suite/processed_sancov/` | Baseline symcov (required by `target-lines`) |
| `commit_lines_report/commit_lines_uncovered.csv` | **Main result** — added lines where every suite point on that line is off |

---

## Reduce interesting tests

Once you have `new_coverage.csv` (Workflow 1) or a specific uncovered line you want to target (Workflow 2), use the **`reduce`** module to shrink a testcase while preserving coverage or crash behaviour.

Each row in `new_coverage.csv` maps a test file to a source location and one or more SanitizerCoverage point ids (`covered-points`). Turn a row into a reduction job by pointing a JSON config at the testcase, setting `file` / `line`, and wiring an interestingness script that checks the coverage address.

Examples:

- [`example/amd/new-test-1/`](example/amd/new-test-1/) — minimal IR reduction from a coverage row
- [`scripts/reduce_amd_coverage_based.sh`](scripts/reduce_amd_coverage_based.sh), [`scripts/batch_reduce_using_coverage.sh`](scripts/batch_reduce_using_coverage.sh) — batch reduction from a coverage CSV

```bash
python -m reduce --config example/amd/new-test-1/config.json --llvm-bin "$LLVM/build/bin"
```

See `python -m reduce --help` and the checked-in `example/*/config.json` files for pipeline options.

---

## CLI reference

The workflows above call these modules. Use `--help` on any command for the full flag list.

| Command | Role in workflows |
|---------|-------------------|
| `python -m coverage test-suite` | Baseline LIT coverage (both workflows) |
| `python -m coverage new-tests` | Coverage from a fuzz-generated test corpus (Workflow 1) |
| `python -m coverage diff` | Suite gaps filled by fuzz tests (Workflow 1) |
| `python -m coverage target-lines` | Uncovered target lines vs baseline symcov (Workflow 2) |
| `python -m added_lines` | Lines added by a git commit (Workflow 2) |
| `python -m reduce` | Testcase reduction |

---

## Docker test image

The Docker image bundles a pinned LLVM revision, both instrumented and uninstrumented builds, and a fuzz-fill venv. Use it when you want to run integration tests or experiment without building LLVM locally.

**Scripts:** [`scripts/build-image.sh`](scripts/build-image.sh), [`scripts/tmp-container.sh`](scripts/tmp-container.sh)

### Build

From the repo root (first build compiles LLVM and can take a while):

```bash
./scripts/build-image.sh
```

The image is tagged `fuzz-fill-test:latest` by default. Override with `IMAGE_NAME` / `IMAGE_TAG`. The build passes your host `UID`, `GID`, and username so files created in the container are owned by you.

Inside the image, LLVM and fuzz-fill live at fixed paths (required by `lit.site.cfg.py`):

| Path | Contents |
|------|----------|
| `/work/llvm-project` | LLVM source checkout |
| `/work/llvm-build-uninstrumented/bin` | Uninstrumented tools (`sancov`, …) |
| `/work/llvm-build-sancov/bin` | SanitizerCoverage build (`llvm-lit`, `llc`, `opt`) |
| `/work/fuzz-fill` | fuzz-fill checkout with venv |

### Run a container

```bash
./scripts/tmp-container.sh                              # interactive shell
./scripts/tmp-container.sh --bind-repo                  # shell with host repo mounted
./scripts/tmp-container.sh --bind-repo <command> [args] # one-shot command
```

Without `--bind-repo`, the container uses the fuzz-fill copy baked into the image.

With `--bind-repo`, your local checkout is mounted at `/work/fuzz-fill`.

### Run integration tests in Docker

```bash
./scripts/tmp-container.sh ./integration-tests/test.sh \
  --venv ./venv \
  --llvm-build /work/llvm-build-uninstrumented/bin \
  --llvm-sancov-build /work/llvm-build-sancov/bin \
  --llvm-src /work/llvm-project \
  -v integration-tests/
```

Use `--bind-repo` when testing local changes to fuzz-fill:

```bash
./scripts/tmp-container.sh --bind-repo ./integration-tests/test.sh \
  --venv ./venv \
  --llvm-build /work/llvm-build-uninstrumented/bin \
  --llvm-sancov-build /work/llvm-build-sancov/bin \
  --llvm-src /work/llvm-project \
  -v integration-tests/
```

---

## Running integration tests

Integration tests need both LLVM `bin` directories (same version). Locally:

```bash
./integration-tests/test.sh \
  --venv ./venv/ \
  --llvm-build llvm-project/build-uninstrumented/bin/ \
  --llvm-sancov-build llvm-project/build-sancov/bin/ \
  --llvm-src llvm-project/ \
  integration-tests/
```

Or use the [Docker test image](#docker-test-image) paths above.

`--llvm-build` is the uninstrumented tree; `--llvm-sancov-build` is the SanitizerCoverage build; `--llvm-src` is the llvm-project checkout root (used as `%llvm-repo` in tests).
