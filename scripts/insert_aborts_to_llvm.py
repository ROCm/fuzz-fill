import json
import argparse
import subprocess
from pathlib import Path

from src.reduce.utils import get_repo_base, get_file, get_line_number

def abort_at_line(info: dict) -> None:
    """Replace the line in info['file'] at info['line'] with info['replace']."""
    path = info["file"]
    line = info["line"]
    replacement_line = info["replace"]
    lines = path.read_text().splitlines(keepends=True)
    idx = line - 1
    lines[idx] = replacement_line
    path.write_text("".join(lines))
    cmd = ["git", "diff", path]
    result = subprocess.run(cmd, cwd=path.parent, capture_output=True, text=True)
    if result.stdout == "":
        raise RuntimeError("File not modified!")
        
def main():
    base = get_repo_base(__file__)
    parser = argparse.ArgumentParser(description='Insert aborts for coverage gaps.')
    parser.add_argument('--target', '-t', choices=['spirv', 'amd'], default='spirv',
                        help='Target: spirv or amd (default: spirv)')
    parser.add_argument('--llvm-project', type=Path, default=None,
                        help='Path to llvm-project root (default: base/llvm-project)')
    parser.add_argument('--reverse', '-r', action='store_true',
                        help='Reverse: git restore each file that had an abort added')
    args = parser.parse_args()

    target = args.target
    llvm_project = args.llvm_project if args.llvm_project is not None else base / 'llvm-project'
    fuzzer_test_dir = base / 'fuzzer-tests' / args.target
    gaps_file = fuzzer_test_dir / f'coverage_gaps_{target}.json'

    # Load coverage gaps
    with open(gaps_file, 'r') as f:
        raw_gaps: dict[str, str] = json.load(f)

    gap_files: dict = { x : {'file' : get_file(llvm_project, x), 'line' : get_line_number(x), 'replace':  v} for x, v in raw_gaps.items()}

    if args.reverse:
        # Restore each unique file that was modified (had an abort added)
        seen = set()
        for info in gap_files.values():
            path = info.get('file')
            if path is None:
                continue
            path = Path(path)
            if not path.is_absolute():
                path = llvm_project / path
            try:
                rel = path.relative_to(llvm_project)
            except ValueError:
                continue
            key = rel.as_posix()
            if key in seen:
                continue
            seen.add(key)
            print(f'Restoring {rel}')
            subprocess.run(['git', 'restore', str(rel)], cwd=llvm_project, check=True)
        return

    for id, info in gap_files.items():
        print(f'File-line: {id}')
        abort_at_line(info)

if __name__ == "__main__":
    main()