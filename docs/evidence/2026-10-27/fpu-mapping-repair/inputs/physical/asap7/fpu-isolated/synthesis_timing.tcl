# Diagnostic only: no routes, wire capacitance or propagated clock tree.
source /workspace/physical/asap7/baseline/timing_common.tcl
read_db $::env(RV32_ODB)
if {[grt::have_routes]} {error "expected an unplaced synthesis database"}
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
group_path -name in2reg -from [all_inputs -no_clocks] -to [all_registers]
group_path -name reg2out -from [all_registers] -to [all_outputs]
group_path -name reg2reg -from [all_registers] -to [all_registers]
group_path -name in2out -from [all_inputs -no_clocks] -to [all_outputs]
set fp_pins {}
set sink115 {}
foreach pin [get_pins -hierarchical -quiet *cmp_data*] {
  set name [get_full_name $pin]
  if {[regexp {^u_fp_execute[/\.]cmp_data.*\/D$} $name]} {
    lappend fp_pins $pin
    if {[string first {cmp_data[115]} $name] >= 0} {lappend sink115 $pin}
  }
}
if {[llength $fp_pins] != 100 || [llength $sink115] != 1} {
  error "unexpected FPU completion endpoint count: [llength $fp_pins] / [llength $sink115]"
}
save_report $directory/units.rpt {report_units}
save_report $directory/check_setup.rpt {check_setup -verbose}
save_report $directory/fp_max.rpt {
  report_checks -to $fp_pins -path_delay max -path_group reg2reg -group_path_count 5 -format full_clock_expanded -fields {input_pin net fanout capacitance slew} -digits 6 -no_line_splits
}
save_report $directory/fp_sink_115_max.rpt {
  report_checks -to $sink115 -path_delay max -path_group reg2reg -group_path_count 1 -format full_clock_expanded -fields {input_pin net fanout capacitance slew} -digits 6 -no_line_splits
}
set f [open $directory/metrics.json w]
puts $f [format {{"diagnostic_only":true,"corner":"%s","period_ps":10000,"fp_completion_d_pins":%d,"setup_slack_ps":%.12f,"hold_slack_ps":%.12f}} $suffix [llength $fp_pins] [sta::worst_slack -max] [sta::worst_slack -min]]
close $f
puts "RV32_FPU_SYNTHESIS_DIAGNOSTIC_COMPLETE"
