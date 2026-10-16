#!/usr/bin/env bash
# Yosys 0.9 needs sv2v to lower packages, structs and enums first.
set -euo pipefail
mkdir -p build/smoke
mapfile -t rtl_files < sim/scripts/rv32_ooo_core.f
sv2v --top=rv32_ooo_core -I rtl/pkg "${rtl_files[@]}" > build/smoke/rv32_ooo_core.v
yosys -Q -T -p 'read_verilog build/smoke/rv32_ooo_core.v; hierarchy -check -top rv32_ooo_core; stat'
echo 'YOSYS hierarchy: PASS'
