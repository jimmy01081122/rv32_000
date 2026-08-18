# ============================================================================
# rv32ooo-sim — G1 Simulation + Verification Container
# Base: ubuntu:22.04
#
# Pinned tool versions (see toolchain.lock):
#   verilator   : 4.038-1     (Ubuntu 22.04 LTS native package)
#   yosys       : 0.9-2       (Ubuntu 22.04 LTS native package)
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
    device-tree-compiler libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build/spike
RUN git clone --depth 1 --branch ${SPIKE_TAG} \
        https://github.com/riscv-software-src/riscv-isa-sim.git . \
    && mkdir build && cd build \
    && ../configure --prefix=/opt/spike \
    && make -j${NJOBS} \
    && make install

# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG RISCV_GCC_RELEASE=2026.07.15

LABEL maintainer="rv32ooo-project"
LABEL description="rv32ooo sim/verif: Verilator 4.038, Yosys 0.9, RISC-V GCC 2026.07.15, Spike v1.1.0"
LABEL verilator.version="4.038-1"
LABEL yosys.version="0.9-2"
LABEL riscv_gcc.version="${RISCV_GCC_RELEASE}"
LABEL spike.version="v1.1.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates wget curl xz-utils file \
    make cmake \
    build-essential \
    verilator=4.038* \
    yosys=0.9* \
    libgmp10 libmpfr6 libmpc3 \
    libfl2 libreadline8 libtcl8.6 libffi7 zlib1g \
    libboost-all-dev \
    device-tree-compiler \
    python3 python3-pip python3-venv \
    time less tree unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sL https://github.com/zachjs/sv2v/releases/download/v0.0.12/sv2v-Linux.zip -o /tmp/sv2v.zip \
    && unzip -q /tmp/sv2v.zip -d /tmp/ \
    && mv /tmp/sv2v-Linux/sv2v /usr/local/bin/sv2v \
    && chmod +x /usr/local/bin/sv2v \
    && rm -rf /tmp/sv2v*

COPY --from=spike_builder /opt/spike /opt/spike

# ── RISC-V GCC pre-built elf/newlib toolchain (rv32) ────────────────────────
RUN wget -q \
    "https://github.com/riscv-collab/riscv-gnu-toolchain/releases/download/${RISCV_GCC_RELEASE}/riscv32-elf-ubuntu-22.04-gcc.tar.xz" \
    -O /tmp/riscv32-gcc.tar.xz \
    && mkdir -p /opt/riscv32-gcc \
    && tar -xf /tmp/riscv32-gcc.tar.xz -C /opt/riscv32-gcc --strip-components=1 \
    && rm /tmp/riscv32-gcc.tar.xz \
    && /opt/riscv32-gcc/bin/riscv32-unknown-elf-gcc --version

# ── Python packages ───────────────────────────────────────────────────────────
RUN pip3 install --no-cache-dir \
    pyelftools==0.31 \
    pyyaml==6.0.2 \
    tabulate==0.9.0 \
    rich==13.9.4

ENV PATH="/opt/spike/bin:/opt/riscv32-gcc/bin:${PATH}"
ENV RISCV="/opt/riscv32-gcc"

WORKDIR /workspace

# ── Smoke-test all tools ──────────────────────────────────────────────────────
RUN echo "=== rv32ooo-sim toolchain ===" \
    && verilator --version \
    && yosys -V \
    && (spike -h 2>&1 | head -n 2 || true) \
    && riscv32-unknown-elf-gcc --version \
    && python3 -c "import elftools; print('elftools OK')" \
    && echo "=== G1 verification OK ==="

ENTRYPOINT ["/bin/bash"]
CMD ["-l"]
