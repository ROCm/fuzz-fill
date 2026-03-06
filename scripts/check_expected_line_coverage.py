'''
Run a fuzzer test on the instrumented backend and look at the coverage - check we can see the line that we expect in the covered version
'''
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from utils import get_repo_base, get_file, get_line_number


def parse_args(base: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Check expected line coverage.')
    parser.add_argument('--target', '-t', choices=['spirv', 'amd'], default='spirv',
                        help='Target: spirv or amd (default: spirv)')
    parser.add_argument('--llvm-project', type=Path, default=None,
                        help='Path to llvm-project root (default: base/llvm-project)')
    parser.add_argument('--build-dir', type=Path, default=None,
                        help='Path to LLVM build directory for specific backends')
    parser.add_argument('--coverage-dir', type=Path, default=None,
                        help='Directory for ASan coverage output (default: base/coverage_output/<target>_<timestamp>)')
    args = parser.parse_args()
    args.llvm_project = args.llvm_project or base / 'llvm-project'
    args.build_dir = args.llvm_project / (args.build_dir or Path('build/bin'))
    if args.coverage_dir is not None:
        args.coverage_dir = Path(args.coverage_dir).resolve()
    else:
        args.coverage_dir = (base / 'coverage_output' / f'{args.target}_{int(time.time())}').resolve()
    return args


def load_test_map(path: Path) -> dict[str, str]:
    with open(path, 'r') as f:
        return json.load(f)


def run_one_test(
    llc_bin: Path,
    test_cmd: str,
    fuzzer_test_dir: Path,
    coverage_dir: Path,
) -> subprocess.CompletedProcess:
    """Run a single llc test with ASan coverage enabled."""
    cmd = [str(llc_bin)] + test_cmd.split()[1:]
    env = os.environ.copy()
    env['ASAN_OPTIONS'] = f'coverage=1:coverage_dir={coverage_dir}'
    return subprocess.run(cmd, cwd=fuzzer_test_dir, capture_output=True, text=True, env=env)


def symbolize_coverage(
    coverage_dir: Path,
    llc_bin: Path,
    build_dir: Path,
    test_cmd: str,
    fuzzer_test_dir: Path,
) -> None:
    """Find the newest .sancov for the binary in coverage_dir and write a .symcov file."""
    binary_name = llc_bin.name
    sancov_files = sorted(
        coverage_dir.glob(f'{binary_name}.*.sancov'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not sancov_files:
        print('  (no .sancov file found, skipping symbolize)')
        return
    latest_sancov = sancov_files[0]
    safe_name = test_cmd.replace(' ', '_').replace('/', '_').strip()
    symcov_path = coverage_dir / f'{safe_name}.symcov'
    sancov_bin = build_dir / 'sancov'
    if not sancov_bin.exists():
        print(f'  (sancov not found at {sancov_bin}, skipping symbolize)')
        return
    with symcov_path.open('w') as f:
        subprocess.run(
            [str(sancov_bin), '-symbolize', str(latest_sancov), str(llc_bin)],
            cwd=fuzzer_test_dir,
            check=True,
            stdout=f,
        )
    print(f'  -> {symcov_path}')


def main():
    base = get_repo_base(__file__)
    args = parse_args(base)

    args.coverage_dir.mkdir(parents=True, exist_ok=True)
    fuzzer_test_dir = base / 'fuzzer-tests' / args.target
    test_map = load_test_map(fuzzer_test_dir / 'test_map.json')
    llc_bin = args.build_dir / 'llc'

    for test_cmd, url in test_map.items():
        parts = test_cmd.split()
        if not parts or parts[0] != 'llc':
            print(f'Skipping unsupported command: {test_cmd!r}')
            continue

        print(f'Running: {[str(llc_bin)] + parts[1:]}')
        result = run_one_test(llc_bin, test_cmd, fuzzer_test_dir, args.coverage_dir)

        if result.returncode != 0:
            print(f'  stderr: {result.stderr}')
        else:
            print('  ok')

        symbolize_coverage(
            args.coverage_dir, llc_bin, args.build_dir, test_cmd, fuzzer_test_dir
        )


if __name__ == '__main__':
    main()
