source [file join [file dirname [info script]] timing_common.tcl]
read_lef $platform/lef/asap7_tech_1x_201209.lef
read_lef $platform/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog [file join [file dirname [info script]] adder_audit.v]
link_design adder_audit
create_clock -name clk -period 5500 [get_ports clk]
set_input_transition 20 [all_inputs]
set_input_delay 0 -clock clk [all_inputs -no_clocks]
set_output_delay 0 -clock clk [all_outputs]
set_load 2 [all_outputs]
set directory $::env(RV32_REPORT_DIR)
file mkdir $directory
save_report $directory/units.rpt {report_units}
foreach input {A B CI} {
  foreach output {FCON FSN HCON HSN} {
    if {$input eq "CI" && [string match H* $output]} { continue }
    save_report $directory/${input}_${output}.rpt {report_checks -from [get_ports $input] -to [get_ports $output] -path_delay min_max -group_path_count 2}
  }
}
exit
