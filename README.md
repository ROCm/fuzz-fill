# fuzz-fill

Fuzzing to fill test suite gaps.

## Python environment

Create a virtual environment, **activate it**, then install the project. With the venv active, `pip` installs into that environment only (not your system Python), including dependencies such as **pandas**:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

This installs editable packages, console scripts (`reduce`, `llvm-test-suite-coverage`), and **`pandas`** (used by **`coverage map`**). **`coverage run`** does not import **`coverage.map`**, but pandas is still a declared dependency of the package.

## Coverage module

### TL;DR

To get coverage of the LLVM test-suite tests under `llvm-project/llvm/test/CodeGen/AMDGPU` of the AMDGPU backend, first drop the file `config/amdgpu-be/lit.local.cfg.py` in `llvm-project/llvm/test/CodeGen/AMDGPU`. The LIT test runner will pick this up and know which environment variables it needs to pass on to the local test-running environment. Next, run the coverage module with the options specified in this script:
```
./scripts/run_get_llvm_test_suite_coverage.sh
```

To run the same steps in order, edit **`OUT_BASENAME`** and **`BUILD_DIR`** (and **`WORK_ROOT`** if needed) in **`scripts/full_coverage_run.sh`**, then run `./scripts/full_coverage_run.sh` with no arguments. Each step script still accepts its own optional coverage-directory argument when run alone; see comments at the top of each file under `scripts/`.

This will output coverage files and process them into two summaries, one for `llc` and one for `opt`. Raw per-process `.sancov` files land under `data/coverage_output/$OUTPUT_ID/raw_sancov/`; merged outputs are (by default) `llc.0.sancov`, `llc.0.symcov`, `opt.0.sancov`, and `opt.0.symcov` in the output directory root, where `OUTPUT_ID` is either the `OUT_BASENAME` set in `full_coverage_run.sh` or a date-time ID when `--coverage-dir` is omitted.

The next step is to generate a single `.sancov` file that contains the full *joint* coverage of both `llc` and `opt` tests. This is so that we can quickly check new tests' coverage against a single sancov file correctly encoded for `llc`. The binary mapping for `opt` is different than `llc`, so we need to map the line coverage in `opt.0.symcov` back to the `llc` `sancov`.

To get the single `sancov` file, run:
```
./scripts/run_get_joint_sancov.sh
```

This will output a `csv` file in the coverage directory that contains all lines covered by either `opt` or `llc` and the list of addresses in the `llc` `sancov` binary that those lines correspond to. This is the set of addresses that new coverage output should be checked against. If the `sancov` file of a test run with `llc` contains an address that does *not* appear in the output `csv` file, then the test has achieved new coverage and should be a candidate test for addition to the test suite.

And to get a mapping from llc lines to addresses, run:
```
./scripts/run_get_llc_line_addr_map.sh
```

Next, run:
```
./scripts/run_get_new_test_coverage.sh
```

This will run a set of new tests (that must be pre-existing in a directory), get the line coverage of these tests, and record whether any additional lines have been covered. Pass **`--coverage-dir`** as the parent directory from a prior **`coverage run`** (the same folder that contains `covered_either.csv` and merged `llc.0.*` artifacts). The tool writes only under **`new-tests/`** there: `llc_test_report.csv`, novel-line subdirectories, and raw `llc.<pid>.sancov` files under **`new-tests/raw_sancov/`** when llc runs. **`--baseline-csv`** and **`--line-address-map`** default to **`covered_either.csv`** and **`llc.0.point_symbol_info.json`** next to **`--coverage-dir`** when those files exist and the flags are omitted.

Next, run:
```
run_analyse_new_coverage.sh
```

This will analyse the incremental coverage of the new tests and produce a list of non-duplicate new coverage. It will save details of the tests of interest and the new lines they cover in `analyse_stacked_novel_lines/all_novel_source_lines.csv` within the new test output folder.

### Summary

The `coverage` package (under `src/coverage/`) drives **LLVM SanitizerCoverage** from **llvm-lit** (or a custom command): it sets `UBSAN_OPTIONS` so runs emit raw `*.sancov` files under **`raw_sancov/`** inside the output directory, **merges** them per instrumented binary with `llvm-sancov -union`, **symbolizes** with `sancov -symbolize`, prints **coverage stats**, and writes **`coverage_outline.txt`** in the chosen output directory (and optional **`--outline-json`**).

Use an LLVM **build** that matches the tests (same `llc`, `opt`, etc., built with SanitizerCoverage as you already use for lit). Raw files are `raw_sancov/<binary>.<digits>.sancov`; merged outputs in the directory root are `<binary>.0.sancov` / `.symcov` (the basename prefix must match the binary—required by LLVM’s `sancov`).

### Layout

| Piece | Role |
|-------|------|
| `SanCov` | Merge raw `.sancov`, symbolize, stats for one `build/.../bin` tree |
| `TestCommandRunner` | Runs the test command with `coverage_dir` (typically `…/raw_sancov`) wired into `UBSAN_OPTIONS` |
| `CoverageSession` | Runs tests (unless `--skip-run`), then each `--binary`, then outline output |
| `CoverageConfig` | Resolved paths and options for a run |

### How to run

The CLI uses **subcommands**:

- **`run`** — llvm-lit (or `-c`) plus merge/symbolize (this is the default if you start with a flag, e.g. `python -m coverage --cwd …` is treated as `run`).
- **`map`** — four paths (llc/opt symcov and sancov). Use **`--get-summary`** for the JSON summary (loads whole `.symcov` files; can be large), and/or **`--create-joint-sancov`** for a joint llc-oriented `.sancov` (when implemented). At least one of those flags is required.

