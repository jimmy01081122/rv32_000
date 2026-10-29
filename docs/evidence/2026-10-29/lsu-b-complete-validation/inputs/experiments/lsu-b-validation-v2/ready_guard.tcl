# Uniform noninverting input delay guard, after the separately qualified hold40 construction.
utl::set_metrics_stage "readyguard__{}"
source $::env(SCRIPTS_DIR)/load.tcl
erase_non_stage_variables grt
load_design 5_0_grt_input.odb 5_0_grt_input.sdc
source $::env(PLATFORM_DIR)/fastroute.tcl
if {![grt::have_routes]} { error "guard input lacks global routes" }
set_global_routing_random -seed $::env(GRT_SEED)
set_propagated_clock [all_clocks]
set_placement_padding -global -left $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT) -right $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT)
set block [ord::get_db_block]
proc pin_net {pin} {
  set net [$pin getNet]
  if {$net eq "NULL"} { return "" }
  return [$net getName]
}
proc pins_of {inst} {
  set result [dict create]
  foreach pin [$inst getITerms] { dict set result [[$pin getMTerm] getName] [pin_net $pin] }
  return $result
}
set before [dict create]
set original_pins 0
foreach inst [$block getInsts] {
  set pins [pins_of $inst]
  dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
  incr original_pins [dict size $pins]
}
set ports [dict create]
foreach port [$block getBTerms] { dict set ports [$port getName] [list [$port getIoType] [pin_net $port]] }
set ready [$block findBTerm dmem_req_ready]
if {$ready eq "NULL" || [$ready getIoType] ne "INPUT"} { error "missing ready input" }
set old_net [$ready getNet]
set old_name [$old_net getName]
if {[llength [$old_net getBTerms]] != 1} { error "ready input has unexpected other boundary terminals" }
set loads [$old_net getITerms]
if {![llength $loads]} { error "ready input has no loads" }
foreach load $loads { if {[[$load getMTerm] getIoType] ne "INPUT"} { error "ready net has a non-input load" } }
if {[$block findInst rv32_ready_hold_guard] ne "NULL" || [$block findNet rv32_ready_hold_guard_net] ne "NULL"} { error "guard name already exists" }
lassign [[[lindex $loads 0] getInst] getLocation] x y
set dbu [$block getDbUnitsPerMicron]
set location [list [expr {double($x)/$dbu}] [expr {double($y)/$dbu}]]
global_route -start_incremental
insert_buffer -buffer_cell BUFx2_ASAP7_75t_R -net $old_name -location $location -buffer_name rv32_ready_hold_guard -net_name rv32_ready_hold_guard_net
# The native -buffer_name is a prefix, not a literal instance name.
set additions {}
foreach inst [$block getInsts] {
  if {![dict exists $before [$inst getName]]} { lappend additions $inst }
}
if {[llength $additions] != 1} { error "insertion did not add exactly one cell" }
set inserted [lindex $additions 0]
set guard_name [$inserted getName]
if {[[$inserted getMaster] getName] ne "BUFx2_ASAP7_75t_R" || ![regexp {^rv32_ready_hold_guard[0-9]*$} $guard_name]} { error "unexpected inserted cell" }
puts "RV32_GUARD_INSERTED name=$guard_name master=[[$inserted getMaster] getName]"
detailed_placement
check_placement -verbose
global_route -end_incremental -congestion_iterations 30 -verbose
puts "RV32_GUARD_FULL_ROUTE_BEGIN"
global_route -congestion_iterations 30 -verbose
estimate_parasitics -global_routing
if {![grt::have_routes]} { error "guard lost global routes" }
puts "RV32_GUARD_FULL_ROUTE_COMPLETE"
check_antennas -report_file $::env(REPORTS_DIR)/ready_guard_antennas.rpt
# All original cell masters, every pin and all boundary terminals must survive.
# Removing this one proven wire buffer must recover exactly the original graph.
set guard [$block findInst $guard_name]
if {$guard eq "NULL" || [[$guard getMaster] getName] ne "BUFx2_ASAP7_75t_R"} { error "wrong guard cell" }
if {[llength [$block getInsts]] != [dict size $before]+1} { error "unexpected cell addition/removal" }
set a [pin_net [$guard findITerm A]]
set y [pin_net [$guard findITerm Y]]
if {$a eq $y || [pin_net $ready] ne $a} { error "guard direction/connection mismatch" }
set checked_pins 0
set changed_loads 0
dict for {name value} $before {
  lassign $value master pins
  set inst [$block findInst $name]
  if {$inst eq "NULL" || [[$inst getMaster] getName] ne $master} { error "original cell changed: $name" }
  set after [pins_of $inst]
  if {[lsort [dict keys $after]] ne [lsort [dict keys $pins]]} { error "pin set changed: $name" }
  dict for {pin net} $pins {
    set wanted $net
    if {$net eq $old_name} { set wanted $y; incr changed_loads }
    if {[dict get $after $pin] ne $wanted} { error "original pin changed: $name/$pin" }
    incr checked_pins
  }
}
if {[llength [$block getBTerms]] != [dict size $ports]} { error "boundary port count changed" }
dict for {name value} $ports {
  lassign $value direction net
  set port [$block findBTerm $name]
  if {$name eq "dmem_req_ready"} { set net $a }
  if {$port eq "NULL" || [$port getIoType] ne $direction || [pin_net $port] ne $net} { error "boundary terminal changed: $name" }
}
if {$checked_pins != $original_pins || $changed_loads != [llength $loads]} { error "incomplete connectivity audit" }
set audit [open $::env(REPORTS_DIR)/ready_guard_connectivity.json w]
puts $audit "\{\"passed\":true,\"original_cells\":[dict size $before],\"final_cells\":[llength [$block getInsts]],\"original_pins_checked\":$checked_pins,\"boundary_ports_checked\":[dict size $ports],\"redirected_input_loads\":$changed_loads,\"added_buffer\":\"$guard_name\",\"master\":\"BUFx2_ASAP7_75t_R\",\"all_other_cells_masters_pins_ports_unchanged\":true\}"
close $audit
puts "RV32_GUARD_CONNECTIVITY_PASS cells=[dict size $before] pins=$checked_pins ports=[dict size $ports]"
write_guides $::env(RESULTS_DIR)/route.guide
orfs_write_db $::env(RESULTS_DIR)/5_1_grt.odb
orfs_write_sdc $::env(RESULTS_DIR)/5_1_grt.sdc
puts "RV32_GUARD_COMPLETE"
