###############################################################################
# Created by write_sdc
# Sun Oct 18 14:49:45 2026
###############################################################################
current_design report_audit
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core_clk -period 5500.0000 [get_ports {clk}]
set_clock_uncertainty -setup 50.0000 core_clk
set_clock_uncertainty -hold 25.0000 core_clk
set_propagated_clock [get_clocks {core_clk}]
set_input_delay 0.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {A}]
set_input_delay 1100.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {A}]
set_input_delay 0.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {B}]
set_input_delay 1100.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {B}]
set_input_delay 0.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {CI}]
set_input_delay 1100.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {CI}]
set_output_delay 0.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {FCON}]
set_output_delay 1100.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {FCON}]
set_output_delay 0.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {HCON}]
set_output_delay 1100.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {HCON}]
set_output_delay 0.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {HSN}]
set_output_delay 1100.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {HSN}]
set_output_delay 0.0000 -clock [get_clocks {core_clk}] -min -add_delay [get_ports {Q}]
set_output_delay 1100.0000 -clock [get_clocks {core_clk}] -max -add_delay [get_ports {Q}]
group_path -name reg2reg\
    -from [list [get_cells {ff0}]\
           [get_cells {ff1}]]\
    -to [list [get_cells {ff0}]\
           [get_cells {ff1}]]
group_path -name reg2out\
    -from [list [get_cells {ff0}]\
           [get_cells {ff1}]]\
    -to [list [get_ports {FCON}]\
           [get_ports {HCON}]\
           [get_ports {HSN}]\
           [get_ports {Q}]]
group_path -name in2reg\
    -from [list [get_ports {A}]\
           [get_ports {B}]\
           [get_ports {CI}]]\
    -to [list [get_cells {ff0}]\
           [get_cells {ff1}]]
group_path -name in2out\
    -from [list [get_ports {A}]\
           [get_ports {B}]\
           [get_ports {CI}]]\
    -to [list [get_ports {FCON}]\
           [get_ports {HCON}]\
           [get_ports {HSN}]\
           [get_ports {Q}]]
###############################################################################
# Environment
###############################################################################
set_load -pin_load 2.0000 [get_ports {FCON}]
set_load -pin_load 2.0000 [get_ports {HCON}]
set_load -pin_load 2.0000 [get_ports {HSN}]
set_load -pin_load 2.0000 [get_ports {Q}]
set_input_transition 20.0000 [get_ports {A}]
set_input_transition 20.0000 [get_ports {B}]
set_input_transition 20.0000 [get_ports {CI}]
set_input_transition 20.0000 [get_ports {clk}]
###############################################################################
# Design Rules
###############################################################################
