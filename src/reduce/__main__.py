import argparse
from datetime import datetime
from pathlib import Path

from reduce.reducer import Reducer
from reduce.test import Test
from reduce.utils import run_one_test_with_coverage

def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        'original_test', 
        type=Path,
        help='The original test to reduce',
    )
    parser.add_argument(
        'llvm_bin', 
        type=Path, 
        help='The path to the llvm-project bin directory')
    parser.add_argument(
        '--interesting', 
        type=Path,
        default=None,
        help='The interestingness test to use',
    )
    parser.add_argument(
        '--output_dir',
        type=Path,
        default=None,
        help='The directory to output the reduced test',
    )
    parser.add_argument(
        '--line',
        type=int,
        default=None,
        help='The line number for which to retain coverage',
    )
    parser.add_argument(
        '--symcov',
        type=Path,
        default=None,
        help='The path to the symcov file',
    )
    parser.add_argument(
        '--action',
        choices=['reduce', 'test', 'get_interesting_address'],
        default='reduce',
        help='The action to perform',
    )
    args = parser.parse_args()
    current_file = Path(__file__).resolve()
    default_output_dir = (
        current_file.parent.parent
        / 'data'
        / 'output'
        / datetime.now().strftime('%Y%m%d-%H%M%S')
    )
    args.output_dir = args.output_dir or default_output_dir
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Just one test for now
    # TODO: Support multiple tests e.g. using json to load info for each test
    test = Test(args.original_test, args.interesting, args.line, args.symcov)

    if args.action == 'get_interesting_address':
        address = test.get_interesting_address()
        print(f'Address for line {test.line} is {address}')
        
    if args.action == 'test':
        test.run()

    if args.action == 'reduce':
        reducer = Reducer(args.llvm_bin, args.output_dir, [test])
        reducer.reduce()

if __name__ == '__main__':
    main()