read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_db /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/6_final.odb
read_sdc /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/5_route.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -global_routing

puts "========================================================"
puts "                SDC & TIMING AUDIT                      "
puts "========================================================"

puts "--- Clocks ---"
report_clocks

puts "--- Clock Uncertainty ---"
report_clock_properties

puts "--- Check Timing Setup ---"
check_timing -verbose

puts "--- Check Constraints ---"
report_checks -unconstrained

puts "--- Constrained vs Unconstrained Endpoints ---"
set total_endpoints [llength [all_registers]]
puts "Total register endpoints: $total_endpoints"

puts "========================================================"
exit
