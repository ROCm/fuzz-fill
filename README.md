# fuzz-fill

Fuzzing to fill test suite gaps.

## Reduce module

The `reduce` package drives **LLVM testcase reduction**: it reads a small JSON config, runs a **pass pipeline**, and writes artifacts under an output directory.

### What it does

1. **Loads config** — One JSON object describes a single testcase. Paths in the JSON are resolved relative to the config file’s directory unless they are absolute.
2. **Chooses an output directory** — Either `output_dir` from the config or a timestamped path under `data/output/<original-ll-basename>/` (see below).
3. **Runs `action`** — `reduce` (default) runs the reducer; `test` is reserved for running the test harness (not fully wired yet).

For **`action: reduce`** (or default), the tool runs the **`pipeline`**: an ordered list of **pass ids** defined in the config (the same id may appear more than once). Valid ids are whatever the reducer registers (see table below).

| Pass id | Class | Behavior |
|---------|--------|----------|
| `snapshot` | `SnapshotPass` | Copies the input `.ll` into `output_dir/tmp/00_snapshot.ll` (step index may differ). |
| `llvm_reduce_ir` | `LlvmReduceIrPass` | Runs `llvm-reduce` with `--test=<interesting script>`, writes `…/NN_llvmreduce.ll`, cwd `tmp/`. |
| `llvm_reduce_mir` | `LlvmReduceMirPlaceholderPass` | **Stub** — copies through to `…_llvmreduce_mir.ll` (real `llvm-reduce -x=mir` not implemented yet). |

After the last pass, the result is copied to **`output_dir/reduced.ll`**.

**`--only-pass`** — runs exactly one pass by id; the input IR is always the **original** testcase from the config. Artifact names use step index `0`.

### Config JSON

One top-level object. **Required:**

- `input` — path to the original `.ll` file.
- `file`, `line` — LLVM source location metadata (used when constructing the in-memory `Test` object).
- `pipeline` — non-empty JSON array of pass id strings (order = execution order; repeats allowed), e.g. `["snapshot", "llvm_reduce_ir"]` or `["snapshot", "llvm_reduce_mir"]`.

**Optional:**

- `interesting` — path to an executable script **`llvm-reduce` invokes**; it should take the candidate IR path as an argument (e.g. `$1`) and exit `0` if the testcase is still “interesting”, non-zero otherwise.
- `replacement` — how the line of interest in LLVM should be replaced to trigger the interestingness test; not consumed by reduction today.
- `output_dir` — where to write `reduced.ll` and `tmp/`.
- `action` — e.g. `reduce` or `test`.

LLVM’s `bin` directory is **only** passed on the command line (`--llvm-bin`), not in JSON.

Unknown top-level JSON keys emit a **`UserWarning`** (ignored otherwise).

### CLI

Run from `src/` (so `reduce` is importable) or install the package and use the `reduce` console script from `pyproject.toml`.

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
