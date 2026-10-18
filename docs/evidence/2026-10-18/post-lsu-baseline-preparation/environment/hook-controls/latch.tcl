yosys -import
read_verilog build/baseline-setup/hook-controls/latch.v
hierarchy -top bad
source physical/asap7/baseline/lower_processes.tcl
