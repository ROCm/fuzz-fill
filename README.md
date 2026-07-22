# fuzz-fill

Fuzzing to fill test suite coverage gaps in LLVM.

fuzz-fill supports two main workflows:

1. **Find coverage gaps in the existing LLVM test suite and fill them with fuzz-generated tests** — measure what the suite already covers, run a fuzz corpus, and identify which tests hit lines the suite misses; then reduce those tests into minimal LIT cases.
2. **Find uncovered lines in a commit** — list source lines added by a patch that the regression suite still does not fully cover.

See [here](#contributions) for a list of tests contributed to LLVM.

## Quick start (Docker)

Try [Workflow 2](#workflow-2-uncovered-lines-in-a-commit), which reports lines added as part of a commit that the LLVM test suite does not cover.

Prerequisites:
- [Docker](https://docs.docker.com/)
- A local `llvm-project` checkout

```bash
git clone https://github.com/ROCm/fuzz-fill.git
cd fuzz-fill
```

**LLVM pull request** — requires [GitHub CLI](https://cli.github.com/) (`gh`). Builds a PR image and runs detection in one step (first build compiles LLVM in Docker and can take a while):

```bash
./scripts/docker/pr-cov-gaps-detection.sh \
  --build-image \
  --llvm-repo /path/to/llvm-project \
  --pr-id 203468 \
  --backend-tests amdgpu \
  --output-dir ./data/pr-cov-gaps-203468 \
  -j "$(nproc)"
```

Use `spirv` instead of `amdgpu` for SPIR-V backend tests.

**Local commit** — build from your `llvm-project` and then run:

```bash
./scripts/docker/build-image.sh --llvm-dir /path/to/llvm-project --allowlist amdgpu -j "$(nproc)"

./scripts/docker/pr-cov-gaps-detection.sh \
  --image fuzz-fill-test:latest \
  --output-dir ./data/my-commit \
  --commit HEAD \
  -j "$(nproc)"
```

Replace `HEAD` with a hash, branch, or `main~3` as needed.

**Result (both paths):** `<output-dir>/commit_lines_report/target_lines_uncovered.csv` — added source lines that are not covered by the test suite. See [Workflow 2](#workflow-2-uncovered-lines-in-a-commit) and [Docker test image](#docker-test-image) for more options.

## Table of Contents

- [Quick start (Docker)](#quick-start-docker)
- [Setup](#setup)
  - [Python environment](#python-environment)
  - [LLVM builds](#llvm-builds)
- [Workflow 1: Fill suite coverage gaps with fuzz-generated tests](#workflow-1-fill-suite-coverage-gaps-with-fuzz-generated-tests)
- [Workflow 2: Uncovered lines in a commit](#workflow-2-uncovered-lines-in-a-commit)
- [Reduce interesting tests](#reduce-interesting-tests)
- [CLI reference](#cli-reference)
  - [Environment variables](#environment-variables)
- [Docker test image](#docker-test-image)
  - [Build](#build)
  - [Build from an LLVM pull request](#build-from-an-llvm-pull-request)
  - [Workflow 2: PR coverage gap detection](#workflow-2-pr-coverage-gap-detection)
  - [Run integration tests](#run-integration-tests)
  - [Run a container](#run-a-container)
- [Tests](#tests)
- [Contributions](#contributions)
  - [AMDGPU](#amdgpu)
  - [SPIR-V](#spir-v)

## Setup

### Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### LLVM build

You need an official **LLVM GitHub release** as bootstrap and one **SanitizerCoverage** build of llvm-project at the matching tag:

| Component | Purpose | How |
|-----------|---------|-----|
| **Release bootstrap** | `clang`, `clang++` for compiling LLVM | Download [LLVM release](https://github.com/llvm/llvm-project/releases) (e.g. `LLVM-22.1.8-Linux-X64.tar.xz`) |
| **SanitizerCoverage** | Unified build tree: instrumented `llc`/`opt`, Release LIT helpers, `llvm-lit`, `sancov` | `./scripts/build-llvm-sancov.sh ./scripts/allowlist-amdgpu.txt llvm-project llvm-project/build-sancov --bootstrap-bin /path/to/LLVM-22.1.8/bin` |

`build-llvm-sancov.sh` runs two partial builds from the same source: **`llvm-tblgen` is built from the source tree first**, then a **Release** tree for target-agnostic LIT helpers plus **`sancov`**, and a **Debug** SanitizerCoverage tree for **`llc`**, **`opt`**, and target-linked helpers (`llvm-mc`, `llvm-objdump`, …). Release tools are copied into the instrumented tree's `bin/`; `llvm-lit` is generated there by cmake. The bootstrap release supplies **clang/clang++ only** (TableGen must match the source).

**`python -m coverage baseline`** patches **`<instrumented-build>/test/lit.site.cfg.py`** so LIT forwards **`UBSAN_OPTIONS`** to every test subprocess. The patch is idempotent and is re-applied if CMake regenerates that file.

The example scripts below assume paths like:

- `$LLVM/build-sancov/bin` — unified build (`llvm-lit`, instrumented `llc`/`opt` + target helpers, Release `sancov`/other LIT helpers)

Adjust these to match your trees before running.

---

## Workflow 1: Fill suite coverage gaps with fuzz-generated tests

**When to use this:** you want to improve LLVM test coverage in a target area (e.g. AMDGPU `CodeGen`) by finding lines the regression suite does not hit, then checking whether fuzz-generated tests can cover those gaps.

**Reference script:** [`scripts/test_coverage.sh`](scripts/test_coverage.sh)

### What it does

```text
baseline  →  candidate-test  →  incremental  →  reduce
(suite baseline)  (fuzz corpus)  (gaps filled)  (minimal LIT tests)
```

1. **`baseline`** — run a filtered slice of the LLVM LIT suite with SanitizerCoverage to establish baseline coverage: which source lines the existing tests already hit.
2. **`candidate-test`** — run a directory of fuzz-generated tests (`.ll` / `.bc`) through instrumented `llc` and collect their coverage.
3. **`incremental`** — compare fuzz-test coverage against the suite baseline and report which fuzz tests cover lines the suite misses — these are candidate gap-fillers. A fuzz test qualifies for a line only when it fully covers that line and the line appears in the baseline `line_coverage_uncovered.csv`.
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
| `FILTER` | llvm-lit `--filter=` regex or prefix (default: `(^|/)AMDGPU/` for all AMDGPU folders; use `CodeGen/AMDGPU` for CodeGen only) |

Then run from the fuzz-fill repo root:

```bash
./scripts/test_coverage.sh
```

By default the script runs only **`baseline`**. Uncomment the **`candidate-test`** and **`incremental`** blocks when you are ready for the full pipeline.

### Key outputs

Under `$OUTPUT_DIR`:

| Path | Contents |
|------|----------|
| `baseline/line_coverage_summary.csv` | Per-line baseline coverage (joint llc + opt): `covered`, `partially`, or `uncovered` |
| `baseline/line_coverage_uncovered.csv` | Baseline lines with no suite coverage — input to `incremental` and `target-lines` |
| `baseline/llc_address_line_map.csv` | llc address-to-line map — input to `incremental` |
| `baseline/lit_failures.json` | Failed lit tests from the baseline run (llvm-lit `--report-failures-only` JSON: `name`, `code`, `output`, `elapsed`) |
| `baseline/processed_sancov/` | Merged, symbolized symcov files — debugging artifact from baseline |
| `candidate_tests/raw_sancov/` | Per-test raw sancov shards |
| `incremental/new_coverage.csv` | **Main result** — columns `test`, `file`, `line`, `covered-points`: fuzz tests that fill suite coverage gaps |

`new_coverage.csv` is the input for testcase reduction in step 4.

---

## Workflow 2: Uncovered lines in a commit

**When to use this:** you landed a patch and want a precise list of **added** source lines that the regression suite still does not fully cover.

**Reference script:** [`scripts/test_coverage_commit_lines.sh`](scripts/test_coverage_commit_lines.sh)

### What it does

```text
added-lines  →  baseline  →  target-lines
(from git)     (baseline)      (uncovered added lines)
```

1. **`added-lines`** — parse `git show` for a commit and list every line added on the right-hand side of the diff.
2. **`baseline`** — same baseline coverage run as Workflow 1 (produces `line_coverage_uncovered.csv` and related CSVs).
3. **`target-lines`** — for each line in the target CSV, include it in the report when its `(file, line)` appears in `line_coverage_uncovered.csv` from the baseline run.

Step 3 does **not** re-run LIT, so you can repeat it with different `added-lines.csv` inputs as long as the `baseline` symcov artifacts are still present.

### Configure and run

Edit the variables at the top of `scripts/test_coverage_commit_lines.sh`:

| Variable | Meaning |
|----------|---------|
| `LLVM` | `llvm-project` checkout (same tree `added-lines` diffs against) |
| `LLVM_BIN` / `INSTRUMENTED_BIN_DIR` | Same as Workflow 1 |
| `OUTPUT_DIR` | Root for all artifacts |
| `FILTER` | llvm-lit `--filter=` regex or prefix for the baseline run |
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
| `test_suite/line_coverage_uncovered.csv` | Baseline uncovered lines — **required by `target-lines`** |
| `baseline/lit_failures.json` | Failed lit tests from the baseline run (llvm-lit `--report-failures-only` JSON: `name`, `code`, `output`, `elapsed`) |
| `baseline/processed_sancov/` | Merged symcov (still produced for debugging; not read by `target-lines`) |
| `target_lines_report/target_lines_uncovered.csv` | **Main result** — added lines where every suite point on that line is off |

---

## Reduce interesting tests

Once you have `new_coverage.csv` (Workflow 1) or a specific uncovered line you want to target (Workflow 2), use the **`reduce`** module to shrink a testcase while preserving coverage or crash behaviour.

Each row in `new_coverage.csv` maps a test file to a source location and one or more SanitizerCoverage point ids (`covered-points`). Turn a row into a reduction job by pointing a JSON config at the testcase, setting `file` / `line`, and wiring an interestingness script that checks the coverage address.

Examples:

- [`example/amd/new-test-1/`](example/amd/new-test-1/) — minimal IR reduction from a coverage row
- [`scripts/reduce_amd_coverage_based.sh`](scripts/reduce_amd_coverage_based.sh), [`scripts/batch_reduce_using_coverage.sh`](scripts/batch_reduce_using_coverage.sh) — batch reduction from a coverage CSV

```bash
python -m reduce --config example/amd/new-test-1/config.json \
  --llc "$LLVM/build-sancov/bin/llc" \
  --llvm-reduce "$LLVM/build-sancov/bin/llvm-reduce"
```

See `python -m reduce --help` and the checked-in `example/*/config.json` files for pipeline options.

---

## CLI reference

The workflows above call these modules. Use `--help` on any command for the full flag list.

| Command | Role in workflows |
|---------|-------------------|
| `python -m coverage baseline` | Baseline LIT coverage (both workflows) |
| `python -m coverage candidate-test` | Coverage from a fuzz-generated test corpus (Workflow 1) |
| `python -m coverage incremental` | Suite gaps filled by fuzz tests (Workflow 1) |
| `python -m coverage target-lines` | Uncovered target lines vs `line_coverage_uncovered.csv` (Workflow 2) |
| `python -m added_lines` | Lines added by a git commit (Workflow 2) |
| `python -m reduce` | Testcase reduction |

### `coverage baseline` filters

| Flag | Meaning |
|------|---------|
| `--lit-filter` | Regex or path prefix for llvm-lit `--filter=` (default: `(^|/)AMDGPU/`) |

Baseline symcov CSVs always include source paths under `llvm/lib` (see `DEFAULT_SOURCE_CODE_FILTER` in [`src/coverage/constants.py`](src/coverage/constants.py)). Constants: `DEFAULT_LIT_FILTER`, `DEFAULT_SOURCE_CODE_FILTER`.

### Environment variables

Several commands accept LLVM tool paths via environment variables when the matching CLI flag is omitted. A flag on the command line always wins.

| Env var | CLI flag | Commands |
|---------|----------|----------|
| `FUZZ_FILL_SANCOV` | `--sancov` | `coverage baseline`, `coverage incremental` |
| `FUZZ_FILL_LLVM_LIT` | `--llvm-lit` | `coverage baseline` |
| `FUZZ_FILL_LLC` | `--llc` | `coverage baseline`, `coverage candidate-test`, `reduce` |
| `FUZZ_FILL_OPT` | `--opt` | `coverage baseline` |
| `FUZZ_FILL_LLVM_REDUCE` | `--llvm-reduce` | `reduce` |
| `FUZZ_FILL_LLVM_DIS` | `--llvm-dis` | `reduce` (required for `.bc` input with `llvm_reduce_ir`) |
| `FUZZ_FILL_LLVM_REPO` | `--llvm-repo` | `added_lines`, `coverage target-lines` |

The [Docker test image](#docker-test-image) sets these per-tool defaults so interactive container use can omit tool flags. Integration tests use explicit CLI flags instead (see [Integration tests](#integration-tests)).

Example (paths match the Docker test image):

```bash
export FUZZ_FILL_SANCOV=/work/llvm-build-sancov/bin/sancov
export FUZZ_FILL_LLVM_LIT=/work/llvm-build-sancov/bin/llvm-lit
export FUZZ_FILL_LLC=/work/llvm-build-sancov/bin/llc
export FUZZ_FILL_OPT=/work/llvm-build-sancov/bin/opt
export FUZZ_FILL_LLVM_REPO=/work/llvm-project

python -m coverage baseline \
  --output-dir data/baseline
python -m added_lines --commit HEAD
```

By default, `coverage baseline` uses `--lit-filter '(^|/)AMDGPU/'` (all LIT tests under an `AMDGPU/` directory). For a faster CodeGen-only run:

```bash
python -m coverage baseline \
  --output-dir data/baseline-codegen \
  --lit-filter CodeGen/AMDGPU
```

Explicit full-folder baseline (same as default):

```bash
python -m coverage baseline \
  --output-dir data/baseline-amdgpu-dirs \
  --lit-filter '(^|/)AMDGPU/' \
  -j "$(nproc)"
```

Or via [`scripts/test_coverage.sh`](scripts/test_coverage.sh) (defaults match the above):

```bash
./scripts/test_coverage.sh
```

CodeGen-only via script:

```bash
FILTER=CodeGen/AMDGPU ./scripts/test_coverage.sh

Workflow shell scripts under `scripts/` may use their own names (`LLVM_BIN`, `INSTRUMENTED_BIN_DIR`, …); only the `FUZZ_FILL_*` variables are read by the Python CLIs.

---

## Docker test image

The Docker image bundles an official LLVM release bootstrap, a dual-build SanitizerCoverage LLVM tree (instrumented `llc`/`opt` plus Release helpers), and a fuzz-fill venv. Use it when you want to run integration tests or experiment without building LLVM locally.

**Scripts** (under [`scripts/docker/`](scripts/docker/)): [`build-image.sh`](scripts/docker/build-image.sh), [`build-image-pr.sh`](scripts/docker/build-image-pr.sh), [`pr-cov-gaps-detection.sh`](scripts/docker/pr-cov-gaps-detection.sh), [`test-image.sh`](scripts/docker/test-image.sh), [`tmp-container.sh`](scripts/docker/tmp-container.sh)

### Build

From the repo root (first build compiles LLVM and can take a while):

```bash
./scripts/docker/build-image.sh
```

By default the image is tagged `fuzz-fill-test:latest`. LLVM source is downloaded at tag `llvmorg-22.1.8` and bootstrapped from the matching GitHub release.

| Option | Meaning |
|--------|---------|
| `--llvm-dir <path>` | Use a local `llvm-project` checkout instead of downloading tagged source |
| `--llvm-release-version <ver>` | Official LLVM release for bootstrap toolchain (default: `22.1.8`) |
| `--tag <tag>` | Docker image tag (default: `latest`) |
| `--allowlist amdgpu\|spirv` | SanitizerCoverage allowlist baked into the instrumented build (default: `amdgpu`) |
| `-j <n>`, `--jobs <n>` | Limit ninja parallelism for the sancov build (default: unconstrained) |

Examples:

```bash
./scripts/docker/build-image.sh --llvm-dir llvm-project --tag local-llvm
./scripts/docker/build-image.sh --allowlist spirv --tag spirv
./scripts/docker/build-image.sh -j "$(nproc)"
```

### Build from an LLVM pull request

[`scripts/docker/build-image-pr.sh`](scripts/docker/build-image-pr.sh) builds a Docker image from an LLVM PR. Pass a local `llvm-project` clone; the PR is squashed in a standalone fuzz-fill clone so your llvm checkout is unchanged. Requires local `gh` and Docker (BuildKit). PRs are assumed to live on **`llvm/llvm-project`** unless you pass `--github-repo`.

```bash
./scripts/docker/build-image-pr.sh --llvm-repo /path/llvm-project --pr-id 185430 --allowlist amdgpu
```

| Option | Meaning |
|--------|---------|
| `--llvm-repo <path>` | Local `llvm-project` clone |
| `--pr-id <n>` | GitHub pull request number |
| `--allowlist amdgpu\|spirv` | SanitizerCoverage allowlist |
| `--github-repo <owner/repo>` | GitHub repo hosting the PR (default: `llvm/llvm-project`) |
| `-j <n>`, `--jobs <n>` | Limit ninja parallelism for both LLVM builds (default: unconstrained) |

For the full coverage-gap workflow (build + detect), use [`scripts/docker/pr-cov-gaps-detection.sh --build-image`](#pr-coverage-gap-detection) instead.

### Workflow 2: PR coverage gap detection

[`scripts/docker/pr-cov-gaps-detection.sh`](scripts/docker/pr-cov-gaps-detection.sh) runs Workflow 2 in Docker (baseline → `added_lines` → `target-lines`). Use `--build-image` to build the PR image and run detection in one step. The lit filter defaults from the image's `/work/.sancov-allowlist`; override with `--lit-filter` (regex or prefix).

```bash
./scripts/docker/pr-cov-gaps-detection.sh \
  --build-image \
  --llvm-repo /path/llvm-project \
  --pr-id 203468 \
  --backend-tests amdgpu \
  --output-dir /path/pr-cov-gaps-203468 \
  -j "$(nproc)"
```

| Option | Meaning |
|--------|---------|
| `--build-image` | Build PR image first via `scripts/docker/build-image-pr.sh` |
| `--llvm-repo <path>` | Required with `--build-image` |
| `--backend-tests amdgpu\|spirv` | Required with `--build-image` |
| `--pr-id <n>` | PR number (image tag `llvm-pr-<n>`) |
| `--output-dir <path>` | Host output directory |
| `-j <n>`, `--jobs <n>` | Parallel jobs (ninja when building, llvm-lit when detecting) |
| `--lit-filter <regex>` | llvm-lit `--filter=` regex or prefix (default from allowlist) |
| `--github-repo <owner/repo>` | Optional; default `llvm/llvm-project` when building |

If the image `fuzz-fill-test:llvm-pr-<n>` already exists, omit `--build-image` to run detection only.

Main output: `<output-dir>/commit_lines_report/target_lines_uncovered.csv`. See [Workflow 2](#workflow-2-uncovered-lines-in-a-commit) for report semantics.

### Run integration tests

```bash
./scripts/docker/test-image.sh
```

This runs the full suite under `integration-tests/` using the image baked into the container. Pass the same `--tag` you used when building:

```bash
./scripts/docker/build-image.sh --tag local-llvm
./scripts/docker/test-image.sh --tag local-llvm
```

After building a [PR image](#build-from-an-llvm-pull-request), pass the same tag (default `llvm-pr-<pr-id>`):

```bash
./scripts/docker/build-image-pr.sh --llvm-repo ../llvm-project --pr-id 185430 --allowlist amdgpu
./scripts/docker/test-image.sh --tag llvm-pr-185430
```

Use `--bind-repo` to mount your local fuzz-fill checkout over `/work/fuzz-fill` while keeping the image venv at `/work/fuzz-fill-venv`:

```bash
./scripts/docker/test-image.sh --bind-repo
```

Any extra arguments are forwarded to lit. For example:

```bash
./scripts/docker/test-image.sh --tag local-llvm integration-tests/smoke.test
```

### Run a container

For an interactive shell or arbitrary commands:

```bash
./scripts/docker/tmp-container.sh                              # interactive shell
./scripts/docker/tmp-container.sh --bind-repo                  # shell with host repo mounted
./scripts/docker/tmp-container.sh --bind-repo <command> [args] # one-shot command
```

Without `--bind-repo`, the container uses the fuzz-fill copy baked into the image.

With `--bind-repo`, your local checkout is mounted at `/work/fuzz-fill`; the venv stays at `/work/fuzz-fill-venv`.

To run integration tests manually inside the container:

```bash
./scripts/docker/tmp-container.sh ./integration-tests/test.sh \
  --venv /work/fuzz-fill-venv \
  --llvm-build /work/llvm-build-sancov/bin \
  --llvm-sancov-build /work/llvm-build-sancov/bin \
  --llvm-src /work/llvm-project \
  -v integration-tests/
```

---

## Tests

### Unit tests

Python unit tests live under `tests/`. They use the stdlib `unittest` runner and do not need LLVM builds.

```bash
source venv/bin/activate
python -m unittest discover -s tests -v
```

To run a single module:

```bash
python -m unittest tests.test_analyser -v
```

### Integration tests

Integration tests need the SanitizerCoverage LLVM `bin` directory and llvm-project source. Locally:

```bash
./integration-tests/test.sh \
  --venv ./venv/ \
  --llvm-build llvm-project/build-sancov/bin/ \
  --llvm-sancov-build llvm-project/build-sancov/bin/ \
  --llvm-src llvm-project/ \
  integration-tests/
```

Or use [`scripts/docker/test-image.sh`](scripts/docker/test-image.sh) with the [Docker test image](#docker-test-image). That script runs unit tests first, then integration tests:

```bash
./scripts/docker/test-image.sh                    # default tag: latest
./scripts/docker/test-image.sh --tag llvm-pr-42   # after scripts/docker/build-image-pr.sh
./scripts/docker/test-image.sh --bind-repo        # mount local checkout
```

Both `--llvm-build` and `--llvm-sancov-build` point at the same SanitizerCoverage tree; `--llvm-src` is the llvm-project checkout root (used as `%llvm-repo` in tests).

---

## Contributions

### AMDGPU

| Date | Commit | Summary |
|------|--------|---------|
| 2026-03-10 | [30f13b12a0be](https://github.com/llvm/llvm-project/commit/30f13b12a0bee2ec109f37876d3d17106acfb41f) | New `vgpr-mark-last-scratch-load.ll` coverage for `AMDGPUMarkLastScratchLoad` ([#185430](https://github.com/llvm/llvm-project/pull/185430)) |
| 2026-03-19 | [c63ce62f7cf6](https://github.com/llvm/llvm-project/commit/c63ce62f7cf6193714e95f6b3442170ccb2a3a5e) | New cases in `si-lower-i1-copies.mir` for `SILowerI1Copies` ([#186127](https://github.com/llvm/llvm-project/pull/186127)) |
| 2026-03-31 | [67d4842910b8](https://github.com/llvm/llvm-project/commit/67d4842910b8cb79f31b9041bdf56c206cd768e9) | New cases in `si-lower-sgpr-spills.mir` for `SILowerSGPRSpills` ([#189426](https://github.com/llvm/llvm-project/pull/189426)) |
| 2026-06-12 | [4a3946fc690c](https://github.com/llvm/llvm-project/commit/4a3946fc690c461417d38b6264a1f7a70f5dd364) | Expanded `float-sopc-vopc.ll` coverage for `SIInstrInfo` ([#200414](https://github.com/llvm/llvm-project/pull/200414)) |

### SPIR-V

| Date | Commit | Summary |
|------|--------|---------|
| 2026-03-11 | [e45c8b6555c8](https://github.com/llvm/llvm-project/commit/e45c8b6555c866cd0412b42fce0439e927ca3ba2) | New `icmp.ll` cases for the SPIR-V backend ([#185686](https://github.com/llvm/llvm-project/pull/185686)) |
| 2026-03-17 | [b2442a20a946](https://github.com/llvm/llvm-project/commit/b2442a20a9462ef4a4244c2992abf6a102e90472) | New `icmp.ll` cases for `SPIRVInstructionSelector` ([#186069](https://github.com/llvm/llvm-project/pull/186069)) |
| 2026-03-25 | [741eb8015253](https://github.com/llvm/llvm-project/commit/741eb8015253866323a3c38eb4e7ae686323002d) | New `SPIRVEmitIntrinsics.ll` for the `SPIRVEmitIntrinsics` pass ([#188285](https://github.com/llvm/llvm-project/pull/188285)) |
| 2026-03-27 | [294dc1b89452](https://github.com/llvm/llvm-project/commit/294dc1b894520506cdd8d260f51c3f8fec6a7118) | New `SPIRVEmitIntrinsics-get-element-ptr.ll` ([#188962](https://github.com/llvm/llvm-project/pull/188962)) |
| 2026-03-27 | [9238b0f765ad](https://github.com/llvm/llvm-project/commit/9238b0f765ada177cd7034cf75a57acf26f2ac46) | New `SPIRVEmitIntrinsics-infer-ptr-type.ll` ([#188950](https://github.com/llvm/llvm-project/pull/188950)) |
| 2026-03-31 | [a839e500e8a1](https://github.com/llvm/llvm-project/commit/a839e500e8a1934d3ad0a346d3789904c2a865a9) | New `SPIRVEmitIntrinsics-infer-fnptr-todo-type.ll` ([#189413](https://github.com/llvm/llvm-project/pull/189413)) |
