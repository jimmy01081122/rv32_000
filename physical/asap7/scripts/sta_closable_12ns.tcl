read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_db /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/6_final.odb
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -global_routing

# Target period: 13.0 ns (13000 ps = 76.92 MHz) to close timing with positive slack
set period_ps 13000.0
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

set rpt_dir "/OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base"

puts "=================== TIMING SUMMARY AT T = 13.0 ns ==================="
puts "Setup WNS:  [sta::worst_slack -max]"
puts "Setup TNS:  [sta::total_negative_slack -max]"
puts "Hold Slack: [sta::worst_slack -min]"

puts "=================== POWER AT 13.0 ns (OPERATING POWER) ==================="
report_power > "$rpt_dir/power_closable_13ns.rpt"
report_power

puts "=================== TOP 20 PATHS PER GROUP ==================="
report_checks -path_delay max -from [all_registers] -to [all_registers] -endpoint_count 20 -format full_clock_expanded > "$rpt_dir/closable_timing_reg2reg.rpt"
report_checks -path_delay max -from $non_clock_inputs -to [all_registers] -endpoint_count 20 -format full_clock_expanded > "$rpt_dir/closable_timing_in2reg.rpt"
report_checks -path_delay max -from [all_registers] -to $all_outputs_list -endpoint_count 20 -format full_clock_expanded > "$rpt_dir/closable_timing_reg2out.rpt"
report_checks -path_delay max -from $non_clock_inputs -to $all_outputs_list -endpoint_count 20 -format full_clock_expanded > "$rpt_dir/closable_timing_in2out.rpt"

report_checks -path_delay min -from [all_registers] -to [all_registers] -endpoint_count 20 -format full_clock_expanded > "$rpt_dir/closable_hold_reg2reg.rpt"

puts "STA analysis complete."
exit
