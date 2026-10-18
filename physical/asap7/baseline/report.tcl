proc save_report {filename script} {
  sta::redirect_file_begin $filename
  set code [catch {uplevel 1 $script} result options]
  sta::redirect_file_end
  return -options $options $result
}
# Inspect the same global-route database at explicitly tested clock periods.
set platform /OpenROAD-flow-scripts/flow/platforms/asap7
set suffix $::env(RV32_CORNER)
if {$suffix ni {TT SS FF}} { error "RV32_CORNER must be TT, SS or FF" }
# Each corner is analyzed in a fresh OpenSTA process. Cross-corner XOR arcs in
# this PDK do not all match a shared reference timing graph (STA-1111).
# Match the five libraries selected by the pinned platform config exactly.
# A glob also selects experimental FAKE DFF views and a second FF SIMPLE lib.
foreach template {
  asap7sc7p5t_AO_RVT_%s_nldm_211120.lib.gz
  asap7sc7p5t_INVBUF_RVT_%s_nldm_220122.lib.gz
  asap7sc7p5t_OA_RVT_%s_nldm_211120.lib.gz
  asap7sc7p5t_SIMPLE_RVT_%s_nldm_211120.lib.gz
  asap7sc7p5t_SEQ_RVT_%s_nldm_220123.lib
} {
  set file $platform/lib/NLDM/[format $template $suffix]
  read_liberty $file
}
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
if {$unsafe_cells} { error "database uses $unsafe_cells cells with STA-1212 library warnings" }
set metrics [open $directory/clock_trials.json w]
puts $metrics "\{\"corner\":\"$suffix\",\"global_routes_restored\":true,\"library_warning_cell_instances\":$unsafe_cells,\"standard_cell_area_um2\":$standard_area,\"standard_cell_count\":$standard_cells,\"macro_count\":$macros,\"trials\":\["
set first 1
foreach period {5500 6000 7000 8000 10000 12000 14000 16000 20000} {
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
  save_report $directory/check_setup_${period}.rpt {check_setup -verbose}
  save_report $directory/setup_${period}.rpt {report_worst_slack -max}
  save_report $directory/hold_${period}.rpt {report_worst_slack -min}
  save_report $directory/setup_paths_${period}.rpt {report_checks -path_delay max -group_path_count 5 -format full_clock_expanded}
  save_report $directory/hold_paths_${period}.rpt {report_checks -path_delay min -group_path_count 5 -format full_clock_expanded}
  save_report $directory/electrical_${period}.rpt {report_check_types -max_slew -max_capacitance -violators}
  set setup [sta::worst_slack -max]
  set hold [sta::worst_slack -min]
  if {!$first} { puts $metrics , }
  set first 0
  puts -nonewline $metrics "\{\"period_ps\":$period,\"setup_slack_library_units\":$setup,\"hold_slack_library_units\":$hold\}"
}
puts $metrics "\]\}"
close $metrics
