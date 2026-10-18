source physical/asap7/baseline/report.tcl
foreach name {place18130/A _320642_/A1 {u_rob.next_seq[9]$_SDFFE_PP0P_/QN} {u_rob.next_seq[9]$_SDFFE_PP0P_/CLK}} {
  puts "PIN $name"
  sta::report_slews -digits 4 $name
  report_net -digits 4 $name
}
