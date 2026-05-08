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

The coverage CLI lives under **`src/coverage/`** (Python package **`coverage`**).

The script `scripts/test_coverage.sh` shows how to run the coverage gap identification process start to finish. Below are details of each step in the process.

The inputs are:
- An LLVM build instrumented with `sancov` at the basic block level
- A directory of new tests
- Configuration options (shown in `scripts/test_coverage.sh`) to control parameters such as the target file of interest, the number of new tests to run, and the type of coverage (full line vs partial line)

The output is:
- A `.csv` file with format `cols=['test','file','line','covered_addresses']` that lists new tests that cover lines of code in the target files that are not covered by the LLVM test suite. This can be used as an input to the reducer. 
- Intermediate data files containing more details on new coverage.

### Prerequisites 

For **llvm-lit** tests under `llvm-project/llvm/test` (e.g. AMDGPU `CodeGen/AMDGPU`), copy **`config/amdgpu-be/lit.local.cfg.py`** into the matching test tree so LIT forwards **`UBSAN_OPTIONS`** to subprocesses.

Build LLVM twice:
- Once uninstrumented with the `sancov` tool
- Once instrumented with coverage

#TODO: add clearer instructions for the LLVM builds and reference the build scripts

### Subcommands

| Subcommand | Status |
|------------|--------|
| **`test-suite`** |  Get baseline coverage of the LIT test suite. |
| **`new-tests`** | Get coverage of new tests. |
| **`diff`** | Get incremental coverage of new tests relative to the baseline test suite coverage. |

### `test-suite` — inputs

Run from the repo root:

```text
python -m coverage test-suite --llvm-bin DIR --instrumented-bin DIR [--output-dir DIR] [--filter PREFIX] [--debug]
```

| Input | Required | Meaning |
|--------|----------|---------|
| **`--llvm-bin`** | Yes | Directory containing the **uninstrumented** LLVM tools, in particular **`sancov`**, used to merge (`sancov -union`) and symbolize (`sancov -symbolize`) raw coverage files. |
| **`--instrumented-bin`** | Yes | Directory containing **`llvm-lit`**, **`llc`**, and **`opt`** from a **SanitizerCoverage-instrumented** build (same revision/layout you use for lit). |
| **`--output-dir`** | No | Root directory for **all artifacts** from this run. Parent directories are created as needed. If omitted, the default path is whatever the package defines as its default output root (see `src/coverage/constants.py`). |
| **`--filter`** | No | Passed to lit as **`--filter=<PREFIX>`**. If you omit it, the code uses the built-in default filter (same idea as restricting to **`CodeGen/AMDGPU`**; see `DEFAULT_LIT_FILTER` in `src/coverage/constants.py`). |
| **`--debug`** | No | Prints the lit argv, cwd, **`UBSAN_OPTIONS`**, and coverage directory **instead of executing** lit or standalone test subprocesses—use it only to inspect what would run. |

### `test-suite` — outputs

All paths are under **`--output-dir`** unless noted.

#### Main outputs

| Output | Description |
|--------|-------------|
| **`llc_address_line_map.csv`** | Top-level CSV in **`--output-dir`** (default name from `DEFAULT_LLC_ADDRESS_LINE_MAP_FILE`) mapping **source file**, **line**, and **hex point id** from llc coverage. |
| **`joint_llc_and_opt_coverage.csv`** | Top-level CSV in **`--output-dir`** (default name from `DEFAULT_JOINT_LLC_AND_OPT_COVERAGE_FILE`) built from shared **`(file, line, col)`** points present in both llc and opt symcovs. In current **`coverage_mode="full"`**, a row is kept when all shared points on that **`(file, line)`** are covered by **either** llc or opt. |

Note: coverage selection rules are currently limited to **`coverage_mode="full"`** in `src/coverage/sancov.py`. Other modes (for example, partial-coverage style rules) may be added in the future but are not implemented yet.

#### Intermediate outputs

| Output | Description |
|--------|-------------|
| **`raw_sancov/`** | Raw SanitizerCoverage **`*.sancov`** shards from the lit run (names follow LLVM’s **`<binary>.<id>.sancov`** pattern for each instrumented binary). |
| **`processed_sancov/llc.0.sancov`**, **`llc.0.symcov`** | Merged union of all raw **`llc.*.sancov`**, then **JSON symcov** from **`sancov -symbolize`** using the **instrumented** `llc` binary. |
| **`processed_sancov/opt.0.sancov`**, **`opt.0.symcov`** | Same for **`opt`**. |


### Example

