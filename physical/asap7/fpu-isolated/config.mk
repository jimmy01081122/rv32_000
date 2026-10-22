# Experimental v2 synthesis boundary; never changes the frozen v1 config.
include $(RV32_ROOT)/physical/asap7/baseline/config.mk
export SYNTH_KEEP_MODULES = rv32_ooo_fp_execute
export SYNTH_SCRIPT = $(RV32_ROOT)/physical/asap7/fpu-isolated/synth.tcl
