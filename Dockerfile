# syntax=docker/dockerfile:1

FROM ubuntu:24.04 AS llvm-release

ARG DEBIAN_FRONTEND=noninteractive
ARG LLVM_RELEASE_VERSION=22.1.8
ARG LLVM_TARBALL=LLVM-${LLVM_RELEASE_VERSION}-Linux-X64.tar.xz
ARG LLVM_URL=https://github.com/llvm/llvm-project/releases/download/llvmorg-${LLVM_RELEASE_VERSION}/${LLVM_TARBALL}

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/llvm-releases,sharing=locked \
    set -eux; \
    if [ ! -f "/root/.cache/llvm-releases/${LLVM_TARBALL}" ]; then \
      curl -fsSL "${LLVM_URL}" -o "/root/.cache/llvm-releases/${LLVM_TARBALL}.partial"; \
      mv "/root/.cache/llvm-releases/${LLVM_TARBALL}.partial" "/root/.cache/llvm-releases/${LLVM_TARBALL}"; \
    fi; \
    mkdir -p /opt/llvm-release; \
    tar -xJf "/root/.cache/llvm-releases/${LLVM_TARBALL}" -C /opt/llvm-release --strip-components=1

FROM ubuntu:24.04 AS llvm-source

ARG DEBIAN_FRONTEND=noninteractive
ARG LLVM_RELEASE_VERSION=22.1.8

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/llvm-sources,sharing=locked \
    set -eux; \
    TARBALL="llvm-project-${LLVM_RELEASE_VERSION}.tar.gz"; \
    if [ ! -f "/root/.cache/llvm-sources/${TARBALL}" ]; then \
      curl -fsSL "https://github.com/llvm/llvm-project/archive/refs/tags/llvmorg-${LLVM_RELEASE_VERSION}.tar.gz" \
        -o "/root/.cache/llvm-sources/${TARBALL}.partial"; \
      mv "/root/.cache/llvm-sources/${TARBALL}.partial" "/root/.cache/llvm-sources/${TARBALL}"; \
    fi; \
    mkdir -p /opt/llvm-project; \
    tar -xzf "/root/.cache/llvm-sources/${TARBALL}" -C /opt/llvm-project --strip-components=1

FROM ubuntu:24.04 AS llvm-builder

ARG DEBIAN_FRONTEND=noninteractive
ARG LLVM_RELEASE_VERSION=22.1.8
ARG SANCOV_ALLOWLIST=amdgpu
ARG NINJA_JOBS=""

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cmake \
    curl \
    file \
    ninja-build \
    python3 \
    xz-utils \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

COPY --from=llvm-release /opt/llvm-release /work/llvm-release
COPY --from=llvm-source /opt/llvm-project /work/llvm-project-default

# Optional local llvm-project: pass a named build context when invoking docker build,
# e.g.  docker build --build-context llvm=/path/to/llvm-project ...
# scripts/build-image.sh sets this from --llvm-dir; an empty context falls back to the tagged source.
RUN --mount=type=bind,from=llvm,source=.,target=/llvm-src,ro \
    if [ -d /llvm-src/llvm ]; then \
        echo "local build context (release ${LLVM_RELEASE_VERSION} bootstrap)" > /work/.llvm-source; \
        echo "=== fuzz-fill: LLVM source = local llvm-project (build context) ==="; \
        cp -a /llvm-src /work/llvm-project; \
    else \
        echo "release ${LLVM_RELEASE_VERSION}" > /work/.llvm-source; \
        echo "=== fuzz-fill: LLVM source = GitHub tag llvmorg-${LLVM_RELEASE_VERSION} ==="; \
        cp -a /work/llvm-project-default /work/llvm-project; \
    fi \
 && echo "=== fuzz-fill: LLVM source recorded as: $(cat /work/.llvm-source) ==="

COPY scripts/build-llvm-sancov.sh /usr/local/bin/
COPY scripts/allowlist-amdgpu.txt /work/allowlist-amdgpu.txt
COPY scripts/allowlist-spirv.txt /work/allowlist-spirv.txt
COPY scripts/ignorelist-amdgpu.txt /work/ignorelist-amdgpu.txt
RUN chmod +x /usr/local/bin/build-llvm-sancov.sh