Examples:

- **Console script** (after `pip install -e .`): `llvm-test-suite-coverage run …`, `llvm-test-suite-coverage map …`
- **Module**: `PYTHONPATH=src python -m coverage run …` or `… map …` from the repo root (or after install).

Top-level help: `python -m coverage --help` lists `{run,map}`. Per-command: `python -m coverage run --help`, `python -m coverage map --help`.

If the PyPI **`coverage`** package is installed in the same environment, ensure this project’s `coverage` is found first (e.g. `PYTHONPATH=src` when working from a clone) so `python -m coverage` hits `src/coverage`, not the third-party tool.

### `run` flags

- **`--cwd`** — LLVM **build directory** (e.g. `build-amdgpu/`); default test command runs `./bin/llvm-lit` relative to it.
- **`--build-dir`** — Same tree (or its `bin`); used to locate `sancov`, `llc`, `opt`, etc. Defaults to `<llvm-project>/build` when `--llvm-project` is unset.
- **`--filter`** — Passed to the default lit invocation as `--filter=…` (default `CodeGen/AMDGPU`). Ignored if you pass **`--command` / `-c`**.
- **`--binary`** — Repeat per tool; default is **`llc`** and **`opt`**. Skip a binary if there are no raw `.sancov` files for it under **`raw_sancov/`**.
- **`--coverage-dir`** — Output root: **`raw_sancov/`** for raw per-run files, merged **`.sancov` / `.symcov`** and reports in the root (default under `data/coverage_output/test_suite_<timestamp>`).
- **`--skip-run`** — Only merge/symbolize; **`--coverage-dir`** must already contain raw inputs under **`raw_sancov/`** from a prior run.
- **`--outline-json`** — Extra machine-readable summary (`binaries` + `run_summary`).

Use `llvm-test-suite-coverage run --help` for the full list.

### `new-tests` flags

- **`--coverage-dir`** — **Required.** Parent output directory from **`coverage run`** (defaults for baseline and line map resolve here).
- **`--tests-dir`** — **Required.** Directory tree searched for `*.ll` / `*.bc`.
- **`--baseline-csv`** — Optional; defaults to **`covered_either.csv`** next to **`--coverage-dir`** if present.
- **`--line-address-map`** — Optional; defaults to **`llc.0.point_symbol_info.json`** next to **`--coverage-dir`** if present (requires a baseline when used).

Use `llvm-test-suite-coverage new-tests --help` for the full list.

### `map`

Four positional paths (order fixed). Then choose at least one action:

- **`--get-summary`** — write JSON (stdout, or **`--output` / `-o`** for a file): per-symcov top-level keys, optional `BinaryHash` / list lengths when present, byte size for each `.sancov`.
- **`--create-joint-sancov`** — union of covered `(file, function, line)` from llc and opt symcov. Prints a one-line count summary to the terminal (llc-only / opt-only / either deduped), not the full location list. With **`--get-summary`**, stdout JSON includes **`joint_coverage_line_counts`** (`llc`, `opt`, `either_deduped`); the full **`joint_covered_locations`** list is written only when **`--output` / `-o`** is set (each entry includes **`llc_addresses`** as for the CSV). Does not emit the symcov summary JSON unless **`--get-summary`** is also set.
- **`--joint-csv PATH`** — with **`--create-joint-sancov`**, write the **union** of locations covered by llc **or** opt (deduped on `file`, `function`, `line`) to that CSV, plus **`llc_addresses`**: a JSON array of hex coverage point ids from the llc symcov **`point-symbol-info`** for that exact `(file, function, line)` (all instrumented points for the line, not only those hit in `covered-points`). Rows only covered via opt may get `[]` if the llc symcov uses different path or function strings. Creates parent dirs if needed.
- **`--joint-file-prefix PREFIX`** — with **`--create-joint-sancov`**, only keep source paths under this prefix (after `expanduser`, compared as POSIX paths). Filtering runs on the point table **before** merging with covered ids, so the union/CSV work stays smaller. Mutually exclusive with **`--no-joint-file-filter`**.
- **`--no-joint-file-filter`** — with **`--create-joint-sancov`**, include all paths from symcov (legacy behavior: no path filter). Mutually exclusive with **`--joint-file-prefix`**. If neither flag is set, the default is to keep only paths that contain a directory component named **`llvm-project`** (typical checkout layout).

```text
coverage map llc-symcov llc-sancov opt-symcov opt-sancov --get-summary [-o OUT.json]
coverage map … --create-joint-sancov
coverage map … --create-joint-sancov --joint-csv covered_either.csv
coverage map … --get-summary --create-joint-sancov
```

### Example

Full run (adjust paths). You can use **`run` explicitly** or omit it when the first argument is an option:

```bash
source venv/bin/activate   # optional
PYTHONPATH=src python -m coverage run \
  --cwd "$LLVM_BUILD" \
  --build-dir "$LLVM_BUILD" \
  --filter "CodeGen/AMDGPU"
```

Re-process **opt** only from an existing output dir:

```bash
PYTHONPATH=src python -m coverage run \
  --skip-run \
  --binary opt \
  --coverage-dir /path/to/data/coverage_output/test_suite_XXXXX \
  --build-dir "$LLVM_BUILD" \
  --cwd "$LLVM_BUILD"
```

Summarize four merged files:

```bash
PYTHONPATH=src python -m coverage map \
  llc.0.symcov llc.0.sancov opt.0.symcov opt.0.sancov \
  --get-summary -o coverage_map_summary.json
```

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
