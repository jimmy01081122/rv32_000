#!/usr/bin/env bash
# compile_tests.sh — Cross-compile directed test programs (bare-metal)
# Requires: riscv32-unknown-elf-gcc in PATH (via Docker)
# Run from /workspace (repo root)

set -euo pipefail

OUT_DIR="build/tests"
CC="riscv32-unknown-elf-gcc"
OBJCOPY="riscv32-unknown-elf-objcopy"
OBJDUMP="riscv32-unknown-elf-objdump"
CFLAGS="-march=rv32imf_zicsr -mabi=ilp32 -O2 -nostartfiles -nostdlib -Isoftware/include"
LD_SCRIPT="software/linker/link.ld"

mkdir -p "${OUT_DIR}"

# Collect all .c test sources
SOURCES=()
if [ -d "software/directed" ]; then
  while IFS= read -r -d $'\0' f; do
    SOURCES+=("$f")
  done < <(find software/directed -name "*.c" -print0)
fi
if [ -d "verif/directed" ]; then
  while IFS= read -r -d $'\0' f; do
    SOURCES+=("$f")
  done < <(find verif/directed -name "*.c" -print0)
fi

if [ ${#SOURCES[@]} -eq 0 ]; then
  echo "INFO: No C tests found."
  exit 0
fi

echo "=== Compiling Bare-Metal Tests ==="
for src in "${SOURCES[@]}"; do
  name=$(basename "${src}" .c)
  echo "  [CC]  ${src} -> ${OUT_DIR}/${name}.elf"
  ${CC} ${CFLAGS} -T "${LD_SCRIPT}" \
    software/crt0/crt0.S "${src}" \
    -o "${OUT_DIR}/${name}.elf"
  ${OBJCOPY} -O binary "${OUT_DIR}/${name}.elf" "${OUT_DIR}/${name}.bin"
  ${OBJDUMP} -d "${OUT_DIR}/${name}.elf" > "${OUT_DIR}/${name}.dis"
  echo "  [OK]  ${OUT_DIR}/${name}.elf, .bin, .dis generated"
done

echo "=== Compilation Complete ==="
