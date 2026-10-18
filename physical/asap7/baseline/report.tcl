# Inspect the same global-route database at explicitly tested clock periods.
define_corners typical slow fast
set platform /OpenROAD-flow-scripts/flow/platforms/asap7
foreach corner {typical slow fast} suffix {TT SS FF} {
  foreach file [glob $platform/lib/NLDM/*_RVT_${suffix}_nldm_*.lib*] {
    read_liberty -corner $corner $file
  }
}
read_db $::env(RV32_ODB)
source $platform/setRC.tcl
estimate_parasitics -global_routing
set directory $::env(RV32_REPORT_DIR)
file mkdir $directory
report_units > $directory/units.rpt
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set standard_area 0.0
set standard_cells 0
set macros 0
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  if {[string match CORE* [$master getType]]} {
    set standard_area [expr {$standard_area + double([$master getWidth])*[$master getHeight]/$dbu/$dbu}]
    incr standard_cells
  } elseif {[$master isBlock]} { incr macros }
}
set metrics [open $directory/clock_trials.json w]
puts $metrics "\{\"standard_cell_area_um2\":$standard_area,\"standard_cell_count\":$standard_cells,\"macro_count\":$macros,\"trials\":\["
set first 1
foreach period {5500 6000 7000 8000 10000 12000 14000 16000 20000} {
  create_clock -name core_clk -period $period [get_ports clk]
  set_clock_uncertainty -setup 50 [all_clocks]
  set_clock_uncertainty -hold 25 [all_clocks]
  set_input_transition 20 [all_inputs]
  set_input_delay 1100 -clock core_clk [all_inputs -no_clocks]
  set_output_delay 1100 -clock core_clk [all_outputs]
  set_load 2 [all_outputs]
  set_propagated_clock [all_clocks]
  group_path -name in2reg -from [all_inputs -no_clocks] -to [all_registers]
  group_path -name reg2out -from [all_registers] -to [all_outputs]
  group_path -name reg2reg -from [all_registers] -to [all_registers]
  group_path -name in2out -from [all_inputs -no_clocks] -to [all_outputs]
  check_setup -verbose > $directory/check_setup_${period}.rpt
  report_worst_slack -max > $directory/setup_${period}.rpt
  report_worst_slack -min > $directory/hold_${period}.rpt
  report_checks -scenes [get_scenes slow] -path_delay max -group_path_count 5 -format full_clock_expanded > $directory/slow_paths_${period}.rpt
  report_checks -scenes [get_scenes fast] -path_delay min -group_path_count 5 -format full_clock_expanded > $directory/fast_paths_${period}.rpt
  report_check_types -max_slew -max_capacitance -violators > $directory/electrical_${period}.rpt
  set setup [sta::worst_slack -max]
  set hold [sta::worst_slack -min]
  if {!$first} { puts $metrics , }
  set first 0
  puts -nonewline $metrics "\{\"period_ps\":$period,\"setup_slack_library_units\":$setup,\"hold_slack_library_units\":$hold\}"
}
puts $metrics "\]\}"
close $metrics
