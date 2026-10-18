# AP5B post-LSU v1 research flow. Paths are explicit; all outputs are ignored.
export PLATFORM = asap7
export DESIGN_NICKNAME = rv32_post_lsu_v1
export DESIGN_NAME = rv32_ooo_core
export VERILOG_FILES = $(RV32_ROOT)/build/baseline-setup/rtl_lowered.v
export SDC_FILE = $(RV32_SDC)
export SYNTH_CANONICALIZE_TCL = $(RV32_ROOT)/physical/asap7/baseline/lower_processes.tcl
export CORE_UTILIZATION = 50
export CORE_ASPECT_RATIO = 1
export CORE_MARGIN = 2.0
export PLACE_DENSITY = 0.55
export GPL_RANDOM_SEED = 1
export GRT_SEED = 1
export LIB_MODEL = NLDM
export ASAP7_USE_VT = RVT
# Yosys maps at TT; OpenROAD evaluates TT/SS/FF on the same routed netlist.
export CORNER = TC
export CORNERS = typical slow fast
export TYPICAL_LIB_FILES = $(TC_NLDM_LIB_FILES)
export SLOW_LIB_FILES = $(WC_NLDM_LIB_FILES)
export FAST_LIB_FILES = $(BC_NLDM_LIB_FILES)
export SKIP_DETAILED_ROUTE = 1
