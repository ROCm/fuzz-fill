import argparse
from pathlib import Path


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    default_output = repo_root / "data" / "test_generation"

    parser = argparse.ArgumentParser(
        description="Generate tests for coverage analysis."
    )
    parser.add_argument(
        "--llvm-bin",
        type=Path,
        required=True,
        help="Path to llvm-project bin directory.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=default_output,
        help="Output directory for generated artifacts (default: %(default)s).",
    )
    ns = parser.parse_args()

    llvm_bin = ns.llvm_bin.resolve()
    output_dir = ns.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[main] llvm-bin={llvm_bin}", flush=True)
    print(f"[main] output={output_dir}", flush=True)


if __name__ == "__main__":
    main()
