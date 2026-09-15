read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_db /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/6_final.odb
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -global_routing

set period_ps 12000.0
create_clock -name core_clk -period $period_ps -waveform [list 0 [expr $period_ps / 2.0]] [get_ports clk]
set_clock_uncertainty -setup 50.0 [get_clocks core_clk]
set_clock_uncertainty -hold 25.0 [get_clocks core_clk]
set_input_transition 20.0 [get_ports clk]
set_propagated_clock [all_clocks]

set non_clock_inputs [all_inputs -no_clocks]
set all_outputs_list [all_outputs]
set_input_delay [expr 0.20 * $period_ps] -clock core_clk $non_clock_inputs
set_input_transition 20.0 $non_clock_inputs
set_output_delay [expr 0.20 * $period_ps] -clock core_clk $all_outputs_list
set_load 2.0 $all_outputs_list

group_path -name in2reg  -from $non_clock_inputs -to [all_registers]
group_path -name reg2out -from [all_registers]   -to $all_outputs_list
group_path -name reg2reg -from [all_registers]   -to [all_registers]
group_path -name in2out  -from $non_clock_inputs -to $all_outputs_list

# AP4F: Clean hold timing closure
repair_timing -hold -verbose
estimate_parasitics -global_routing

set rpt_dir "/OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base"

puts "=================== TIMING SUMMARY AT T = 12.0 ns ==================="
puts "Overall Setup WNS:  [sta::worst_slack -max]"
puts "Overall Setup TNS:  [sta::total_negative_slack -max]"
puts "Overall Hold Slack: [sta::worst_slack -min]"

puts "=================== POWER AT 12.0 ns (OPERATING POWER) ==================="
report_power > "$rpt_dir/power_closable_12ns.rpt"
report_power

puts "=================== PATH GROUP SLACKS ==================="
report_checks -group_path_count 10 -endpoint_path_count 1

puts "=================== TOP 50 REG2REG PATHS (50 DISTINCT ENDPOINTS) ==================="
report_checks -path_group reg2reg -path_delay max -endpoint_path_count 1 -group_path_count 50 -format full_clock_expanded > "$rpt_dir/closable_timing_reg2reg.rpt"
report_checks -path_group reg2reg -path_delay max -endpoint_path_count 1 -group_path_count 50 -format summary > "$rpt_dir/reg2reg_summary.rpt"
report_checks -path_group reg2reg -path_delay max -endpoint_path_count 1 -group_path_count 5 -format full_clock_expanded

puts "=================== TOP 10 IN2REG PATHS ==================="
report_checks -path_group in2reg -path_delay max -endpoint_path_count 1 -group_path_count 10 -format full_clock_expanded > "$rpt_dir/closable_timing_in2reg.rpt"

puts "=================== TOP 10 REG2OUT PATHS ==================="
report_checks -path_group reg2out -path_delay max -endpoint_path_count 1 -group_path_count 10 -format full_clock_expanded > "$rpt_dir/closable_timing_reg2out.rpt"

puts "=================== TOP 10 IN2OUT PATHS ==================="
report_checks -path_group in2out -path_delay max -endpoint_path_count 1 -group_path_count 10 -format full_clock_expanded > "$rpt_dir/closable_timing_in2out.rpt"

puts "=================== TOP 10 HOLD REG2REG PATHS ==================="
report_checks -path_group reg2reg -path_delay min -endpoint_path_count 1 -group_path_count 10 -format full_clock_expanded > "$rpt_dir/closable_hold_reg2reg.rpt"

puts "STA signoff complete."
exit
