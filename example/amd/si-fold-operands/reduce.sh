#!/bin/bash

python3 -m reduce \
    --config /home/macarras/local3/fuzz-fill/example/amd/si-fold-operands/config.json \
    --llc /home/macarras/local3/ubsan-test/llvm-project/build/bin/llc \
    --llvm-reduce /home/macarras/local3/ubsan-test/llvm-project/build/bin/llvm-reduce