```bash
source venv/bin/activate   # optional
PYTHONPATH=src python -m coverage test-suite \
  --output-dir "$HOME/fuzz-fill/data/coverage_output/my_run" \
  --llvm-bin "$LLVM/build/bin" \
  --instrumented-bin "$LLVM/build-amdgpu-bb/bin" \
  --filter "CodeGen/AMDGPU"
```

Use `python -m coverage test-suite --help` for the authoritative flag list.

### `new-tests` — inputs

Run from the repo root:

```text
python -m coverage new-tests --llvm-bin DIR --instrumented-bin DIR --new-tests-dir DIR [--n N] [--output-dir DIR] [--debug] [--filter PREFIX]
```

| Input | Required | Meaning |
|--------|----------|---------|
| **`--instrumented-bin`** | Yes | Directory containing the **instrumented** `llc` binary used to execute each new test and emit sancov data. |
| **`--new-tests-dir`** | Yes | Root directory scanned recursively for input files matching **`*.ll`** and **`*.bc`**. |
| **`--n`** | No | Maximum number of discovered tests to run, after sorting by path. Default is **`1`**. |
| **`--output-dir`** | No | Root directory for artifacts from this run. Parent directories are created as needed. If omitted, uses the package default output root from `src/coverage/constants.py`. |
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
PYTHONPATH=src python -m coverage new-tests \
  --output-dir "$HOME/fuzz-fill/data/coverage_output/new_tests_run" \
  --llvm-bin "$LLVM/build/bin" \
  --instrumented-bin "$LLVM/build-amdgpu-bb/bin" \
  --new-tests-dir "$HOME/fuzz-fill/data/new_tests" \
  --n 25
