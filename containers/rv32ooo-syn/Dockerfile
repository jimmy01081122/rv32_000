# ============================================================================
# rv32ooo-syn — Generic Synthesis Container (OpenROAD/PDK are separate)
# Base: ubuntu:22.04
#
# Pinned tool versions (see toolchain.lock):
#   yosys       : 0.9-2   (Ubuntu 22.04 LTS native package)
#   python      : 3.10    (Ubuntu 22.04 system)
# ============================================================================

FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

LABEL maintainer="rv32ooo-project"
LABEL description="rv32ooo generic synthesis: sv2v 0.0.12 + Yosys 0.9"
LABEL yosys.version="0.9-2"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip \
    yosys=0.9* \
    python3 \
    time \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export CURL_CA_BUNDLE=/run/secrets/proxy_ca; fi; \
    curl --fail --location --retry 3 https://github.com/zachjs/sv2v/releases/download/v0.0.12/sv2v-Linux.zip -o /tmp/sv2v.zip \
    && unzip -q /tmp/sv2v.zip -d /tmp/ \
    && mv /tmp/sv2v-Linux/sv2v /usr/local/bin/sv2v \
    && chmod +x /usr/local/bin/sv2v \
    && rm -rf /tmp/sv2v*

WORKDIR /workspace

RUN echo "=== rv32ooo-syn toolchain ===" \
    && yosys -V \
    && echo "=== G1 synthesis container OK ==="

ENTRYPOINT ["/bin/bash"]
CMD ["-l"]