ARG SANCOV_ALLOWLIST=amdgpu
ARG NINJA_JOBS=""
RUN case "${SANCOV_ALLOWLIST}" in \
        amdgpu) allowlist=/work/allowlist-amdgpu.txt; ignorelist=/work/ignorelist-amdgpu.txt ;; \
        spirv) allowlist=/work/allowlist-spirv.txt; ignorelist="" ;; \
        *) echo "error: unsupported SANCOV_ALLOWLIST: ${SANCOV_ALLOWLIST} (expected amdgpu or spirv)" >&2; exit 1 ;; \
    esac \
 && echo "${SANCOV_ALLOWLIST}" > /work/.sancov-allowlist \
 && echo "=== fuzz-fill: SanitizerCoverage allowlist = ${SANCOV_ALLOWLIST} ===" \
 && if [ -n "${ignorelist}" ]; then echo "=== fuzz-fill: SanitizerCoverage ignorelist = ${ignorelist} ==="; fi \
 && llvm_build_start=$(date +%s) \
 && if [ -n "${ignorelist}" ]; then \
        /usr/local/bin/build-llvm-sancov.sh \
            "${allowlist}" \
            /work/llvm-project \
            /work/llvm-build-sancov \
            --bootstrap-bin /work/llvm-release/bin \
            --ignorelist "${ignorelist}" \
            "${NINJA_JOBS}"; \
    else \
        /usr/local/bin/build-llvm-sancov.sh \
            "${allowlist}" \
            /work/llvm-project \
            /work/llvm-build-sancov \
            --bootstrap-bin /work/llvm-release/bin \
            "${NINJA_JOBS}"; \
    fi \
 && llvm_build_secs=$(( $(date +%s) - llvm_build_start )) \
 && echo "${llvm_build_secs}" > /work/.llvm-build-time \
 && echo "=== fuzz-fill: LLVM build wall time: ${llvm_build_secs}s ==="

FROM ubuntu:24.04 AS final

ARG DEBIAN_FRONTEND=noninteractive
ARG UID=1000
ARG GID=1000
ARG USERNAME=developer

RUN apt-get update && apt-get install -y --no-install-recommends \
    creduce \
    git \
    libgcc-s1 \
    libstdc++6 \
    libtinfo6 \
    python3 \
    python3-pip \
    python3-pygments \
    python3-venv \
    python3-yaml \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g "${GID}" "${USERNAME}" \
    && useradd -l -m -u "${UID}" -g "${GID}" -s /bin/bash "${USERNAME}"

COPY --chown=${UID}:${GID} --from=llvm-builder /work/.llvm-source /work/.llvm-source
COPY --chown=${UID}:${GID} --from=llvm-builder /work/.sancov-allowlist /work/.sancov-allowlist
COPY --chown=${UID}:${GID} --from=llvm-builder /work/.llvm-build-time /work/.llvm-build-time
COPY --chown=${UID}:${GID} --from=llvm-builder /work/llvm-project /work/llvm-project
COPY --chown=${UID}:${GID} --from=llvm-builder /work/llvm-build-sancov /work/llvm-build-sancov

COPY --chown=${UID}:${GID} pyproject.toml LICENCE.txt README.md /work/fuzz-fill/
COPY --chown=${UID}:${GID} src /work/fuzz-fill/src
COPY --chown=${UID}:${GID} tests /work/fuzz-fill/tests
COPY --chown=${UID}:${GID} integration-tests /work/fuzz-fill/integration-tests
COPY --chown=${UID}:${GID} scripts /work/fuzz-fill/scripts

RUN echo "=== fuzz-fill image LLVM source: $(cat /work/.llvm-source) ===" \
 && echo "=== fuzz-fill image SanitizerCoverage allowlist: $(cat /work/.sancov-allowlist) ===" \
 && echo "=== fuzz-fill image LLVM build wall time: $(cat /work/.llvm-build-time)s ==="

USER "${UID}"
WORKDIR /work/fuzz-fill
RUN python3 -m venv /work/fuzz-fill-venv && \
    /work/fuzz-fill-venv/bin/pip install --no-cache-dir -e /work/fuzz-fill && \
    echo 'source /work/fuzz-fill-venv/bin/activate' >> ~/.bashrc

ENV VIRTUAL_ENV=/work/fuzz-fill-venv \
    PATH="/work/fuzz-fill-venv/bin:${PATH}" \
    PYTHON="/work/fuzz-fill-venv/bin/python" \
    FUZZ_FILL_SANCOV=/work/llvm-build-sancov/bin/sancov \
    FUZZ_FILL_LLVM_LIT=/work/llvm-build-sancov/bin/llvm-lit \
    FUZZ_FILL_LLC=/work/llvm-build-sancov/bin/llc \
    FUZZ_FILL_OPT=/work/llvm-build-sancov/bin/opt \
    FUZZ_FILL_LLVM_REDUCE=/work/llvm-build-sancov/bin/llvm-reduce \
    FUZZ_FILL_LLVM_DIS=/work/llvm-build-sancov/bin/llvm-dis \
    FUZZ_FILL_LLVM_REPO=/work/llvm-project

# Dev/batch image: runs to completion or interactively, no health check applicable.
HEALTHCHECK NONE
