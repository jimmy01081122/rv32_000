read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_db /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/4_cts.odb
read_sdc /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/4_cts.sdc

set rpt_dir "/OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base"

puts "Dumping timing_summary.rpt..."
set sum_fp [open "$rpt_dir/timing_summary.rpt" "w"]
puts $sum_fp "Setup WNS:  [sta::worst_slack -max]"
puts $sum_fp "Setup TNS:  [sta::total_negative_slack -max]"
puts $sum_fp "Hold Slack: [sta::worst_slack -min]"
close $sum_fp

puts "Dumping timing_critical.rpt (critical path)..."
report_checks -path_delay max -format full_clock_expanded > "$rpt_dir/timing_critical.rpt"

puts "Done!"
exit
