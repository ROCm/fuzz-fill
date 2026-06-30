FROM ubuntu:24.04 AS llvm-builder

ARG DEBIAN_FRONTEND=noninteractive
# Parent commit before the first fuzz-fill contribution: https://github.com/llvm/llvm-project/pull/185430.
ARG LLVM_COMMIT=40cd48fd385b57855a104a4192c4d4468889d22d

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

RUN curl -fsSL "https://github.com/llvm/llvm-project/archive/${LLVM_COMMIT}.tar.gz" \
    | tar -xz -C /work \
 && mv "/work/llvm-project-${LLVM_COMMIT}" /work/llvm-project

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
RUN chmod +x /usr/local/bin/build-llvm-sancov.sh

RUN /usr/local/bin/build-llvm-sancov.sh \
    /work/allowlist-amdgpu.txt \
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
COPY --chown=${UID}:${GID} --from=llvm-builder /work/llvm-project /work/llvm-project
COPY --chown=${UID}:${GID} --from=llvm-builder /work/llvm-build-uninstrumented /work/llvm-build-uninstrumented
COPY --chown=${UID}:${GID} --from=llvm-builder /work/llvm-build-sancov /work/llvm-build-sancov

COPY --chown=${UID}:${GID} pyproject.toml LICENCE.txt README.md /work/fuzz-fill/
COPY --chown=${UID}:${GID} src /work/fuzz-fill/src
COPY --chown=${UID}:${GID} integration-tests /work/fuzz-fill/integration-tests

USER "${UID}"
WORKDIR /work/fuzz-fill
RUN python3 -m venv venv && \
    ./venv/bin/pip install --no-cache-dir -e . && \
    echo 'source /work/fuzz-fill/venv/bin/activate' >> ~/.bashrc

# Keep the venv active in every container (non-interactive and interactive).
ENV VIRTUAL_ENV=/work/fuzz-fill/venv \
    PATH="/work/fuzz-fill/venv/bin:${PATH}" \
    PYTHON="/work/fuzz-fill/venv/bin/python"
