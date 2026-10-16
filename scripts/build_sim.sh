#!/usr/bin/env bash
# Shared simulator build entry point for Make and clean-SHA signoff.
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"
build_jobs=${1:-${JOBS:-$(nproc)}}

mkdir -p build/sim
verilator --cc --exe --trace \
  -Wall -Wno-UNUSED -Wno-STMTDLY \
  -f sim/scripts/rv32_ooo_core.f \
  "$project_root/sim/tb/sim_main.cpp" "$project_root/sim/tb/sim_mem.cpp" \
  --top-module rv32_ooo_core \
  --Mdir build/sim -o rv32_ooo_sim \
  -CFLAGS "-I$project_root/sim/tb -O2"
make -C build/sim -f Vrv32_ooo_core.mk -j "$build_jobs"
