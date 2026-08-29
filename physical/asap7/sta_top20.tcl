read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_db /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/6_final.odb
read_sdc /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/5_route.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -global_routing

puts "=== TOP 20 UNIQUE SETUP PATHS ==="
report_checks -path_delay max -unique_paths_to_endpoint -endpoint_count 20 -format full_clock_expanded > /OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base/top20_setup_unique.rpt

puts "=== TOP 20 UNIQUE REG2REG SETUP PATHS ==="
report_checks -path_delay max -from [all_registers] -to [all_registers] -unique_paths_to_endpoint -endpoint_count 20 -format full_clock_expanded > /OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base/top20_setup_reg2reg.rpt

puts "=== TOP 20 UNIQUE HOLD PATHS ==="
report_checks -path_delay min -unique_paths_to_endpoint -endpoint_count 20 -format full_clock_expanded > /OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base/top20_hold_unique.rpt

puts "=== TOP 20 UNIQUE REG2REG HOLD PATHS ==="
report_checks -path_delay min -from [all_registers] -to [all_registers] -unique_paths_to_endpoint -endpoint_count 20 -format full_clock_expanded > /OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base/top20_hold_reg2reg.rpt

exit
