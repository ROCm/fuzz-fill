# fuzz-fill

Fuzzing to fill test suite gaps.

## Reduce module

The `reduce` package drives **LLVM testcase reduction**: it reads a small JSON config, runs a **pass pipeline**, and writes artifacts under an output directory. 

### What it does

1. **Loads config** — Exactly **one** test entry is allowed. Paths in the JSON are resolved relative to the config file’s directory unless they are absolute.
2. **Chooses an output directory** — Either `output_dir` from the config (wrapper form) or a timestamped path under `data/output/<original-ll-basename>/` (see below).
3. **Runs `action`** — `reduce` (default) runs the reducer; `test` is reserved for running the test harness (not fully wired yet).

For **`action: reduce`** (or default), the pipeline is:

| Step | Pass | Behavior |
|------|------|----------|
| 0 | `SnapshotPass` | Copies the input `.ll` into `output_dir/tmp/00_snapshot.ll`. |
| 1 | IR: `LlvmReduceIrPass` | Runs `llvm-reduce` with `--test=<interesting script>`, `-o=…/01_llvmreduce.ll`, and the current IR as input. Working directory for the subprocess is `tmp/` so stray cwd-relative files stay there. |
| 1 | MIR: `LlvmReduceMirPlaceholderPass` | **Stub** — copies through to `01_llvmreduce_mir.ll` (real `llvm-reduce -x=mir` not implemented yet). |

After the last pass, the result is copied to **`output_dir/reduced.ll`**.

### Config JSON

**Simple form** — top-level object is a map with a single key: path to the original `.ll` file, value is the test spec:

- `file`, `line` — source location metadata (used when constructing the in-memory `Test` object).
- `interesting` — path to an executable script **`llvm-reduce` invokes**; it should take the candidate IR path as an argument (e.g. `$1`) and exit `0` if the testcase is still “interesting”, non-zero otherwise.
- `replacement` — shows how the line of interest in `LLVM` should be replaced to trigger the interestingness test, e.g. with an `abort()` or `assert(0)` statement; optional; not consumed by reduction today.

**Wrapper form** — optional top-level fields:

- `tests` — same single-key map as above.
- `output_dir` — where to write `reduced.ll` and `tmp/`.
- `action` — e.g. `reduce` or `test`.

LLVM’s `bin` directory is **only** passed on the command line (`--llvm-bin`), not in JSON.

Unknown JSON keys emit a **`UserWarning`** (ignored otherwise): extra top-level keys in the **wrapper** form, or extra keys inside a **test** object beyond `file`, `line`, `replacement`, and `interesting`.

### CLI

Run from `src/` (so `reduce` is importable) or install the package and use the `reduce` console script from `pyproject.toml`.

```text
python -m reduce --config <path/to/config.json> --llvm-bin <path/to/llvm-project/build/bin> [--engine llvmreduce-ir|llvm-reduce-mir]
```

- **`--config` / `-c`** — required path to the JSON config.
- **`--llvm-bin`** — required; directory containing `llvm-reduce` (and anything your interesting script needs).
- **`--engine`** — `llvmreduce-ir` (default) runs real `llvm-reduce` on IR; `llvm-reduce-mir` uses the MIR placeholder pass only.

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
