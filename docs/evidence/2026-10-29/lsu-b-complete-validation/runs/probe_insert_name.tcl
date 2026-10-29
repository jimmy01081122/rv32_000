source /workspace/physical/asap7/baseline/timing_common.tcl
read_db /workspace/build/experiments/lsu-b-validation-v2/physical-baseline-v2/eco/results/asap7/rv32_post_lsu_v1/base/5_1_grt.odb
read_sdc /workspace/build/experiments/lsu-b-validation-v2/physical-baseline-v2/eco/results/asap7/rv32_post_lsu_v1/base/5_1_grt.sdc
set block [ord::get_db_block]
set before [dict create]
foreach inst [$block getInsts] { dict set before [$inst getName] 1 }
set result [insert_buffer -buffer_cell BUFx2_ASAP7_75t_R -net dmem_req_ready -buffer_name rv32_ready_hold_guard -net_name rv32_ready_hold_guard_net]
puts "RV32_INSERT_RETURN=$result"
foreach inst [$block getInsts] {
 if {![dict exists $before [$inst getName]]} { puts "RV32_ADDED_CELL name=[$inst getName] master=[[$inst getMaster] getName]" }
}
exit
