set clk [lindex [all_clocks] 0]
puts "Clock: [get_name $clk]"
puts "Period: [get_property $clk period]"
puts "Properties:"
foreach p [list_property $clk] {
    puts "  $p"
}
exit
