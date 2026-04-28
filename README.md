# fuzz-fill

Fuzzing to fill test suite gaps in LLVM.

## Python environment

Create a virtual environment, **activate it**, then install the project. 

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Coverage module

The coverage CLI lives under **`src/new_cov/`** (Python package **`new_cov`**).

### Subcommands

| Subcommand | Status |
|------------|--------|
| **`test-suite`** |  Get baseline coverage of the LIT test suite. |
| **`new-tests`** | Get coverage of new tests. |
| **`diff`** | Get incremental coverage of new tests relative to the baseline test suite coverage. |

### `test-suite` — inputs

For **llvm-lit** tests under `llvm-project/llvm/test` (e.g. AMDGPU `CodeGen/AMDGPU`), install **`config/amdgpu-be/lit.local.cfg.py`** into the matching test tree so LIT forwards **`UBSAN_OPTIONS`** to subprocesses.

Run from the repo root:

```text
python -m new_cov test-suite --llvm-bin DIR --instrumented-bin DIR [--output-dir DIR] [--filter PREFIX] [--debug]
```

| Input | Required | Meaning |
|--------|----------|---------|
| **`--llvm-bin`** | Yes | Directory containing the **uninstrumented** LLVM tools, in particular **`sancov`**, used to merge (`sancov -union`) and symbolize (`sancov -symbolize`) raw coverage files. |
| **`--instrumented-bin`** | Yes | Directory containing **`llvm-lit`**, **`llc`**, and **`opt`** from a **SanitizerCoverage-instrumented** build (same revision/layout you use for lit). |
| **`--output-dir`** | No | Root directory for **all artifacts** from this run. Parent directories are created as needed. If omitted, the default path is whatever the package defines as its default output root (see `src/new_cov/constants.py`). |
| **`--filter`** | No | Passed to lit as **`--filter=<PREFIX>`**. If you omit it, the code uses the built-in default filter (same idea as restricting to **`CodeGen/AMDGPU`**; see `DEFAULT_LIT_FILTER` in `src/new_cov/constants.py`). |
| **`--debug`** | No | Prints the lit argv, cwd, **`UBSAN_OPTIONS`**, and coverage directory **instead of executing** lit or standalone test subprocesses—use it only to inspect what would run. |

### `test-suite` — outputs

All paths are under **`--output-dir`** unless noted.

#### Main outputs

| Output | Description |
|--------|-------------|
| **`llc_address_line_map.csv`** | Top-level CSV in **`--output-dir`** (default name from `DEFAULT_LLC_ADDRESS_LINE_MAP_FILE`) mapping **source file**, **line**, and **hex point id** from llc coverage. |
| **`joint_llc_and_opt_coverage.csv`** | Top-level CSV in **`--output-dir`** (default name from `DEFAULT_JOINT_LLC_AND_OPT_COVERAGE_FILE`) built from shared **`(file, line, col)`** points present in both llc and opt symcovs. In current **`coverage_mode="full"`**, a row is kept when all shared points on that **`(file, line)`** are covered by **either** llc or opt. |

Note: coverage selection rules are currently limited to **`coverage_mode="full"`** in `cov_new/sancov.py`. Other modes (for example, partial-coverage style rules) may be added in the future but are not implemented yet.

#### Intermediate outputs

| Output | Description |
|--------|-------------|
| **`raw_sancov/`** | Raw SanitizerCoverage **`*.sancov`** shards from the lit run (names follow LLVM’s **`<binary>.<id>.sancov`** pattern for each instrumented binary). |
| **`processed_sancov/llc.0.sancov`**, **`llc.0.symcov`** | Merged union of all raw **`llc.*.sancov`**, then **JSON symcov** from **`sancov -symbolize`** using the **instrumented** `llc` binary. |
| **`processed_sancov/opt.0.sancov`**, **`opt.0.symcov`** | Same for **`opt`**. |


### Example

```bash
source venv/bin/activate   # optional
PYTHONPATH=src python -m new_cov test-suite \
  --output-dir "$HOME/fuzz-fill/data/coverage_output/my_run" \
  --llvm-bin "$LLVM/build/bin" \
  --instrumented-bin "$LLVM/build-amdgpu-bb/bin" \
  --filter "CodeGen/AMDGPU"
```

