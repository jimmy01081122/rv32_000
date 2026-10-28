# Use the pinned ORFS algorithm, retaining checkpoints at the ABC boundary.
# These observations do not alter ABC arguments or the selected design.
yosys -import
rename abc rv32_native_abc
proc rv32_save_fp {name} {
  # -module itself rejects a missing boundary; -assert-count would count
  # every wire and cell inside the module, not the module name.
  select -module rv32_ooo_fp_execute
  write_rtlil -selected $::env(RESULTS_DIR)/$name
  write_json -selected $::env(RESULTS_DIR)/$name.json
  select -clear
}
proc abc {args} {
  rv32_save_fp fp_pre_abc.rtlil
  rv32_native_abc {*}$args
  rv32_save_fp fp_post_abc.rtlil
}
source $::env(SCRIPTS_DIR)/synth.tcl
rv32_save_fp fp_mapped.rtlil
