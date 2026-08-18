// rv32_ooo_fp_prf.sv — Floating-Point Physical Register File (FP PRF)
// 48 entries × 32-bit FLEN, 4 asynchronous read ports with dedicated LSU bypass, 2 synchronous write ports
// architecture_spec.md §23.1, §6 | uop_spec.md §17

module rv32_ooo_fp_prf
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic clk,
  input  logic rst,            // synchronous active-high

  // Write port 0 (from FP execution cluster)
  input  logic            wr0_en,
  input  phys_reg_t       wr0_addr,
  input  logic [FLEN-1:0] wr0_data,

  // Write port 1 (from LSU load completion - FLW)
  input  logic            wr1_en,
  input  phys_reg_t       wr1_addr,
  input  logic [FLEN-1:0] wr1_data,

  // Dedicated LSU load bypass channel (purely from ld_cmp to break combinational loops)
  input  logic            lsu_bypass_en,
  input  phys_reg_t       lsu_bypass_addr,
  input  logic [FLEN-1:0] lsu_bypass_data,

  // Read port 0: FP IQ operand 0
  input  phys_reg_t       rd_addr_0,
  output logic [FLEN-1:0] rd_data_0,

  // Read port 1: FP IQ operand 1
  input  phys_reg_t       rd_addr_1,
  output logic [FLEN-1:0] rd_data_1,

  // Read port 2: FP IQ operand 2 (FMA third source)
  input  phys_reg_t       rd_addr_2,
  output logic [FLEN-1:0] rd_data_2,

  // Read port 3: SQ FP store-data capture (FSW, dedicated)
  input  phys_reg_t       rd_addr_sq,
  output logic [FLEN-1:0] rd_data_sq
);

  logic [FLEN-1:0] storage [FP_PRF_ENTRIES-1:0];

  // Asynchronous read ports: bypass from dedicated LSU memory response
  assign rd_data_0  = (lsu_bypass_en && (lsu_bypass_addr == rd_addr_0))  ? lsu_bypass_data : storage[rd_addr_0];
  assign rd_data_1  = (lsu_bypass_en && (lsu_bypass_addr == rd_addr_1))  ? lsu_bypass_data : storage[rd_addr_1];
  assign rd_data_2  = (lsu_bypass_en && (lsu_bypass_addr == rd_addr_2))  ? lsu_bypass_data : storage[rd_addr_2];
  assign rd_data_sq = (lsu_bypass_en && (lsu_bypass_addr == rd_addr_sq)) ? lsu_bypass_data : storage[rd_addr_sq];

  // Synchronous write ports: discrete per-entry flip-flops with single driver
  for (genvar i = 0; i < FP_PRF_ENTRIES; i++) begin : gen_fp_prf_storage
    logic [FLEN-1:0] entry_q;
    always_ff @(posedge clk) begin
      if (rst) begin
        entry_q <= '0;
      end else begin
        if (wr1_en && (wr1_addr == i[PHYS_W-1:0])) begin
          entry_q <= wr1_data;
        end else if (wr0_en && (wr0_addr == i[PHYS_W-1:0])) begin
          entry_q <= wr0_data;
        end
      end
    end
    assign storage[i] = entry_q;
  end

endmodule
