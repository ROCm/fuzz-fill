import subprocess
import json
import argparse
from pathlib import PurePosixPath, Path
from urllib.parse import urlparse


def main():
    base = Path(__file__).resolve().parent.parent  # repo root (parent of scripts/)
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

def get_file(llvm_project: Path, url: str) -> Path:
    parts = PurePosixPath(urlparse(url).path).parts

    try:
        llvm_idx = parts.index("llvm", parts.index("llvm-project") + 1)
    except ValueError:
        return None

    return Path(llvm_project, *parts[llvm_idx:])

def get_line_number(url: str) -> int:
    fragment = urlparse(url).fragment 

    if fragment.startswith("L") and fragment[1:].isdigit():
        return int(fragment[1:])

    return None

def abort_at_line(info: dict) -> None:

    path = info['file']
    line = info['line']
    replacement_line = info['replace']

    lines = path.read_text().splitlines(keepends=True)

    idx = line - 1

    lines[idx] = replacement_line

    path.write_text("".join(lines))

    # Check the rewrite worked
    cmd = ['git', 'diff', path]

    result = subprocess.run(cmd, cwd=path.parent, capture_output=True, text=True)

    if result.stdout == '':
        raise RuntimeError('File not modified!')

if __name__ == "__main__":
    main()