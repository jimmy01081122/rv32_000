# ============================================================================
# RV32 OoO Core — Fast Robust Flat ASAP7 Synthesis Script for ORFS
# ============================================================================

source $::env(SCRIPTS_DIR)/synth_preamble.tcl

read_design_sources

hierarchy -top $::env(DESIGN_NAME)
flatten

# 1. Fast process lowering
proc_clean
proc_rmdead
proc_init
proc_arst
proc_mux
opt_expr
opt_clean
proc_dff
proc_clean

# 2. Eliminate any formal verification / process artifacts
chformal -remove
delete t:\$process
delete t:\$mem*

# 3. Technology mapping to bit-level gate primitives
techmap
opt_expr
opt_clean
clean

# 4. Technology mapping of sequential elements (DFF) to ASAP7 SEQ library
dfflibmap -liberty $::env(PLATFORM_DIR)/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib {*}$lib_dont_use_args
opt_expr
opt_clean
clean

# 5. Constant initialization
setundef -zero

# 6. ABC technology mapping into ASAP7 standard cell library
log_cmd abc {*}$abc_args

# 7. Split compound wire assignments and clean unused wires/cells
splitnets
opt_clean -purge
clean

# 8. Tie hi/lo cell insertion
hilomap -singleton \
  -hicell {*}$::env(TIEHI_CELL_AND_PORT) \
  -locell {*}$::env(TIELO_CELL_AND_PORT)

# 9. Reports
tee -o $::env(REPORTS_DIR)/synth_stat.txt stat {*}$lib_args

# 10. Write synthesized Verilog netlist for OpenROAD
write_verilog -noattr -nohex -nodec $::env(RESULTS_DIR)/1_2_yosys.v
