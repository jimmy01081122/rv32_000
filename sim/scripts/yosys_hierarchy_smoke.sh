#!/usr/bin/env bash
# yosys_hierarchy_smoke.sh
# Yosys 0.9 hierarchy smoke-test for G1.1 acceptance.
#
# Yosys 0.9 cannot parse SystemVerilog packages with typedef/enum.
# Strategy: use Yosys with the -norestrict flag and read only the
# structural (non-package) modules.  The package types are synthesized
# out to bit vectors automatically when Yosys elaborates the hierarchy.
# Any structural error (missing module, unresolved port, bad hierarchy)
# will be caught by 'hierarchy -check'.
#
# Run from repo root: bash sim/scripts/yosys_hierarchy_smoke.sh

set -euo pipefail

MODULES=(
  rtl/rename/rv32_ooo_int_prf.sv
  rtl/rename/rv32_ooo_fp_prf.sv
  rtl/frontend/rv32_ooo_frontend.sv
  rtl/rename/rv32_ooo_rename.sv
  rtl/rob/rv32_ooo_rob.sv
  rtl/issue/rv32_ooo_int_iq.sv
  rtl/issue/rv32_ooo_fp_iq.sv
  rtl/execute/int/rv32_ooo_int_execute.sv
  rtl/execute/fp/rv32_ooo_fp_execute.sv
  rtl/lsu/rv32_ooo_lsu.sv
  rtl/csr/rv32_ooo_csr.sv
  rtl/core/rv32_ooo_core.sv
)

# Build read_verilog commands (packages first via -sv, then modules)
YOSYS_SCRIPT="
read_verilog -sv -norestrict rtl/pkg/rv32_ooo_params.sv;
read_verilog -sv -norestrict rtl/pkg/rv32_ooo_types.sv;
"
for f in "${MODULES[@]}"; do
  YOSYS_SCRIPT+="read_verilog -sv -norestrict ${f};"$'\n'
done
YOSYS_SCRIPT+="
hierarchy -check -top rv32_ooo_core;
stat;
"

echo "=== Yosys G1.1 hierarchy smoke ==="
yosys -q -p "$YOSYS_SCRIPT"
echo "YOSYS: PASS"
