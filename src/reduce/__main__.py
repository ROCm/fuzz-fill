import argparse
from datetime import datetime
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument('original_test', type=Path, help='The original test to reduce')
    parser.add_argument('llvm_bin', type=Path, help='The path to the llvm-project bin directory')
    parser.add_argument(
        'output_dir',
        nargs='?',
        type=Path,
        help='The directory to output the reduced test',
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
    
    print(args)

if __name__ == '__main__':
    main()