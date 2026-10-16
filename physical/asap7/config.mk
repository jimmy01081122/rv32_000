# ============================================================================
# RV32 OoO Core — ASAP7 Physical Implementation Config (ORFS)
# Existing research configuration; source and results must be pinned per run.
# Checked-in SDC is 5.5 ns under the ASAP7 ps-unit convention.
# This is an exploration constraint, not a qualified frequency target.
# See README.md for path portability, routing-stage and corner limitations.
# ============================================================================

export PLATFORM               = asap7
export DESIGN_NICKNAME        = rv32_ooo
export DESIGN_NAME            = rv32_ooo_core

# Pre-lowered clean Verilog source (100% registerized arrays, 0 processes)
export VERILOG_FILES = $(DESIGN_HOME)/src/rv32_ooo/rv32_ooo_core_lowered.v

export SDC_FILE = $(DESIGN_HOME)/asap7/rv32_ooo/constraint.sdc

# Fast robust ASAP7 synthesis script for RV32 OoO Core
export SYNTH_SCRIPT = $(DESIGN_HOME)/asap7/rv32_ooo/synth_asap7.tcl

# --------------------------------------------------------------------------
# Floorplan — Conservative AP0 utilization for routability
# Spec: 50-60% core utilization, 0.55-0.65 placement density
# --------------------------------------------------------------------------
export CORE_UTILIZATION       = 50
export CORE_ASPECT_RATIO      = 1
export CORE_MARGIN            = 2.0

# Conservative density: OoO CPU has large mux trees, wakeup/select logic,
# PRF read muxes, store forwarding — all create routing pressure
export PLACE_DENSITY          = 0.55

# --------------------------------------------------------------------------
# Timing
# --------------------------------------------------------------------------
export TNS_END_PERCENT        = 100

# --------------------------------------------------------------------------
# Routing — OoO design has complex inter-module data paths
# --------------------------------------------------------------------------
export ROUTING_LAYER_ADJUSTMENT = 0.25

# --------------------------------------------------------------------------
# Library Model
# --------------------------------------------------------------------------
export LIB_MODEL              = NLDM

# Random seed for reproducibility
# Fast exploration settings
export SKIP_REPORT_METRICS    = 0
export REMOVE_ABC_BUFFERS     = 1
export GPL_TIMING_DRIVEN      = 0
export GPL_ROUTING_DRIVEN     = 0
export SKIP_CTS_REPAIR_TIMING = 1
export SKIP_INCREMENTAL_REPAIR = 1
export SKIP_DETAILED_ROUTE    = 1
