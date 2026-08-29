# OpenSTA Analysis Script for AP0 Baseline
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_db /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/6_final.odb
read_sdc /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/5_route.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -global_routing

puts "=== DUMPING TOP 20 SETUP PATHS ==="
report_checks -path_delay max -format full_clock_expanded -endpoint_count 20 > /OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base/top20_setup.rpt

puts "=== DUMPING TOP 20 HOLD PATHS ==="
report_checks -path_delay min -format full_clock_expanded -endpoint_count 20 > /OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base/top20_hold.rpt

puts "=== CLOCK PERIOD SWEEP ==="
set periods {2000.0 1500.0 1250.0 1100.0 1000.0 900.0}
set sweep_out [open "/OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base/clock_sweep.rpt" "w"]
puts $sweep_out "period_ps,freq_mhz,wns_ps,tns_ps"

foreach p $periods {
    create_clock -name core_clk -period [expr $p / 1000.0] [get_ports clk]
    set_propagated_clock [all_clocks]
    set wns [sta::worst_slack -max]
    set tns [sta::total_negative_slack -max]
    set freq [expr 1000000.0 / $p]
    puts $sweep_out "$p,$freq,$wns,$tns"
    puts "Period: $p ps ($freq MHz) -> WNS: $wns ps, TNS: $tns ps"
}
close $sweep_out
puts "STA analysis complete."
exit
