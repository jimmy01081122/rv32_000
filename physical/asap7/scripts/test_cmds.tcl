puts "=== CLOCK INFO ==="
foreach clk [all_clocks] {
    puts "Clock: [get_name $clk]"
    puts "  Period: [get_property $clk period]"
    puts "  Waveform: [get_property $clk waveform]"
    puts "  Sources: [get_name [get_property $clk sources]]"
}

puts "=== UNCONSTRAINED CHECK ==="
check_timing -verbose

puts "=== REPORT CHECKS UNCONSTRAINED ==="
report_checks -unconstrained

puts "=== CHECK PIN/PORT CONSTRAINTS ==="
set unconstrained_endpoints [all_registers -data_pins]
puts "Total Data Pins: [llength $unconstrained_endpoints]"

puts "=== DONE TEST ==="
exit
