# ============================================================================
# rv32ooo-syn — G1 Synthesis + Physical Design Container
# Base: ubuntu:22.04
#
# Pinned tool versions (see toolchain.lock):
#   yosys       : 0.9-2   (Ubuntu 22.04 LTS native package)
#   python      : 3.10    (Ubuntu 22.04 system)
# ============================================================================

FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

LABEL maintainer="rv32ooo-project"
LABEL description="rv32ooo synthesis: Yosys 0.9 + STA / PPA tools"
LABEL yosys.version="0.9-2"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates wget curl unzip \
    build-essential make cmake \
    yosys=0.9* \
    tcl-dev libffi-dev libboost-all-dev \
    libfl2 libreadline8 zlib1g \
    libeigen3-dev libgomp1 \
    python3 python3-pip python3-venv \
    time tree less \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sL https://github.com/zachjs/sv2v/releases/download/v0.0.12/sv2v-Linux.zip -o /tmp/sv2v.zip \
    && unzip -q /tmp/sv2v.zip -d /tmp/ \
    && mv /tmp/sv2v-Linux/sv2v /usr/local/bin/sv2v \
    && chmod +x /usr/local/bin/sv2v \
    && rm -rf /tmp/sv2v*

RUN pip3 install --no-cache-dir \
    pyyaml==6.0.2 \
    tabulate==0.9.0 \
    rich==13.9.4

WORKDIR /workspace

RUN echo "=== rv32ooo-syn toolchain ===" \
    && yosys -V \
    && echo "=== G1 synthesis container OK ==="

ENTRYPOINT ["/bin/bash"]
CMD ["-l"]
