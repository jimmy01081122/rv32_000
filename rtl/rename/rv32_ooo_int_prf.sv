// rv32_ooo_int_prf.sv — Integer Physical Register File (PRF)
// 48 entries × 32-bit XLEN, 3 asynchronous read ports with dedicated LSU bypass, 2 synchronous write ports
// architecture_spec.md §14.5 | uop_spec.md §17

module rv32_ooo_int_prf
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic clk,
  input  logic rst,            // synchronous active-high

  // Write port 0 (from ALU / Branch / MULDIV / CSR execution completion)
  input  logic            wr0_en,
  input  phys_reg_t       wr0_addr,
  input  logic [XLEN-1:0] wr0_data,

  // Write port 1 (from LSU load completion / FP-to-INT completion)
  input  logic            wr1_en,
  input  phys_reg_t       wr1_addr,
  input  logic [XLEN-1:0] wr1_data,

  // Dedicated LSU load bypass channel (purely from ld_cmp to break combinational loops)
  input  logic            lsu_bypass_en,
  input  phys_reg_t       lsu_bypass_addr,
  input  logic [XLEN-1:0] lsu_bypass_data,

  // Read port 0: IQ operand 0
  input  phys_reg_t       rd_addr_0,
  output logic [XLEN-1:0] rd_data_0,

  // Read port 1: IQ operand 1
  input  phys_reg_t       rd_addr_1,
  output logic [XLEN-1:0] rd_data_1,

  // Read port 2: SQ store-data capture
  input  phys_reg_t       rd_addr_sq,
  output logic [XLEN-1:0] rd_data_sq,

  // Read port 3: FP-IQ integer operand (e.g. FMV.W.X, FCVT.S.W)
  input  phys_reg_t       rd_addr_fp,
  output logic [XLEN-1:0] rd_data_fp
);

  logic [XLEN-1:0] storage [INT_PRF_ENTRIES-1:0];
  assign storage[0] = '0; // p0 / x0 is hardwired zero

  // Asynchronous read ports: bypass from dedicated LSU memory response, p0 is hardwired to 0
  assign rd_data_0  = (rd_addr_0  == 6'd0) ? '0 : (lsu_bypass_en && (lsu_bypass_addr == rd_addr_0))  ? lsu_bypass_data : storage[rd_addr_0];
  assign rd_data_1  = (rd_addr_1  == 6'd0) ? '0 : (lsu_bypass_en && (lsu_bypass_addr == rd_addr_1))  ? lsu_bypass_data : storage[rd_addr_1];
  assign rd_data_sq = (rd_addr_sq == 6'd0) ? '0 : (lsu_bypass_en && (lsu_bypass_addr == rd_addr_sq)) ? lsu_bypass_data : storage[rd_addr_sq];
  assign rd_data_fp = (rd_addr_fp == 6'd0) ? '0 : (lsu_bypass_en && (lsu_bypass_addr == rd_addr_fp)) ? lsu_bypass_data : storage[rd_addr_fp];

  // Synchronous write ports: discrete per-entry flip-flops with single driver
  for (genvar i = 1; i < INT_PRF_ENTRIES; i++) begin : gen_int_prf_storage
    logic [XLEN-1:0] entry_q;
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
