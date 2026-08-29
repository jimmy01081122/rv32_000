# RV32 OoO Core — ASAP7 Timing Constraints
set sdc_version 2.0
set clk_name core_clk
set clk_port_name clk
set clk_period 12000.0

set clk_port [get_ports $clk_port_name]
create_clock -name $clk_name -period $clk_period -waveform [list 0 [expr $clk_period / 2.0]] $clk_port

set_clock_uncertainty -setup 50.0 [get_clocks $clk_name]
set_clock_uncertainty -hold  25.0 [get_clocks $clk_name]
set_input_transition 20.0 $clk_port

set non_clock_inputs [all_inputs -no_clocks]
set all_outputs_list [all_outputs]

set_input_delay [expr 0.20 * $clk_period] -clock $clk_name $non_clock_inputs
set_input_transition 20.0 $non_clock_inputs
set_output_delay [expr 0.20 * $clk_period] -clock $clk_name $all_outputs_list
set_load 2.0 $all_outputs_list

group_path -name in2reg  -from $non_clock_inputs -to [all_registers]
group_path -name reg2out -from [all_registers]   -to $all_outputs_list
group_path -name reg2reg -from [all_registers]   -to [all_registers]
group_path -name in2out  -from $non_clock_inputs -to $all_outputs_list
