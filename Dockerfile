# syntax=docker/dockerfile:1
FROM ubuntu:24.04 AS llvm-builder

ARG DEBIAN_FRONTEND=noninteractive
# Parent commit before the first fuzz-fill contribution: https://github.com/llvm/llvm-project/pull/185430.
ARG LLVM_COMMIT=40cd48fd385b57855a104a4192c4d4468889d22d
ARG SANCOV_ALLOWLIST=amdgpu

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    clang \
    cmake \
    curl \
    file \
    ninja-build \
    python3 \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

# Optional local llvm-project: pass a named build context when invoking docker build,
# e.g.  docker build --build-context llvm=/path/to/llvm-project ...
# scripts/build-image.sh sets this from --llvm-dir; an empty context falls back to LLVM_COMMIT.
RUN --mount=type=bind,from=llvm,source=.,target=/llvm-src,ro \
    if [ -d /llvm-src/llvm ]; then \
        echo "local build context" > /work/.llvm-source; \
        echo "=== fuzz-fill: LLVM source = local llvm-project (build context) ==="; \
        cp -a /llvm-src /work/llvm-project; \
    else \
        echo "github ${LLVM_COMMIT}" > /work/.llvm-source; \
        echo "=== fuzz-fill: LLVM source = GitHub tarball (${LLVM_COMMIT}) ==="; \
        curl -fsSL "https://github.com/llvm/llvm-project/archive/${LLVM_COMMIT}.tar.gz" \
            | tar -xz -C /work \
         && mv "/work/llvm-project-${LLVM_COMMIT}" /work/llvm-project; \
    fi \
 && echo "=== fuzz-fill: LLVM source recorded as: $(cat /work/.llvm-source) ==="

# Copy scripts after fetching LLVM so script changes do not invalidate that step.
COPY scripts/build-llvm.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/build-llvm.sh

RUN /usr/local/bin/build-llvm.sh \
    /usr/bin/clang \
    /usr/bin/clang++ \
    /work/llvm-project \
    /work/llvm-build-uninstrumented

COPY scripts/build-llvm-sancov.sh /usr/local/bin/
COPY scripts/allowlist-amdgpu.txt /work/allowlist-amdgpu.txt
COPY scripts/allowlist-spirv.txt /work/allowlist-spirv.txt
RUN chmod +x /usr/local/bin/build-llvm-sancov.sh

ARG SANCOV_ALLOWLIST=amdgpu
RUN case "${SANCOV_ALLOWLIST}" in \
        amdgpu) allowlist=/work/allowlist-amdgpu.txt ;; \
        spirv) allowlist=/work/allowlist-spirv.txt ;; \
        *) echo "error: unsupported SANCOV_ALLOWLIST: ${SANCOV_ALLOWLIST} (expected amdgpu or spirv)" >&2; exit 1 ;; \
    esac \
 && echo "${SANCOV_ALLOWLIST}" > /work/.sancov-allowlist \
 && echo "=== fuzz-fill: SanitizerCoverage allowlist = ${SANCOV_ALLOWLIST} ===" \
 && /usr/local/bin/build-llvm-sancov.sh \
        "${allowlist}" \
        /work/llvm-project \
        /work/llvm-build-uninstrumented \
        /work/llvm-build-sancov

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

# Preserve exact paths from the builder stage (required by lit.site.cfg.py).
COPY --chown=${UID}:${GID} --from=llvm-builder /work/.llvm-source /work/.llvm-source
COPY --chown=${UID}:${GID} --from=llvm-builder /work/.sancov-allowlist /work/.sancov-allowlist
COPY --chown=${UID}:${GID} --from=llvm-builder /work/llvm-project /work/llvm-project
COPY --chown=${UID}:${GID} --from=llvm-builder /work/llvm-build-uninstrumented /work/llvm-build-uninstrumented
COPY --chown=${UID}:${GID} --from=llvm-builder /work/llvm-build-sancov /work/llvm-build-sancov

COPY --chown=${UID}:${GID} pyproject.toml LICENCE.txt README.md /work/fuzz-fill/
COPY --chown=${UID}:${GID} src /work/fuzz-fill/src
COPY --chown=${UID}:${GID} tests /work/fuzz-fill/tests
COPY --chown=${UID}:${GID} integration-tests /work/fuzz-fill/integration-tests

RUN echo "=== fuzz-fill image LLVM source: $(cat /work/.llvm-source) ===" \
 && echo "=== fuzz-fill image SanitizerCoverage allowlist: $(cat /work/.sancov-allowlist) ==="

USER "${UID}"
WORKDIR /work/fuzz-fill
RUN python3 -m venv /work/fuzz-fill-venv && \
    /work/fuzz-fill-venv/bin/pip install --no-cache-dir -e /work/fuzz-fill && \
    echo 'source /work/fuzz-fill-venv/bin/activate' >> ~/.bashrc

# Keep the venv outside /work/fuzz-fill so --bind-repo mounts do not hide it.
ENV VIRTUAL_ENV=/work/fuzz-fill-venv \
    PATH="/work/fuzz-fill-venv/bin:${PATH}" \
    PYTHON="/work/fuzz-fill-venv/bin/python"
