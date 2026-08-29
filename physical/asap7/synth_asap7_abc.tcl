# ============================================================================
# RV32 OoO Core — ASAP7 ABC-only Gate Mapping Script for ORFS
#
# Strategy: Read pre-synthesized RTLIL checkpoint (produced by host Yosys 0.9)
# that has already completed: proc -> flatten -> memory -> techmap.
# Only dfflibmap + abc + cleanup remain.
# ============================================================================

source $::env(SCRIPTS_DIR)/synth_preamble.tcl

# Read the RTLIL checkpoint produced by host Yosys 0.9
# (fully proc-lowered, flattened, memory-mapped, techmap-expanded)
read_rtlil $::env(RESULTS_DIR)/1_1_yosys_canonicalize.rtlil

hierarchy -top $::env(DESIGN_NAME)

# Quick cleanup (design is already fully lowered)
opt_expr
opt_clean
clean

# Map sequential elements (DFF) to ASAP7 library cells
if { [env_var_exists_and_non_empty DFF_LIB_FILE] } {
  dfflibmap -liberty $::env(DFF_LIB_FILE) {*}$lib_dont_use_args
} else {
  dfflibmap {*}$lib_args {*}$lib_dont_use_args
}
opt_expr
opt_clean
clean

# Replace undef with defined constants
setundef -zero

# ABC technology mapping to ASAP7 standard cells
log_cmd abc {*}$abc_args

# Post-ABC cleanup
splitnets
opt_clean -purge
clean

# Tie hi/lo driver insertion
hilomap -singleton \
  -hicell {*}$::env(TIEHI_CELL_AND_PORT) \
  -locell {*}$::env(TIELO_CELL_AND_PORT)

# Reports
tee -o $::env(REPORTS_DIR)/synth_stat.txt stat {*}$lib_args

# Write ASAP7 gate-level netlist
write_verilog -noattr -nohex -nodec $::env(RESULTS_DIR)/1_2_yosys.v
