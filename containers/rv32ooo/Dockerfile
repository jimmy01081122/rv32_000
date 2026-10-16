# ============================================================================
# rv32ooo-sim — G1 Simulation + Verification Container
# Base: ubuntu:22.04
#
# Pinned tool versions (see toolchain.lock):
#   verilator   : 4.038-1     (Ubuntu 22.04 LTS native package)
#   riscv32-gcc : 2026.07.15  (riscv-collab/riscv-gnu-toolchain)
#   spike       : v1.1.0      (riscv-software-src/riscv-isa-sim)
#   python      : 3.10        (Ubuntu 22.04 system)
# ============================================================================

# ── Stage 1: build Spike from source ─────────────────────────────────────────
FROM ubuntu:22.04 AS spike_builder

ARG DEBIAN_FRONTEND=noninteractive
ARG SPIKE_TAG=v1.1.0
ARG NJOBS=12

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates \
    build-essential \
    device-tree-compiler libboost-regex-dev libboost-system-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build/spike
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export GIT_SSL_CAINFO=/run/secrets/proxy_ca; fi; \
    git clone --depth 1 --branch ${SPIKE_TAG} \
        https://github.com/riscv-software-src/riscv-isa-sim.git . \
    && mkdir build && cd build \
    && ../configure --prefix=/opt/spike --enable-commitlog \
    && make -j${NJOBS} \
    && make install

# Runtime needs the simulator, not its static libraries, headers or auxiliary tools.
RUN strip --strip-debug /opt/spike/bin/spike

# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG RISCV_GCC_RELEASE=2026.07.15

LABEL maintainer="rv32ooo-project"
LABEL description="rv32ooo sim/verif: Verilator 4.038, RISC-V GCC 2026.07.15, Spike v1.1.0"
LABEL verilator.version="4.038-1"
LABEL riscv_gcc.version="${RISCV_GCC_RELEASE}"
LABEL spike.version="v1.1.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates curl xz-utils file \
    make \
    build-essential \
    verilator=4.038* \
    libgmp10 libmpfr6 libmpc3 \
    libfl2 libreadline8 zlib1g \
    libboost-regex1.74.0 \
    device-tree-compiler \
    python3 \
    time \
    && rm -rf /var/lib/apt/lists/*

COPY --from=spike_builder /opt/spike/bin/spike /opt/spike/bin/spike

# ── RISC-V GCC pre-built elf/newlib toolchain (rv32) ────────────────────────
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export CURL_CA_BUNDLE=/run/secrets/proxy_ca; fi; \
    curl --fail --location --retry 3 \
    "https://github.com/riscv-collab/riscv-gnu-toolchain/releases/download/${RISCV_GCC_RELEASE}/riscv32-elf-ubuntu-22.04-gcc.tar.xz" \
    -o /tmp/riscv32-gcc.tar.xz \
    && mkdir -p /opt/riscv32-gcc \
    && tar -xf /tmp/riscv32-gcc.tar.xz -C /opt/riscv32-gcc --strip-components=1 \
    && rm /tmp/riscv32-gcc.tar.xz \
    && find /opt/riscv32-gcc/bin /opt/riscv32-gcc/libexec -type f \
       -exec sh -c 'for binary do if file -b "$binary" | grep -q "ELF .*x86-64"; then strip --strip-debug "$binary"; fi; done' sh {} + \
    && /opt/riscv32-gcc/bin/riscv32-unknown-elf-gcc --version

ENV PATH="/opt/spike/bin:/opt/riscv32-gcc/bin:${PATH}"
ENV RISCV="/opt/riscv32-gcc"

WORKDIR /workspace

# ── Smoke-test all tools ──────────────────────────────────────────────────────
RUN echo "=== rv32ooo-sim toolchain ===" \
    && verilator --version \
    && (spike -h 2>&1 | head -n 2 || true) \
    && riscv32-unknown-elf-gcc --version \
    && python3 --version \
    && echo "=== G1 verification OK ==="

ENTRYPOINT ["/bin/bash"]
CMD ["-l"]
