# fuzz-fill

Fuzzing to fill LLVM coverage gaps with fuzz-generated tests.

fuzz-fill identifies coverage gaps in LLVM:

1. **Gap finding** — measure baseline coverage achieved by LLVM's LIT test suite and produce a list of uncovered lines. At present `fuzz-fill` supports finding gaps in the AMDGPU and SPIR-V backends; this will be extended in the future to other backends and parts of the LLVM codebase.
   - **Baseline** — all uncovered lines in a user-specified part of the LLVM codebase.
   - **PR** — added or changed lines in a commit that baseline coverage still misses.

Gap filling (running a fuzz corpus against the gap list) will follow in a separate PR.

```
┌─ Gap finding ────────────────────────────────────────────────┐
│                                                              │
│   Baseline ──┐                                               │
│              ├──► Uncovered lines (CSV)                      │
│   PR ────────┘                                               │
└──────────────────────────────────────────────────────────────┘
```

See [Contributions](#contributions) for tests contributed to LLVM.

## Quick start (Docker)

Try [PR gap finding](#gap-finding-pr), which reports lines changed in a PR or commit that are not covered by any LIT tests. Results are saved in `<output-dir>/commit_lines_report/target_lines_uncovered.csv`. See [Gap finding (PR)](#gap-finding-pr) and [Docker test image](#docker-test-image) for more options.

Prerequisites:
- [Docker](https://docs.docker.com/)
- A local `llvm-project` checkout

```bash
git clone https://github.com/ROCm/fuzz-fill.git
cd fuzz-fill
```

**LLVM pull request** — requires [GitHub CLI](https://cli.github.com/) (`gh`). Builds a PR image, squashes all commits onto the PR's base commit, and finds all coverage gaps in that PR:

```bash
./scripts/docker/gap-finding-pr.sh \
  --build-image \
  --llvm-repo /path/to/llvm-project \
  --pr-id 203468 \
  --backend-tests amdgpu \
  --output-dir ./data/gap-finding-pr-203468 \
  -j "$(nproc)"
```

Use `spirv` instead of `amdgpu` for SPIR-V backend tests.

**Local commit** — build from your `llvm-project` checkout (the local checkout remains unchanged). This command only finds gaps in lines changed in a single commit rather than a full PR. Replace `HEAD` with a hash, branch, or `main~3` as needed:

```bash
./scripts/docker/build-image.sh --llvm-dir /path/to/llvm-project --allowlist amdgpu -j "$(nproc)"

./scripts/docker/gap-finding-pr.sh \
  --image fuzz-fill-test:latest \
  --output-dir ./data/my-commit \
  --commit HEAD \
  -j "$(nproc)"
```

## Table of Contents

- [Quick start (Docker)](#quick-start-docker)
- [Setup](#setup)
  - [Python environment](#python-environment)
  - [LLVM builds](#llvm-builds)
- [Gap finding (baseline)](#gap-finding-baseline)
- [Gap finding (PR)](#gap-finding-pr)
- [CLI reference](#cli-reference)
  - [Uncovered-lines CSV contract](#uncovered-lines-csv-contract)
  - [Environment variables](#environment-variables)
- [Docker test image](#docker-test-image)
  - [Build](#build)
  - [Build from an LLVM pull request](#build-from-an-llvm-pull-request)
  - [PR image build and reuse](#pr-image-build-and-reuse)
  - [Gap finding (baseline) in Docker](#gap-finding-baseline-in-docker)
  - [Gap finding (PR) in Docker](#gap-finding-pr-in-docker)
  - [Run integration tests](#run-integration-tests)
  - [Run a container](#run-a-container)
- [Tests](#tests)
- [Contributions](#contributions)
  - [Gaps filled in existing LLVM code](#gaps-filled-in-existing-llvm-code)
  - [Gaps detected on PRs](#gaps-detected-on-prs)

## Setup

### Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### LLVM builds

You need an official **LLVM GitHub release** as bootstrap and one **SanitizerCoverage** build of llvm-project at the matching tag:

| Component | Purpose | How |
|-----------|---------|-----|
| **Release bootstrap** | `clang`, `clang++` for compiling LLVM | Download [LLVM release](https://github.com/llvm/llvm-project/releases) (e.g. `LLVM-22.1.8-Linux-X64.tar.xz`) |
| **SanitizerCoverage** | Unified build tree: instrumented `llc`/`opt`, Release LIT helpers, `llvm-lit`, `sancov` | `./scripts/build-llvm-sancov.sh ./scripts/allowlist-amdgpu.txt llvm-project llvm-project/build-sancov --bootstrap-bin /path/to/LLVM-22.1.8/bin --ignorelist ./scripts/ignorelist-amdgpu.txt` |

`build-llvm-sancov.sh` runs two partial builds from the same source: **`llvm-tblgen` is built from the source tree first**, then a **Release** tree for target-agnostic LIT helpers plus **`sancov`**, and a **Debug** SanitizerCoverage tree for **`llc`**, **`opt`**, and target-linked helpers (`llvm-mc`, `llvm-objdump`, …). Release tools are copied into the instrumented tree's `bin/`; `llvm-lit` is generated there by cmake. The bootstrap release supplies **clang/clang++ only** (TableGen must match the source).

For AMDGPU builds, pass [`scripts/ignorelist-amdgpu.txt`](scripts/ignorelist-amdgpu.txt) with `--ignorelist`. It excludes MC-layer code (AsmParser, Disassembler, MCTargetDesc, MCA, TargetInfo), selected Utils used mainly by MC/PAL/asm, and `AMDGPUSplitModule.cpp` from instrumentation — keeping opt/llc codegen paths covered. SPIRV builds do not use an ignorelist.

**`python -m coverage baseline`** patches **`<instrumented-build>/test/lit.site.cfg.py`** so LIT forwards **`UBSAN_OPTIONS`** to every test subprocess. The patch is idempotent and is re-applied if CMake regenerates that file.

The example scripts below assume paths like:

- `$LLVM/build-sancov/bin` — unified build (`llvm-lit`, instrumented `llc`/`opt` + target helpers, Release `sancov`/other LIT helpers)

Adjust these to match your trees before running.

---

## Gap finding (baseline)

**When to use this:** you want a list of source lines that baseline LIT coverage does not fully hit in a target area (e.g. AMDGPU `CodeGen`).

**Reference script:** [`scripts/gap-finding-baseline.sh`](scripts/gap-finding-baseline.sh)

### What it does

```text
baseline  →  line_coverage_uncovered.csv
(LIT run)     (+ llc_address_line_map.csv)
```

**`coverage baseline`** — identify uncovered lines by running a filtered slice of LLVM instrumented with SanitizerCoverage.

### Configure and run

Required flags mirror the [Docker gap-finding runners](#gap-finding-baseline-in-docker): `--output-dir`, LIT filters via `--lit-filter` or `--backend-tests`, plus explicit LLVM paths for local builds.

| Flag | Meaning |
|------|---------|
| `--output-dir` | Root for artifacts |
| `--llvm-repo` | Path to your `llvm-project` checkout |
| `--llvm-bin` | Uninstrumented `bin` directory (`sancov`) |
| `--instrumented-bin-dir` | SanitizerCoverage `bin` directory (`llvm-lit`, `llc`, `opt`) |
| `--lit-filter` | LIT directory prefix; repeat for multiple |
| `--backend-tests` | `amdgpu` or `spirv` — default LIT filter(s) when `--lit-filter` is omitted |
| `-j`, `--jobs` | Parallel jobs for llvm-lit |

```bash
./scripts/gap-finding-baseline.sh \
  --output-dir ./data/baseline-run \
  --llvm-repo /path/llvm-project \
  --llvm-bin /path/llvm-project/build/bin \
  --instrumented-bin-dir /path/llvm-project/build-sancov/bin \
  --backend-tests amdgpu \
  -j "$(nproc)"
```

### Key outputs

Under `$OUTPUT_DIR/baseline/`:

| Path | Contents |
|------|----------|
| `line_coverage_summary.csv` | Per-line baseline coverage: `covered`, `partially`, or `uncovered` |
| `line_coverage_uncovered.csv` | **Main gap list** — input to `target-lines` and downstream gap filling |
| `llc_address_line_map.csv` | LLC address-to-line map (same baseline run as the gap list) |
| `lit_failures.json` | Failed LIT tests (`name`, `code`, `output`, `elapsed`) |
| `processed_sancov/` | Merged symcov (debugging) |

---

## Gap finding (PR)

**When to use this:** you landed a patch and want **added** source lines that baseline coverage still does not fully cover.

**Reference script:** [`scripts/gap-finding-pr.sh`](scripts/gap-finding-pr.sh)

### What it does

```text
added-lines  →  baseline  →  target-lines
(from git)     (LIT run)     (uncovered added lines)
```

1. **`added-lines`** — parse `git show` for a commit and list every line added on the right-hand side of the diff.
2. **`baseline`** — same baseline run as [gap finding (baseline)](#gap-finding-baseline).
3. **`target-lines`** — include each added line whose `(file, line)` appears in `line_coverage_uncovered.csv`.

Step 3 does **not** re-run LIT; you can repeat it with different `added-lines.csv` inputs while baseline artifacts remain valid.

### Configure and run

| Flag | Meaning |
|------|---------|
| `--output-dir` | Root for all artifacts |
| `--commit` | Revision to analyse (`HEAD`, a hash, `main~3`, …) |
| `--pr-id` | GitHub PR number — squashes PR into `.fuzz-fill-llvm-pr-worktrees/pr-<n>/` (exclusive with `--commit`) |
| `--github-repo` | With `--pr-id` (default: `llvm/llvm-project`) |
| `--llvm-repo` | `llvm-project` checkout (`added-lines` tree; with `--pr-id`, used as clone reference) |
| `--llvm-bin` / `--instrumented-bin-dir` | Same as [baseline gap finding](#gap-finding-baseline) |
| `--lit-filter` / `--backend-tests` | LIT filters for the baseline step |
| `-j`, `--jobs` | Parallel jobs for llvm-lit |

PR gap finding squashes all PR commits onto the merge-base in a self-contained worktree (same as the Docker PR image build). Use [`scripts/prepare-pr-llvm.sh`](scripts/prepare-pr-llvm.sh) directly if you only need the squashed tree:

```bash
./scripts/prepare-pr-llvm.sh \
  --pr-id 214457 \
  --dest ./.fuzz-fill-llvm-pr-worktrees/pr-214457/llvm-project \
  --reference /path/llvm-project \
  --squash-commit-file ./.fuzz-fill-llvm-pr-worktrees/pr-214457/squash-commit
```

```bash
./scripts/gap-finding-pr.sh \
  --output-dir ./data/gap-finding-pr \
  --llvm-repo /path/llvm-project \
  --llvm-bin /path/llvm-project/build/bin \
  --instrumented-bin-dir /path/llvm-project/build-sancov/bin \
  --commit HEAD \
  --backend-tests amdgpu \
  -j "$(nproc)"
```

GitHub pull request (squash + gap finding):

```bash
./scripts/gap-finding-pr.sh \
  --output-dir ./data/gap-finding-pr-214457 \
  --llvm-repo /path/llvm-project \
  --llvm-bin ./.fuzz-fill-llvm-pr-worktrees/pr-214457/llvm-project/build-sancov/bin \
  --instrumented-bin-dir ./.fuzz-fill-llvm-pr-worktrees/pr-214457/llvm-project/build-sancov/bin \
  --pr-id 214457 \
  --backend-tests amdgpu \
  -j "$(nproc)"
```

### Key outputs

Under `$OUTPUT_DIR`:

| Path | Contents |
|------|----------|
| `added-lines/added-lines.csv` | Added lines from the commit (`path`, `line_no`, `text`) |
| `baseline/line_coverage_uncovered.csv` | Baseline uncovered lines |
| `baseline/llc_address_line_map.csv` | LLC map from the baseline run |
| `baseline/lit_failures.json` | Failed LIT tests from baseline |
| `commit_lines_report/target_lines_uncovered.csv` | **Main result** — PR-added lines still uncovered (`file`, `line`, optional `text`; absolute paths) |

---

## CLI reference

The scripts above call these modules. Use `--help` on any command for the full flag list.

| Command | Role |
|---------|------|
| `python -m coverage baseline` | Baseline LIT coverage (gap finding) |
| `python -m coverage candidate-test` | Coverage from a fuzz-generated test corpus (gap filling) |
| `python -m coverage incremental` | Suite gaps filled by fuzz tests (gap filling) |
| `python -m coverage target-lines` | PR added lines vs `line_coverage_uncovered.csv` |
| `python -m added_lines` | Lines added by a git commit |
| `python -m reduce` | Testcase reduction |

### Uncovered-lines CSV contract

PR gap finding output and baseline gap lists both use an uncovered-lines CSV with columns **`file`** and **`line`**. Paths are **absolute** and must match those in `llc_address_line_map.csv` (as produced by `coverage baseline`).

| File | Role |
|------|------|
| `line_coverage_uncovered.csv` | Baseline gap list |
| `target_lines_uncovered.csv` | PR-added lines still uncovered; same `file`/`line` schema, optional `text` |

PR gap finding input to `target-lines` remains `added-lines.csv` (`path`, `line_no`, `text` with git-relative paths). The **output** report uses the shared contract above.

### `coverage baseline` filters

| Flag | Meaning |
|------|---------|
| `--lit-filter DIR` | LIT directory prefix; **repeat** for multiple prefixes (OR'd into one llvm-lit `--filter=` regex) |

Default when omitted: `AMDGPU` (see `DEFAULT_LIT_FILTER_DIRS` in [`src/coverage/constants.py`](src/coverage/constants.py)).

Baseline symcov CSVs include **all** instrumented source paths from the LIT run. Use `--source-filter` on `coverage incremental` to scope gap finding (default: `(?:^|/)llvm/lib/`; see `DEFAULT_SOURCE_CODE_FILTER` in [`src/coverage/constants.py`](src/coverage/constants.py)).

### `coverage incremental` filters

| Flag | Meaning |
|------|---------|
| `--source-filter REGEX` | Only consider baseline gaps whose source file path matches this Python regex (default: `(?:^|/)llvm/lib/`; pass `""` to disable) |

### Candidate-test settings

Each row in `--settings-csv` is one `llc` invocation (flags passed before the input path). The CSV must have a single column header `llc_flags`:

```csv
llc_flags
-O0 -global-isel=0
-O0 -global-isel=1
```

When `--settings-csv` is omitted, fuzz-fill uses the built-in default: all combinations of `-O0`, `-O1`, `-O2`, `-O3` with `-global-isel=0` and `-global-isel=1` (**8 runs per input file**). Total jobs = `(number of .ll/.bc files) × (rows in settings)`.

### Environment variables

Several commands accept LLVM tool paths via environment variables when the matching CLI flag is omitted. A flag on the command line always wins.

| Env var | CLI flag | Commands |
|---------|----------|----------|
| `FUZZ_FILL_SANCOV` | `--sancov` | `coverage baseline`, `coverage incremental`, `coverage min-candidate-tests` (mainly for maintainers) |
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

python -m coverage baseline --output-dir data/baseline
python -m added_lines --commit HEAD
```

CodeGen-only baseline:

```bash
python -m coverage baseline \
  --output-dir data/baseline-codegen \
  --lit-filter CodeGen/AMDGPU
```

Or via the reference script:

```bash
./scripts/gap-finding-baseline.sh \
  --output-dir ./data/baseline-codegen \
  --llvm-repo /path/llvm-project \
  --llvm-bin /path/llvm-project/build/bin \
  --instrumented-bin-dir /path/llvm-project/build-sancov/bin \
  --lit-filter CodeGen/AMDGPU
```

Workflow shell scripts under `scripts/` may use their own names (`LLVM_BIN`, `INSTRUMENTED_BIN_DIR`, …); only the `FUZZ_FILL_*` variables are read by the Python CLIs.

### Utility commands

Optional commands outside the main workflows in fuzz-fill.

| Command | Purpose |
|---------|---------|
| `python -m coverage min-candidate-tests` | From `candidate-test` output, selects a minimal set of tests that cover the same SanitizerCoverage instrumentation points; writes `min_candidate_tests.csv`, `min_candidate_tests_points.csv`, and `min_candidate_tests_source_files.csv`. Requires `candidate_test_manifest.csv` and `candidate_test_settings.csv` emitted by `candidate-test`. |

---

## Docker test image

The Docker image bundles an official LLVM release bootstrap, a dual-build SanitizerCoverage LLVM tree (instrumented `llc`/`opt` plus Release helpers), and a fuzz-fill venv. Use it when you want to run integration tests or experiment without building LLVM locally.

**Scripts** (under [`scripts/docker/`](scripts/docker/)): [`build-image.sh`](scripts/docker/build-image.sh), [`build-image-pr.sh`](scripts/docker/build-image-pr.sh), [`ensure-image.sh`](scripts/docker/ensure-image.sh), [`gap-finding-baseline.sh`](scripts/docker/gap-finding-baseline.sh), [`gap-finding-pr.sh`](scripts/docker/gap-finding-pr.sh), [`test-image.sh`](scripts/docker/test-image.sh), [`tmp-container.sh`](scripts/docker/tmp-container.sh)

The image bakes a copy of fuzz-fill at `/work/fuzz-fill` when built. Pass **`--bind-repo`** on a docker runner to mount your local checkout over that path (venv stays at `/work/fuzz-fill-venv`) when you need code that is newer than the image.

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
| `--allowlist amdgpu\|spirv` | SanitizerCoverage allowlist baked into the instrumented build (default: `amdgpu`; AMDGPU also applies [`scripts/ignorelist-amdgpu.txt`](scripts/ignorelist-amdgpu.txt)) |
| `--sancov-instrumentation-mode func\|bb\|edge` | SanitizerCoverage instrumentation mode (default: `bb`; produces `-fsanitize-coverage=<mode>,trace-pc-guard`) |
| `-j <n>`, `--jobs <n>` | Limit ninja parallelism for the sancov build (default: unconstrained) |

Examples:

```bash
./scripts/docker/build-image.sh --llvm-dir llvm-project --tag local-llvm
./scripts/docker/build-image.sh --allowlist spirv --tag spirv
./scripts/docker/build-image.sh --sancov-instrumentation-mode edge --tag edge
./scripts/docker/build-image.sh -j "$(nproc)"
```

Use this image with **`--image fuzz-fill-test:latest`** for local-commit gap finding (see [Quick start](#quick-start-docker)).

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
| `--sancov-instrumentation-mode func\|bb\|edge` | SanitizerCoverage instrumentation mode (default: `bb`) |
| `--github-repo <owner/repo>` | GitHub repo hosting the PR (default: `llvm/llvm-project`) |
| `-j <n>`, `--jobs <n>` | Limit ninja parallelism for both LLVM builds (default: unconstrained) |

For build + gap finding in one step, use [`gap-finding-pr.sh --build-image`](#gap-finding-pr-in-docker) instead.

### PR image build and reuse

Gap-finding Docker runners share [`ensure-image.sh`](scripts/docker/ensure-image.sh) for PR images tagged `fuzz-fill-test:llvm-pr-<n>`:

| Flag | Meaning |
|------|---------|
| `--build-image` | Build via `build-image-pr.sh` when the tag is missing |
| `--force-build` | Rebuild even when the tag already exists |
| `--keep-image` | Do not remove the image after a `--build-image` run (default: remove) |
| `--pr-id <n>` | Select `fuzz-fill-test:llvm-pr-<n>` |
| `--llvm-repo <path>` | Required with `--build-image` |
| `--backend-tests amdgpu\|spirv` | Required with `--build-image` |

Build once, then reuse on later runs (omit `--build-image`):

```bash
./scripts/docker/gap-finding-pr.sh \
  --build-image --keep-image \
  --llvm-repo /path/llvm-project --pr-id 203468 \
  --backend-tests amdgpu --output-dir ./data/gap-finding-pr-203468 -j "$(nproc)"

./scripts/docker/gap-finding-pr.sh \
  --pr-id 203468 --output-dir ./data/gap-finding-pr-203468
```

### Gap finding (baseline) in Docker

[`scripts/docker/gap-finding-baseline.sh`](scripts/docker/gap-finding-baseline.sh) runs `coverage baseline` in a container. Output: `<output-dir>/baseline/`.

```bash
./scripts/docker/gap-finding-baseline.sh \
  --output-dir ./data/baseline-run \
  -j "$(nproc)"
```

| Option | Meaning |
|--------|---------|
| `--output-dir <path>` | Host output directory (required) |
| `--image <ref>` | Docker image (default: `fuzz-fill-test:latest`) |
| `--pr-id <n>` | PR image `fuzz-fill-test:llvm-pr-<n>` |
| `--build-image` | Build PR image when missing (see [PR image build and reuse](#pr-image-build-and-reuse)) |
| `--bind-repo` | Mount local fuzz-fill checkout over `/work/fuzz-fill` |
| `--lit-filter <prefix>` | LIT filter override (default: from image `/work/.sancov-allowlist`) |
| `-j <n>`, `--jobs <n>` | Parallel jobs for llvm-lit and ninja (when building) |

### Gap finding (PR) in Docker

[`scripts/docker/gap-finding-pr.sh`](scripts/docker/gap-finding-pr.sh) runs baseline → `added_lines` → `target-lines`. Requires **`--image` or `--pr-id`**.

**GitHub PR** (build + run):

```bash
./scripts/docker/gap-finding-pr.sh \
  --build-image \
  --llvm-repo /path/llvm-project \
  --pr-id 203468 \
  --backend-tests amdgpu \
  --output-dir ./data/gap-finding-pr-203468 \
  -j "$(nproc)"
```

**Local commit** (after [`build-image.sh`](#build)):

```bash
./scripts/docker/gap-finding-pr.sh \
  --image fuzz-fill-test:latest \
  --output-dir ./data/my-commit \
  --commit HEAD \
  -j "$(nproc)"
```

For AMDGPU images, baseline defaults to the twelve LIT prefixes in [`scripts/lit-filters-amdgpu.sh`](scripts/lit-filters-amdgpu.sh); SPIRV defaults to `CodeGen/SPIRV`. Override with one or more `--lit-filter` prefixes.

| Option | Meaning |
|--------|---------|
| `--image <ref>` | Docker image (required unless `--pr-id`) |
| `--pr-id <n>` | PR image tag `llvm-pr-<n>` (required unless `--image`) |
| `--commit <rev>` | Revision for `added_lines` (default: `HEAD` in container llvm-project) |
| `--build-image` | Build PR image when missing |
| `--force-build` / `--keep-image` | Rebuild or retain PR image |
| `--llvm-repo <path>` | Required with `--build-image` |
| `--backend-tests amdgpu\|spirv` | Required with `--build-image` |
| `--output-dir <path>` | Host output directory |
| `-j <n>`, `--jobs <n>` | Parallel jobs |
| `--lit-filter <dir>` | LIT prefix; repeat for multiple |
| `--github-repo <owner/repo>` | When building (default: `llvm/llvm-project`) |

Main output: `<output-dir>/commit_lines_report/target_lines_uncovered.csv`.

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

#### E2E integration tests

Tests under `integration-tests/e2e/` are marked `# REQUIRES: e2e` and are **not** run by default. Pass `--param e2e=1` to lit explicitly:

```bash
export FUZZ_FILL_E2E_BOOTSTRAP_BIN=/path/to/LLVM-22.1.8/bin
export GH_TOKEN="$(gh auth token)"   # or ${{ github.token }} in CI

./integration-tests/test.sh \
  --venv ./venv/ \
  --llvm-build llvm-project/build-sancov/bin/ \
  --llvm-sancov-build llvm-project/build-sancov/bin/ \
  --llvm-src llvm-project/ \
  --param e2e=1 \
  -v integration-tests/e2e/gap-finding-pr/
```

E2E tests use [`scripts/prepare-pr-llvm.sh`](scripts/prepare-pr-llvm.sh) with `--plain-clone` (same squash + self-contained export as the Docker PR path), then build SanitizerCoverage and run gap finding. The first run can take several hours (LLVM build + amdgpu LIT slice).

---

## Contributions

fuzz-fill targets two kinds of coverage gap: lines **already in LLVM** that tests miss, and lines **introduced or changed in a PR** that tests still miss after the PR's own tests run.

### Gaps filled in existing LLVM code

Baseline coverage gaps — lines already present in LLVM that the LIT suite did not exercise. Identified with baseline gap finding and closed with new or expanded LIT tests.

#### AMDGPU

| Date | Commit | Summary |
|------|--------|---------|
| 2026-03-10 | [30f13b12a0be](https://github.com/llvm/llvm-project/commit/30f13b12a0bee2ec109f37876d3d17106acfb41f) | New `vgpr-mark-last-scratch-load.ll` coverage for `AMDGPUMarkLastScratchLoad` ([#185430](https://github.com/llvm/llvm-project/pull/185430)) |
| 2026-03-19 | [c63ce62f7cf6](https://github.com/llvm/llvm-project/commit/c63ce62f7cf6193714e95f6b3442170ccb2a3a5e) | New cases in `si-lower-i1-copies.mir` for `SILowerI1Copies` ([#186127](https://github.com/llvm/llvm-project/pull/186127)) |
| 2026-03-31 | [67d4842910b8](https://github.com/llvm/llvm-project/commit/67d4842910b8cb79f31b9041bdf56c206cd768e9) | New cases in `si-lower-sgpr-spills.mir` for `SILowerSGPRSpills` ([#189426](https://github.com/llvm/llvm-project/pull/189426)) |
| 2026-06-12 | [4a3946fc690c](https://github.com/llvm/llvm-project/commit/4a3946fc690c461417d38b6264a1f7a70f5dd364) | Expanded `float-sopc-vopc.ll` coverage for `SIInstrInfo` ([#200414](https://github.com/llvm/llvm-project/pull/200414)) |

#### SPIR-V

| Date | Commit | Summary |
|------|--------|---------|
| 2026-03-11 | [e45c8b6555c8](https://github.com/llvm/llvm-project/commit/e45c8b6555c866cd0412b42fce0439e927ca3ba2) | New `icmp.ll` cases for the SPIR-V backend ([#185686](https://github.com/llvm/llvm-project/pull/185686)) |
| 2026-03-17 | [b2442a20a946](https://github.com/llvm/llvm-project/commit/b2442a20a9462ef4a4244c2992abf6a102e90472) | New `icmp.ll` cases for `SPIRVInstructionSelector` ([#186069](https://github.com/llvm/llvm-project/pull/186069)) |
| 2026-03-25 | [741eb8015253](https://github.com/llvm/llvm-project/commit/741eb8015253866323a3c38eb4e7ae686323002d) | New `SPIRVEmitIntrinsics.ll` for the `SPIRVEmitIntrinsics` pass ([#188285](https://github.com/llvm/llvm-project/pull/188285)) |
| 2026-03-27 | [294dc1b89452](https://github.com/llvm/llvm-project/commit/294dc1b894520506cdd8d260f51c3f8fec6a7118) | New `SPIRVEmitIntrinsics-get-element-ptr.ll` ([#188962](https://github.com/llvm/llvm-project/pull/188962)) |
| 2026-03-27 | [9238b0f765ad](https://github.com/llvm/llvm-project/commit/9238b0f765ada177cd7034cf75a57acf26f2ac46) | New `SPIRVEmitIntrinsics-infer-ptr-type.ll` ([#188950](https://github.com/llvm/llvm-project/pull/188950)) |
| 2026-03-31 | [a839e500e8a1](https://github.com/llvm/llvm-project/commit/a839e500e8a1934d3ad0a346d3789904c2a865a9) | New `SPIRVEmitIntrinsics-infer-fnptr-todo-type.ll` ([#189413](https://github.com/llvm/llvm-project/pull/189413)) |

### Gaps detected on PRs

Lines added or changed in LLVM pull requests that baseline coverage (including tests in the PR) still does not hit. Identified with PR gap finding and reported as review feedback on the PR.

#### AMDGPU

| Date | PR | Summary |
|------|-----|---------|
| 2026-08-04 | [#211465](https://github.com/llvm/llvm-project/pull/211465#issuecomment-5179521133) | [AMDGPU] TFE D16 format buffer loads |
| 2026-08-04 | [#213202](https://github.com/llvm/llvm-project/pull/213202#issuecomment-5179767021) | [AMDGPU] Negated f16 and fp conversion DAG combines |
| 2026-08-04 | [#212507](https://github.com/llvm/llvm-project/pull/212507#issuecomment-5179801936) | [AMDGPU] FLAT_SCRATCH in SILoadStoreOptimizer |
| 2026-08-04 | [#212536](https://github.com/llvm/llvm-project/pull/212536#issuecomment-5179822882) | [AMDGPU] MachinePipeliner support |
| 2026-08-04 | [#212539](https://github.com/llvm/llvm-project/pull/212539#issuecomment-5179840636) | [AMDGPU] Register pressure of pipelined loops |

#### SPIR-V

| Date | PR | Summary |
|------|-----|---------|
| 2026-08-05 | [#212999](https://github.com/llvm/llvm-project/pull/212999#issuecomment-5193889662) | [SPIRV] Legalize byte-buffer reinterpretation ptrcasts |
