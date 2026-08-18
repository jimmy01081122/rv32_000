#!/usr/bin/env bash
# scripts/compile_coremark.sh — Compile Official EEMBC CoreMark for RV32 OoO Core
set -e

ITER=${1:-10}
RUN_TYPE=${2:-PERFORMANCE_RUN} # PERFORMANCE_RUN or VALIDATION_RUN
OPT_FLAGS=${3:--O2}

TOOLCHAIN_PREFIX="riscv32-unknown-elf-"
CC="${TOOLCHAIN_PREFIX}gcc"
OBJCOPY="${TOOLCHAIN_PREFIX}objcopy"
OBJDUMP="${TOOLCHAIN_PREFIX}objdump"

BUILD_DIR="build/coremark"
mkdir -p "${BUILD_DIR}"

OUTPUT_ELF="${BUILD_DIR}/coremark_iter${ITER}.elf"
OUTPUT_BIN="${BUILD_DIR}/coremark_iter${ITER}.bin"
OUTPUT_DIS="${BUILD_DIR}/coremark_iter${ITER}.dis"

CFLAGS="-march=rv32im_zicsr -mabi=ilp32 ${OPT_FLAGS} -ffreestanding -nostartfiles -nostdlib -Wall -Wextra"
CFLAGS+=" -Isoftware/coremark/eembc -Isoftware/coremark/rv32_port -Isoftware/include"
CFLAGS+=" -DITERATIONS=${ITER} -D${RUN_TYPE}=1 -DMULTITHREAD=1 -DUSE_CLOCK=0 -DHAS_FLOAT=0"
CFLAGS+=" -DFLAGS_STR=\"\\\"${OPT_FLAGS}\\\"\""

SRCS=(
  software/crt0/crt0.S
  software/coremark/rv32_port/core_portme.c
  software/coremark/eembc/core_list_join.c
  software/coremark/eembc/core_main.c
  software/coremark/eembc/core_matrix.c
  software/coremark/eembc/core_state.c
  software/coremark/eembc/core_util.c
)

echo "=== Compiling CoreMark (${RUN_TYPE}, ${ITER} iterations, ${OPT_FLAGS}) ==="
${CC} ${CFLAGS} -T software/linker/link.ld "${SRCS[@]}" -o "${OUTPUT_ELF}" -lgcc
${OBJCOPY} -O binary "${OUTPUT_ELF}" "${OUTPUT_BIN}"
${OBJDUMP} -d "${OUTPUT_ELF}" > "${OUTPUT_DIS}"

echo "  [OK] ${OUTPUT_ELF} generated ($(stat -c%s "${OUTPUT_BIN}") bytes)"
