# Independent-corner analysis of a saved global-route database.
source [file join [file dirname [info script]] timing_common.tcl]
read_db $::env(RV32_ODB)
if {![grt::have_routes]} { error "database has no restorable global routes" }
source $platform/setRC.tcl
estimate_parasitics -global_routing
set directory $::env(RV32_REPORT_DIR)
file mkdir $directory
save_report $directory/units.rpt {report_units}
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set standard_area 0.0
set standard_cells 0
set macros 0
set unsafe_cells 0
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  if {[$master getName] in {FAx1_ASAP7_75t_R HAxp5_ASAP7_75t_R}} { incr unsafe_cells }
  if {[string match CORE* [$master getType]]} {
    set standard_area [expr {$standard_area + double([$master getWidth])*[$master getHeight]/$dbu/$dbu}]
    incr standard_cells
  } elseif {[$master isBlock]} { incr macros }
}
if {$unsafe_cells && (![info exists ::env(RV32_ADDER_AUDIT_VERIFIED)] || $::env(RV32_ADDER_AUDIT_VERIFIED) ne "1")} {
  error "adder output-port warning interpretation needs the independent functional/STA audit"
}
set metrics [open $directory/clock_trials.json w]
set registers [llength [all_registers]]
puts $metrics "\{\"corner\":\"$suffix\",\"global_routes_restored\":true,\"library_warning_cell_instances\":$unsafe_cells,\"standard_cell_area_um2\":$standard_area,\"standard_cell_count\":$standard_cells,\"register_count\":$registers,\"macro_count\":$macros,\"trials\":\["
set first 1
set periods {2500 3000 3500 4000 4500 5000 5500 6000 7000 8000 10000 12000 14000 16000 20000}
if {[info exists ::env(RV32_PERIODS_PS)]} { set periods $::env(RV32_PERIODS_PS) }
foreach period $periods {
  if {![string is integer -strict $period] || $period <= 2200} { error "invalid clock trial" }
  create_clock -name core_clk -period $period [get_ports clk]
  set_clock_uncertainty -setup 50 [all_clocks]
  set_clock_uncertainty -hold 25 [all_clocks]
  set_input_transition 20 [all_inputs]
  set_input_delay -max 1100 -clock core_clk [all_inputs -no_clocks]
  set_input_delay -min 0 -clock core_clk [all_inputs -no_clocks]
  set_output_delay -max 1100 -clock core_clk [all_outputs]
  set_output_delay -min 0 -clock core_clk [all_outputs]
  set_load 2 [all_outputs]
  set_propagated_clock [all_clocks]
  group_path -name in2reg -from [all_inputs -no_clocks] -to [all_registers]
  group_path -name reg2out -from [all_registers] -to [all_outputs]
  group_path -name reg2reg -from [all_registers] -to [all_registers]
  group_path -name in2out -from [all_inputs -no_clocks] -to [all_outputs]
  if {[llength [all_clocks]] != 1} { error "expected exactly one core clock" }
  write_sdc $directory/constraints_${period}.sdc
  save_report $directory/check_setup_${period}.rpt {check_setup -verbose}
  save_report $directory/setup_${period}.rpt {report_worst_slack -max}
  save_report $directory/hold_${period}.rpt {report_worst_slack -min}
  save_report $directory/setup_paths_${period}.rpt {report_checks -path_delay max -group_path_count 5 -format full_clock_expanded}
  save_report $directory/hold_paths_${period}.rpt {report_checks -path_delay min -group_path_count 5 -format full_clock_expanded}
  save_report $directory/electrical_${period}.rpt {report_check_types -max_slew -max_capacitance -min_pulse_width -min_period -violators}
  set setup [sta::worst_slack -max]
  set hold [sta::worst_slack -min]
  if {!$first} { puts $metrics , }
  set first 0
  puts -nonewline $metrics "\{\"period_ps\":$period,\"setup_slack_ps\":$setup,\"hold_slack_ps\":$hold\}"
}
puts $metrics "\]\}"
close $metrics
