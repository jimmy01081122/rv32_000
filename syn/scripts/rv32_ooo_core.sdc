# rv32_ooo_core.sdc — Synopsys Design Constraints for rv32_ooo_core
# Target frequency: 100 MHz (10.0 ns period)

set_units -time ns -resistance kOhm -capacitance pF -voltage V -current mA

# 1. Primary Clock Definition
create_clock -name clk -period 10.0 [get_ports clk]
set_clock_uncertainty 0.2 [get_clocks clk]
set_clock_transition 0.15 [get_clocks clk]

# 2. Input Delays (assuming 20% budget for external memory/interface)
set_input_delay -clock clk 2.0 [get_ports rst]
set_input_delay -clock clk 2.0 [get_ports imem_rdata*]
set_input_delay -clock clk 2.0 [get_ports imem_resp_valid]
set_input_delay -clock clk 2.0 [get_ports dmem_rdata*]
set_input_delay -clock clk 2.0 [get_ports dmem_resp_valid]
set_input_delay -clock clk 2.0 [get_ports dmem_busy]
set_input_delay -clock clk 2.0 [get_ports ext_irq]

# 3. Output Delays (assuming 20% budget for external memory/interface)
set_output_delay -clock clk 2.0 [get_ports imem_req_valid]
set_output_delay -clock clk 2.0 [get_ports imem_req_addr*]
set_output_delay -clock clk 2.0 [get_ports dmem_req_valid]
set_output_delay -clock clk 2.0 [get_ports dmem_req_op*]
set_output_delay -clock clk 2.0 [get_ports dmem_req_addr*]
set_output_delay -clock clk 2.0 [get_ports dmem_req_wdata*]
set_output_delay -clock clk 2.0 [get_ports dmem_req_wmask*]
set_output_delay -clock clk 2.0 [get_ports commit_trace*]
