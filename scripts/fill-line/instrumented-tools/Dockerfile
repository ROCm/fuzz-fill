# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
# Minimal image for running CI-built instrumented opt/llc/sancov.
# Ubuntu 24.04 ships a glibc new enough for those binaries.
FROM ubuntu:24.04

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        libstdc++6 \
        zlib1g \
        libzstd1 \
        liblzma5 \
        libtinfo6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
ENTRYPOINT []
