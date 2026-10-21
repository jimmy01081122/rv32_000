#!/usr/bin/env bash
# Shared simulator build entry point for Make and clean-SHA signoff.
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"
build_jobs=${1:-${JOBS:-$(nproc)}}

sim_build_dir=${SIM_BUILD_DIR:-build/sim}
assert_flags=()
if [[ ${SIM_ASSERTIONS:-0} == 1 ]]; then assert_flags+=(--assert); fi
mkdir -p "$sim_build_dir"
verilator --cc --exe --trace "${assert_flags[@]}" \
  -Wall -Wno-UNUSED -Wno-STMTDLY \
  -f sim/scripts/rv32_ooo_core.f \
  "$project_root/sim/tb/sim_main.cpp" "$project_root/sim/tb/sim_mem.cpp" \
  --top-module rv32_ooo_core \
  --Mdir "$sim_build_dir" -o rv32_ooo_sim \
  -CFLAGS "-I$project_root/sim/tb -O2"
make -C "$sim_build_dir" -f Vrv32_ooo_core.mk -j "$build_jobs"
