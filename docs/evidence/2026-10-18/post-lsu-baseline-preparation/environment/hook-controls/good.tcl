yosys -import
read_verilog build/baseline-setup/hook-controls/good.v
hierarchy -top good
source physical/asap7/baseline/lower_processes.tcl