Use `python -m new_cov test-suite --help` for the authoritative flag list.

### `new-tests` — inputs

Run from the repo root:

```text
python -m new_cov new-tests --llvm-bin DIR --instrumented-bin DIR --new-tests-dir DIR [--n N] [--output-dir DIR] [--debug] [--filter PREFIX]
```

| Input | Required | Meaning |
|--------|----------|---------|
| **`--instrumented-bin`** | Yes | Directory containing the **instrumented** `llc` binary used to execute each new test and emit sancov data. |
| **`--new-tests-dir`** | Yes | Root directory scanned recursively for input files matching **`*.ll`** and **`*.bc`**. |
| **`--n`** | No | Maximum number of discovered tests to run, after sorting by path. Default is **`1`**. |
| **`--output-dir`** | No | Root directory for artifacts from this run. Parent directories are created as needed. If omitted, uses the package default output root from `src/cov_new/constants.py`. |
| **`--debug`** | No | Parsed by the CLI, but currently not wired into the `new-tests` execution path. |

### `new-tests` — outputs

All paths are under **`--output-dir`** unless noted.

#### Main outputs

| Output | Description |
|--------|-------------|
| **`raw_sancov/`** | Raw SanitizerCoverage **`*.sancov`** from each new test, saved in a subdirectory that has the name of the test so that tests can be mapped easily to their sancov. |

Note: unlike `test-suite`, `new-tests` does **not** merge or symbolize sancov files.

### `new-tests` — example

```bash
source venv/bin/activate   # optional
PYTHONPATH=src python -m new_cov new-tests \
  --output-dir "$HOME/fuzz-fill/data/coverage_output/new_tests_run" \
  --llvm-bin "$LLVM/build/bin" \
  --instrumented-bin "$LLVM/build-amdgpu-bb/bin" \
  --new-tests-dir "$HOME/fuzz-fill/data/new_tests" \
  --n 25
```

Use `python -m new_cov new-tests --help` for the authoritative flag list.

## Reduce module

The `reduce` package drives **LLVM testcase reduction**: it reads a small JSON config, runs a **pass pipeline**, and writes artifacts under an output directory.

### Quick start

Two examples are given in `example/`:
- The SPIRV example runs a dummy `snapshot` pass that does nothing to the file (useful for debug purposes) and then runs `llvm-reduce` in `ir` form, which is the simplest reduction.
- The AMD exmaple runs `llvm-reduce` in `ir` mode, then extracts the `MIR` from just before the LLVM pass under test, then runs `llfm-reduce` in `mir` mode.

Run them as follows:

```bash
cd src
../scripts/reduce_spirv_icmp.sh
```

```bash
cd src
../scripts/reduce_amd_si_i1.sh
```


### What it does

1. **Loads config** — One JSON object describes a single testcase. Paths in the JSON are resolved relative to the config file’s directory unless they are absolute.
2. **Chooses an output directory** — Either `output_dir` from the config or a timestamped path under `data/output/<original-ll-basename>/` (see below).
3. **Runs `action`** — `reduce` (default) runs the reducer; `test` is reserved for running the test harness (not fully wired yet).

For **`action: reduce`** (or default), the tool runs the **`pipeline`**: an ordered list of **pass ids** defined in the config (the same id may appear more than once). Valid ids are whatever the reducer registers (see table below).

| Pass id | Class | Behavior |
|---------|--------|----------|
| `snapshot` | `SnapshotPass` | Copies the input `.ll` into `output_dir/tmp/00_snapshot.ll` (step index may differ). |
| `llvm_reduce_ir` | `LlvmReduceIrPass` | Runs `llvm-reduce` with `--test=<interesting script>`, writes `…/NN_llvmreduce.ll`, cwd `tmp/`. |
| `creduce` | `CreducePass` | Copies the previous artifact to `…/NN_creduce.<ext>` (same extension as input, e.g. `.mir`), copies the configured interesting script to `…/NN_creduce_interesting.sh`, replaces every literal `"$1"` in that copy with the shell-quoted **basename** of the candidate filename (c-reduce runs the test in a temp dir that contains that file), then runs `creduce --n <N> <copy> <candidate>` (in-place reduction). `<N>` defaults to half of the machine’s logical CPUs (`os.cpu_count()`), at least 1; override with `parameters.n`. The original script must use `"$1"` for the candidate path (same as llvm-reduce). |
| `llvm_reduce_mir` | `LlvmReduceMirPass` | Runs `llvm-reduce -x=mir --test=<interesting_mir>`, writes `…/NN_llvmreduce_mir.mir` (input must be MIR, e.g. after `extract_mir_before_pass`). |
| `extract_mir_before_pass` | `ExtractMirBeforePass` | Runs `llc -o <tmp> <llc_O tokens> -mtriple=<mtriple> -stop-before=<pass_under_test> -simplify-mir <input.ll>`; output is `tmp/NN_mir_before_pass.mir` or `tmp/NN_<extract_mir_output>` (basename only). |

