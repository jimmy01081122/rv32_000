#!/usr/bin/env bash
# syn/scripts/synth_yosys.sh — Yosys Synthesis Signoff Flow (Milestone G15)
# Converts SystemVerilog RTL via sv2v to Verilog-2005 and runs full Yosys synthesis.

set -euo pipefail

OUT_DIR="build/syn"
mkdir -p "${OUT_DIR}"

RTL_FILES=(
  rtl/pkg/rv32_ooo_params.sv
  rtl/pkg/rv32_ooo_types.sv
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

echo "============================================================"
echo "    RV32 Out-of-Order Core — Synthesis Flow (Yosys)        "
echo "============================================================"

echo "==> Step 1: Converting SystemVerilog to Verilog-2005 via sv2v..."
sv2v --top=rv32_ooo_core \
  --write="${OUT_DIR}/rv32_ooo_core.v2k.v" \
  -I rtl/pkg \
  "${RTL_FILES[@]}"

echo "  [OK] Generated ${OUT_DIR}/rv32_ooo_core.v2k.v ($(wc -l < "${OUT_DIR}/rv32_ooo_core.v2k.v") lines)"

echo "==> Step 2: Running Yosys Elaboration & Synthesis..."
cat << 'EOF' > "${OUT_DIR}/synth.ys"
# Read lowered Verilog-2005 RTL
read_verilog build/syn/rv32_ooo_core.v2k.v

# Elaborate hierarchy
hierarchy -check -top rv32_ooo_core

# Process compilation (converts processes to DFFs and combinational logic)
proc

# Check for combinational loops, latches, and missing drivers
check -assert

# Perform generic logic synthesis
synth -top rv32_ooo_core -noabc

# Clean up redundant logic
opt -fast
clean

# Print cell count and area statistics
stat

# Write synthesized gate-level netlist
write_verilog -noattr build/syn/rv32_ooo_core_netlist.v
EOF

yosys -s "${OUT_DIR}/synth.ys" | tee "${OUT_DIR}/synth.log"

echo "============================================================"
echo "  [SUCCESS] Yosys Synthesis Signoff Completed!"
echo "  Netlist : ${OUT_DIR}/rv32_ooo_core_netlist.v"
echo "  Log     : ${OUT_DIR}/synth.log"
echo "============================================================"
