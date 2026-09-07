read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_db /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/1_synth.odb
read_sdc /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/1_synth.sdc

set rpt_dir "/OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base"

puts "Reporting WNS and TNS..."
report_wns
report_tns

puts "Generating synth_timing_reg2reg.rpt (top 50 endpoints)..."
report_checks -path_delay max -from [all_registers] -to [all_registers] -endpoint_count 50 -format full_clock_expanded > "$rpt_dir/synth_timing_reg2reg.rpt"

puts "Done!"
exit
