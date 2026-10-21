source physical/asap7/baseline/timing_common.tcl
read_lef $platform/lef/asap7_tech_1x_201209.lef
read_lef $platform/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog physical/asap7/baseline/report_audit.v
link_design report_audit
create_clock -name core_clk -period 5500 [get_ports clk]
set_input_transition 20 [all_inputs]
set_input_delay -max 1100 -clock core_clk [all_inputs -no_clocks]
set_input_delay -min 0 -clock core_clk [all_inputs -no_clocks]
set_output_delay -max 1100 -clock core_clk [all_outputs]
set_output_delay -min 0 -clock core_clk [all_outputs]
set_load 2 [all_outputs]
initialize_floorplan -site asap7sc7p5t -die_area {0 0 10 10} -core_area {1 1 9 9}
source $platform/openRoad/make_tracks.tcl
source $platform/setRC.tcl
place_pins -hor_layers M4 -ver_layers M5
global_placement -density 0.55
detailed_placement
check_placement -verbose
write_db $::env(RV32_AUDIT_DIR)/unrouted.odb
set_routing_layers -signal M2-M7 -clock M2-M7
set_global_routing_random -seed 1
global_route -congestion_iterations 10
estimate_parasitics -global_routing
write_db $::env(RV32_AUDIT_DIR)/routed.odb
write_guides $::env(RV32_AUDIT_DIR)/route.guide
