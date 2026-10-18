# Conservative TT-only post-route repair; acceptance still uses independent
# unrelaxed TT/SS/FF constraints. Incoming files remain immutable.
utl::set_metrics_stage "postrouteeco__{}"
source $::env(SCRIPTS_DIR)/load.tcl
erase_non_stage_variables grt
load_design 5_0_grt_input.odb 5_0_grt_input.sdc
source $::env(PLATFORM_DIR)/fastroute.tcl
if {![grt::have_routes]} { error "ECO input has no restorable global routes" }
set_global_routing_random -seed $::env(GRT_SEED)
set_propagated_clock [all_clocks]
if {[env_var_exists_and_non_empty DONT_USE_CELLS]} {
  set_dont_use $::env(DONT_USE_CELLS)
}
set_placement_padding -global \
  -left $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT) \
  -right $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT)
estimate_parasitics -global_routing

# Track modified nets from before resizing; retain the existing route solution.
global_route -start_incremental
repair_design_helper
detailed_placement
check_placement -verbose
global_route -end_incremental -congestion_iterations 30 -verbose
estimate_parasitics -global_routing

global_route -start_incremental
repair_timing_helper
detailed_placement
check_placement -verbose
global_route -end_incremental -congestion_iterations 30 -verbose
estimate_parasitics -global_routing
if {![grt::have_routes]} { error "ECO lost global routes" }
write_guides $::env(RESULTS_DIR)/route.guide
orfs_write_db $::env(RESULTS_DIR)/5_1_grt.odb
orfs_write_sdc $::env(RESULTS_DIR)/5_1_grt.sdc
puts "RV32_GRT_ECO_COMPLETE"
