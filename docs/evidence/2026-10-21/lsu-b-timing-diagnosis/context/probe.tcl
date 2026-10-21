# Read-only diagnostics. The frozen independent-corner constraints are retained.
# Zero-wire/ideal-clock synthesis mode is separately labelled, never qualified.
source /workspace/physical/asap7/baseline/timing_common.tcl
read_db $::env(RV32_ODB)
set view $::env(RV32_VIEW)
if {$view eq "routed"} {
  if {![grt::have_routes]} {error "missing original global routes"}
  source $platform/setRC.tcl
  estimate_parasitics -global_routing
} elseif {$view ne "synthesis"} {error "invalid diagnostic view"}
set directory $::env(RV32_OUT)
file mkdir $directory
create_clock -name core_clk -period 10000 [get_ports clk]
set_clock_uncertainty -setup 50 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_transition 20 [all_inputs]
set_input_delay -max 1100 -clock core_clk [all_inputs -no_clocks]
set_input_delay -min 0 -clock core_clk [all_inputs -no_clocks]
set_output_delay -max 1100 -clock core_clk [all_outputs]
set_output_delay -min 0 -clock core_clk [all_outputs]
set_load 2 [all_outputs]
if {$view eq "routed"} {set_propagated_clock [all_clocks]}
group_path -name in2reg -from [all_inputs -no_clocks] -to [all_registers]
group_path -name reg2out -from [all_registers] -to [all_outputs]
group_path -name reg2reg -from [all_registers] -to [all_registers]
group_path -name in2out -from [all_inputs -no_clocks] -to [all_outputs]
save_report $directory/units.rpt {report_units}
save_report $directory/check_setup.rpt {check_setup -verbose}
save_report $directory/reg2reg_max.rpt {
  report_checks -path_delay max -path_group reg2reg -group_path_count 5 -format full_clock_expanded -fields {input_pin net fanout capacitance slew} -digits 6 -no_line_splits
}
save_report $directory/in2reg_min.rpt {
  report_checks -path_delay min -path_group in2reg -group_path_count 10 -format full_clock_expanded -fields {input_pin net fanout capacitance slew} -digits 6 -no_line_splits
}
set fp_pins {}
foreach pin [get_pins -hierarchical -quiet *cmp_data*] {
  set name [get_full_name $pin]
  if {[string first "u_fp_execute.cmp_data" $name] == 0 && [string match */D $name]} {lappend fp_pins $pin}
}
if {[llength $fp_pins] < 32} {error "FP completion endpoints not found"}
save_report $directory/fp_max.rpt {
  report_checks -to $fp_pins -path_delay max -path_group reg2reg -group_path_count 5 -format full_clock_expanded -fields {input_pin net fanout capacitance slew} -digits 6 -no_line_splits
}
foreach bit {115 124 125} {
  set needle [format {u_fp_execute.cmp_data[%d]$_SDFFE_PP0P_/D} $bit]
  set selected {}
  foreach pin $fp_pins {if {[get_full_name $pin] eq $needle} {lappend selected $pin}}
  if {[llength $selected] != 1} {error "missing common FP endpoint: $needle"}
  save_report $directory/fp_sink_${bit}_max.rpt {
    report_checks -to $selected -path_delay max -path_group reg2reg -group_path_count 1 -format full_clock_expanded -fields {input_pin net fanout capacitance slew} -digits 6 -no_line_splits
  }
}
set lsu_tracking {}
foreach pin [get_pins -hierarchical -quiet *in_flight_is_store*] {
  if {[string match */D [get_full_name $pin]]} {lappend lsu_tracking $pin}
}
if {[llength $lsu_tracking] != 1} {error "missing store tracking D pin"}
save_report $directory/ready_to_tracking_min.rpt {
  report_checks -from [get_ports dmem_req_ready] -to $lsu_tracking -path_delay min -group_path_count 1 -format full_clock_expanded -fields {input_pin net fanout capacitance slew} -digits 6 -no_line_splits
}
save_report $directory/hold_violating_endpoints.rpt {
  report_checks -path_delay min -slack_max 0 -group_path_count 100000 -unique_paths_to_endpoint -format end -digits 6
}
set failures [find_timing_paths -path_delay min -slack_max 0 -group_path_count 100000 -unique_paths_to_endpoint]
set file [open $directory/metrics.json w]
puts $file [format {{"diagnostic_only":true,"view":"%s","corner":"%s","period_ps":10000,"setup_slack_ps":%.12f,"hold_slack_ps":%.12f,"reported_hold_violating_endpoints":%d,"fp_completion_d_pins":%d}} $view $suffix [sta::worst_slack -max] [sta::worst_slack -min] [llength $failures] [llength $fp_pins]]
close $file
puts "RV32_READ_ONLY_DIAGNOSTIC_COMPLETE"
