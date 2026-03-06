import json
import argparse
from pathlib import Path

from utils import get_repo_base, get_file, get_line_number, abort_at_line


def main():
    base = get_repo_base(__file__)
    parser = argparse.ArgumentParser(description='Insert aborts for coverage gaps.')
    parser.add_argument('--target', '-t', choices=['spirv', 'amd'], default='spirv',
                        help='Target: spirv or amd (default: spirv)')
    parser.add_argument('--llvm-project', type=Path, default=None,
                        help='Path to llvm-project root (default: base/llvm-project)')
    args = parser.parse_args()

    target = args.target
    llvm_project = args.llvm_project if args.llvm_project is not None else base / 'llvm-project'

    gaps_file = base / 'coverage' / 'coverage-info' / f'coverage_gaps_{target}.json'

    # Load coverage gaps
    with open(gaps_file, 'r') as f:
        raw_gaps: dict[str, str] = json.load(f)

    gap_files: dict = { x : {'file' : get_file(llvm_project, x), 'line' : get_line_number(x), 'replace':  v} for x, v in raw_gaps.items()}

    for id, info in gap_files.items():
        print(f'File-line: {id}')
        abort_at_line(info)

if __name__ == "__main__":
    main()