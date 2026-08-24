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

# Pre-synthesis elaborated AST statistics
stat

# Process elaboration and lowering to registers/muxes
proc_clean
proc_rmdead
proc_init
proc_arst
proc_mux
opt_expr
opt_clean
proc_dff
proc_clean

# Logic optimization and constant propagation
opt -fast

# Verify no multi-drivers, combinational loops, or unelaborated latches
check -assert

# Clean design
clean

# --- Process-Lowered Generic Cell Count (before full optimization passes) ---
stat

# --- Full synthesis pass: technology-independent mapping without ABC ---
# synth -top <top> -noabc performs full synthesis transforms (flatten, coarse,
# fine, memory, logic optimization) into primitive generic gates/DFFs without ABC library mapping.
synth -top rv32_ooo_core -noabc

# --- Post-Synth Generic Cell Count (after synth -noabc) ---
stat

# Write synthesized gate-level netlist (post synth -noabc)
write_verilog -noattr build/syn/rv32_ooo_core_netlist.v
EOF

yosys -l "${OUT_DIR}/synth.log" "${OUT_DIR}/synth.ys"

python3 scripts/parse_synth_log.py "${OUT_DIR}/synth.log" -o "${OUT_DIR}/synthesis_summary.json"

PROC_LOWERED=$(python3 -c "import json; d=json.load(open('${OUT_DIR}/synthesis_summary.json')); print(d.get('process_lowered_cells','N/A'))")
POST_SYNTH=$(python3 -c "import json; d=json.load(open('${OUT_DIR}/synthesis_summary.json')); print(d.get('post_synth_cells','N/A'))")

echo "============================================================"
echo "  [SUCCESS] Yosys Synthesis Signoff Completed!"
echo "  Netlist : ${OUT_DIR}/rv32_ooo_core_netlist.v"
echo "  Log     : ${OUT_DIR}/synth.log"
echo "  Summary : ${OUT_DIR}/synthesis_summary.json"
echo "------------------------------------------------------------"
echo "  Cell Count Summary:"
echo "    Process-Lowered Generic Cells (opt -fast) : ${PROC_LOWERED}"
echo "    Post-Synthesis Generic Cells (synth -noabc): ${POST_SYNTH}"
echo "============================================================"
