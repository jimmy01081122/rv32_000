# FP workload toolchain: keep the G1 simulator and Spike, add a matching
# rv32imf_zicsr/ilp32f multilib instead of replacing the historical compiler.
ARG SIM_BASE_IMAGE=rv32ooo-sim:g1
FROM ${SIM_BASE_IMAGE}

ARG RISCV_FP_RELEASE=v15.2.0-1
ARG RISCV_FP_SHA256=aaaa8060c914851a3e5ee1ba82cc3d6f80972f90638a05c6e823a37557a33758

LABEL description="rv32ooo FP qualification: xPack GCC 15.2.0-1, newlib 4.5.0"
LABEL riscv_fp.version="${RISCV_FP_RELEASE}"

RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export CURL_CA_BUNDLE=/run/secrets/proxy_ca; fi; \
    curl --fail --location --retry 3 \
      "https://github.com/xpack-dev-tools/riscv-none-elf-gcc-xpack/releases/download/${RISCV_FP_RELEASE}/xpack-riscv-none-elf-gcc-15.2.0-1-linux-x64.tar.gz" \
      -o /tmp/riscv-fp.tar.gz \
    && printf '%s  %s\n' "${RISCV_FP_SHA256}" /tmp/riscv-fp.tar.gz | sha256sum -c - \
    && mkdir -p /opt/riscv-fp \
    && tar -xzf /tmp/riscv-fp.tar.gz --strip-components=1 -C /opt/riscv-fp \
    && rm /tmp/riscv-fp.tar.gz

ENV PATH="/opt/riscv-fp/bin:${PATH}"

RUN test "$(riscv-none-elf-gcc -march=rv32imf_zicsr -mabi=ilp32f -print-multi-directory)" \
      = "rv32imf_zicsr/ilp32f" \
    && test -f "$(riscv-none-elf-gcc -march=rv32imf_zicsr -mabi=ilp32f -print-file-name=libm.a)" \
    && riscv-none-elf-gcc --version
