#!/usr/bin/env bash
# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
# Build the image used to run instrumented opt/llc/sancov when the host glibc is too old.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
IMAGE="${FUZZ_FILL_TOOLS_IMAGE:-fuzz-fill-instrumented-tools:ubuntu24.04}"

docker build -t "$IMAGE" "$ROOT"
echo "built $IMAGE"