```

Use `python -m coverage new-tests --help` for the authoritative flag list.

## Reduce module

The `reduce` package drives **testcase reduction** for tests that cover new lines of code as identified by the coverage module. It reads a small JSON config, runs a **pass pipeline**, and writes a reduced test under an output directory.

The inputs are:

- A **JSON config** that points at the testcase (`input`), LLVM source metadata (`file`, `line`), an ordered **`pipeline`** of reducer passes, and paths to **interestingness scripts** where a pass needs them.
- **`--llvm-bin`**: directory with `llvm-reduce`, `llc`, and anything your interesting scripts invoke.

The output is:

- A directory (from **`output_dir`** in the config, or a timestamped default under `data/output/<input-basename>/`) containing step artifacts under **`tmp/`** and a final **`reduced.ll`** or **`reduced.mir`** (suffix matches the last pipeline stage).

### From coverage module output to a reduction example

The coverage module emits a CSV of incremental new coverage whose columns are `test_name`, `file`, `line`, and `covered_addresses` (see **Coverage module** — same shape as the file described there). Each row maps a **new test artifact** (`test_name`, typically a `.bc` or `.ll` under your new-tests directory) to a **source location** in LLVM (`file`, `line`) and one or more **SanitizerCoverage point ids** for that line (`covered_addresses`, semicolon-separated `0x…` values).

To turn one row into something you can reduce:

1. **Pick a row** you care about (often you filter to a single `test_name` first, then choose the `file`/`line` you want minimized toward).
2. Set **`input`** in the config to that testcase file. Copy or symlink the file named in `test_name` next to the config (or use an absolute path); the name in the CSV is the basename the coverage run used.
3. Set **`file`** to the LLVM-relative source path: strip any prefix before `llvm/` so it matches your checkout, e.g. `llvm/lib/Target/AMDGPU/SIInstrInfo.cpp` (the CSV may store an absolute path like `…/llvm-project/llvm/lib/Target/AMDGPU/…`).
4. Set **`line`** to the integer from the **`line`** column.
5. **Interestingness** depends on your goal. For “still hits this coverage point after `llc`”, modify the example in `example/amd/new-test-1/interesting_ir.sh` using one hex id from **`covered_addresses`**.

Two examples for the AMDGPU backend are shown in `scripts/reduce_amd_coverage_based.sh` and `scripts/reduce_amd_argument_usage_multi_addr.sh`.

Example row shape (fields only; paths vary by machine):

```text
<test_name>.bc,…/llvm/lib/Target/AMDGPU/SIInstrInfo.cpp,5112,0x61d2dd3
```

That row says: this input still exercises `SIInstrInfo.cpp` line **5112** and you can treat **0x61d2dd3** as a coverage guard in your script. The checked-in **`example/amd/new-test-1`** config was built the same way for a different line and address on the same file: it pins **`SIInstrInfo.cpp:6069`** and **`COVERED=0x61d4b9a`** in `interesting_ir.sh`, with **`input`** set to the corresponding `.bc` beside `config.json`.

`example/amd/new-test-1/config.json` runs a single IR reduction step:

```json
"pipeline": [
  {
    "id": "llvm_reduce_ir",
    "parameters": { "interesting": "interesting_ir.sh" }
  }
]
```

Run it from the repo root (after `pip install -e .` or with `PYTHONPATH=src`):

```bash
cd src
python -m reduce --config ../example/amd/new-test-1/config.json --llvm-bin "$LLVM/build/bin"
```

Adjust `--llvm-bin` and the hard-coded `LLVM_BIN` inside `interesting_ir.sh` for your trees.

### Example pipelines in `example/*/config.json`

Other checked-in configs illustrate longer pipelines (paths are all under `example/`):

| Directory | Pipeline idea |
|-------------|----------------|
| **`spirv/icmp`**, **`spirv/emit-intrinsics`** | `snapshot` then `llvm_reduce_ir` with `interesting.sh` (crash/assert style). |
| **`amd/si-i1-copies`** | `llvm_reduce_ir` → `extract_mir_before_pass` (`pass_under_test` `si-i1-copies`, `mtriple` / `llc_O`) → `llvm_reduce_mir` with `interesting_mir.sh`. |
| **`amd/si-sgpr-spills`** | `llvm_reduce_ir` → `extract_ir_before_pass` (`amdgpu-remove-incompatible-functions`) → `llvm_reduce_ir` → `extract_mir_before_pass` (`si-lower-sgpr-spills`) → `llvm_reduce_mir` → `creduce`. |

Open each **`config.json`** for full `parameters` (`mtriple`, `llc_O`, script names, etc.).

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
| `extract_ir_before_pass` | `ExtractIrBeforePass` | Same idea as above but **without** `-simplify-mir`; output is sliced IR (e.g. `tmp/NN_ir_before_pass.ll` or `tmp/NN_<extract_ir_before_output>`). |

After the last pass, the result is copied to **`output_dir/reduced.ll`** or **`reduced.mir`** (same suffix as the final artifact).

**`--only-pass`** — runs exactly one pass by id; the input file is always the config **`input`** path. For `llvm_reduce_mir`, that file should be MIR (use a full pipeline first, or point `input` at a `.mir` for debugging).

### Config JSON

One top-level object. **Required:**

- `input` — path to the original `.ll` or `.bc` file.
- `file`, `line` — LLVM source location metadata (used when constructing the in-memory `Test` object).
- `pipeline` — non-empty JSON array; each element is an object with **`id`** (the pass id) and optional **`parameters`** (a JSON object of options for that step only). You may also put option keys directly on the step object next to **`id`** instead of nesting them under **`parameters`**. Order is execution order; repeats are allowed. See `example/amd/new-test-1/config.json`.

**Optional (top-level):**

- `replacement` — how the line of interest in LLVM should be replaced to trigger the interestingness test; not consumed by reduction today.
- `output_dir` — where to write `reduced.ll` and `tmp/`.
- `action` — e.g. `reduce` or `test`.

**Per-step `parameters`** (and which passes accept them) — put these on the matching pipeline step, not at the top level:

- **`llvm_reduce_ir`**, **`creduce`**: `interesting` — path to an executable script: candidate path as `$1`; exit `0` if still “interesting”. For `creduce`, a copy is written under `tmp/` with `"$1"` replaced by the shell-quoted **basename** of the candidate (e.g. `05_creduce.mir`), and that copy is passed to `creduce`.
- **`creduce`**: `n` — positive integer passed as `creduce --n`; if omitted, uses half of `os.cpu_count()` (minimum 1).
- **`llvm_reduce_mir`**: `interesting_mir` — same contract for `llvm-reduce -x=mir`; `$1` is the candidate **`.mir`** file.
- **`extract_mir_before_pass`**, **`extract_ir_before_pass`**: `pass_under_test` — LLVM pass id for `llc --stop-before` (e.g. `si-i1-copies`). **`mtriple`** — target triple for `llc` (e.g. `amdgcn-amd-amdhsa`). **`llc_O`** — string passed through to `llc` before `-mtriple` (e.g. `"-O1"`, `"-Os"`, or `"-O2 -mllvm …"` per shell splitting); use `""` to omit extra `-O` flags.
- **`extract_mir_before_pass`**: `extract_mir_output` — optional MIR filename (basename only); written under `tmp/` as `NN_<name>`. Defaults to `NN_mir_before_pass.mir`.
- **`extract_ir_before_pass`**: `extract_ir_before_output` — optional IR filename (basename only); defaults to `NN_ir_before_pass.ll`.

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

### Interesting script

Your script must match **`llvm-reduce`’s contract**: it receives the path to a candidate IR file and must exit `0` only when that candidate still reproduces whatever you care about (crash, wrong output, etc.). See `example/interesting.sh` for a pattern using `llc` and filtering stderr.
