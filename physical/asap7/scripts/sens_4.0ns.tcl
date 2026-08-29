
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_db /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/6_final.odb
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -global_routing

create_clock -name core_clk -period 4000.0 -waveform [list 0 [expr 4000.0 / 2.0]] [get_ports clk]
set_clock_uncertainty -setup 50.0 [get_clocks core_clk]
set_clock_uncertainty -hold 25.0 [get_clocks core_clk]
set_input_transition 20.0 [get_ports clk]
set_propagated_clock [all_clocks]

set non_clock_inputs [all_inputs -no_clocks]
set all_outputs_list [all_outputs]
set_input_delay [expr 0.2 * 4000.0] -clock core_clk $non_clock_inputs
set_output_delay [expr 0.2 * 4000.0] -clock core_clk $all_outputs_list

puts "=== REPORTING PATH _387041_ -> _388327_ FOR T = 4.0 ns ==="
report_checks -from [get_pins _387041_/CLK] -to [get_pins _388327_/D] -path_delay max -format full_clock_expanded
exit