After the last pass, the result is copied to **`output_dir/reduced.ll`** or **`reduced.mir`** (same suffix as the final artifact).

**`--only-pass`** — runs exactly one pass by id; the input file is always the config **`input`** path. For `llvm_reduce_mir`, that file should be MIR (use a full pipeline first, or point `input` at a `.mir` for debugging).

### Config JSON

One top-level object. **Required:**

- `input` — path to the original `.ll` file.
- `file`, `line` — LLVM source location metadata (used when constructing the in-memory `Test` object).
- `pipeline` — non-empty JSON array of pass id strings (order = execution order; repeats allowed), e.g. `["snapshot", "llvm_reduce_ir"]` or `["snapshot", "llvm_reduce_mir"]`.

**Optional:**

- `interesting` — path to an executable script **`llvm-reduce` invokes** for IR; candidate path as `$1`; exit `0` if still “interesting”.
- `interesting` — also used by `creduce`: a copy is written under `tmp/` with `"$1"` replaced by the shell-quoted **basename** of the candidate (e.g. `05_creduce.mir`), and that copy is passed to `creduce`.
- `n` — (**`creduce` only**) positive integer passed as `creduce --n`; if omitted, uses half of `os.cpu_count()` (minimum 1).
- `interesting_mir` — same contract for **`llvm_reduce_mir`** (`llvm-reduce -x=mir`); `$1` is the candidate **`.mir`** file.
- `replacement` — how the line of interest in LLVM should be replaced to trigger the interestingness test; not consumed by reduction today.
- `output_dir` — where to write `reduced.ll` and `tmp/`.
- `action` — e.g. `reduce` or `test`.
- `pass_under_test` — LLVM pass id for `llc --stop-before` when using `extract_mir_before_pass` (e.g. `si-i1-copies`); ignored for other passes.
- `mtriple` — target triple for `llc` (required with `extract_mir_before_pass`), e.g. `amdgcn-amd-amdhsa`.
- `llc_O` — string passed through to `llc` before `-mtriple` (required with `extract_mir_before_pass`): e.g. `"-O1"`, `"-Os"`, or `"-O2 -mllvm ..."` (split with shell rules). Use `""` to omit any `-O`/extra flags.
- `extract_mir_output` — optional MIR filename (basename only); written under `tmp/` as `NN_<name>`. Defaults to `NN_mir_before_pass.mir`.

LLVM’s `bin` directory is **only** passed on the command line (`--llvm-bin`), not in JSON.

Unknown top-level JSON keys emit a **`UserWarning`** (ignored otherwise).

### CLI

Run from `src/` (so `reduce` is importable), or activate your venv, run `pip install -e .` (see **Python environment** above), and use the `reduce` console script from `pyproject.toml`.

```text
python -m reduce --config <path/to/config.json> --llvm-bin <path/to/llvm-project/build/bin> [--only-pass PASS_ID]
```

- **`--config` / `-c`** — required path to the JSON config.
- **`--llvm-bin`** — required; directory containing `llvm-reduce` (and anything your interesting script needs).
- **`--only-pass`** — run a single pass id for debugging (ignores config `pipeline`).

### Example

With the files under `example/`:

```bash
source venv/bin/activate
cd src
../scripts/reduce_spirv_icmp.sh
```

The script passes `--config` and `--llvm-bin`; adjust paths inside the script for your machine.

### Interesting script

Your script must match **`llvm-reduce`’s contract**: it receives the path to a candidate IR file and must exit `0` only when that candidate still reproduces whatever you care about (crash, wrong output, etc.). See `example/interesting.sh` for a pattern using `llc` and filtering stderr.
