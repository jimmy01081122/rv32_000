// rv32_ooo_core_tb.sv — Minimal elaboration testbench
// Instantiates rv32_ooo_core and checks that it compiles and elaborates.
// Does NOT simulate any instructions (that is G3+).

module rv32_ooo_core_tb;
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;

  // DUT signals
  logic        clk;
  logic        rst;

  logic        imem_req_valid;
  logic [31:0] imem_req_addr;
  logic        imem_req_ready;
  logic        imem_rsp_valid;
  logic [31:0] imem_rsp_rdata;
  logic        imem_rsp_error;
  logic        imem_rsp_ready;

  logic        dmem_req_valid;
  logic [31:0] dmem_req_addr;
  logic [31:0] dmem_req_wdata;
  logic [3:0]  dmem_req_byte_en;
  logic        dmem_req_wen;
  logic        dmem_req_ready;
  logic        dmem_rsp_valid;
  logic [31:0] dmem_rsp_rdata;
  logic        dmem_rsp_error;
  logic        dmem_rsp_ready;

  commit_trace_t commit_trace;

  // DUT
  rv32_ooo_core dut (
    .clk              (clk),
    .rst              (rst),
    .imem_req_valid   (imem_req_valid),
    .imem_req_addr    (imem_req_addr),
    .imem_req_ready   (imem_req_ready),
    .imem_rsp_valid   (imem_rsp_valid),
    .imem_rsp_rdata   (imem_rsp_rdata),
    .imem_rsp_error   (imem_rsp_error),
    .imem_rsp_ready   (imem_rsp_ready),
    .dmem_req_valid   (dmem_req_valid),
    .dmem_req_addr    (dmem_req_addr),
    .dmem_req_wdata   (dmem_req_wdata),
    .dmem_req_byte_en (dmem_req_byte_en),
    .dmem_req_wen     (dmem_req_wen),
    .dmem_req_ready   (dmem_req_ready),
    .dmem_rsp_valid   (dmem_rsp_valid),
    .dmem_rsp_rdata   (dmem_rsp_rdata),
    .dmem_rsp_error   (dmem_rsp_error),
    .dmem_rsp_ready   (dmem_rsp_ready),
    .commit_trace     (commit_trace)
  );

  // Clock generation
  initial clk = 1'b0;
  always #5 clk = ~clk;

  // Tie memory ports to safe idle values
  assign imem_req_ready = 1'b0;
  assign imem_rsp_valid = 1'b0;
  assign imem_rsp_rdata = 32'h0000_0013;   // NOP
  assign imem_rsp_error = 1'b0;
  assign dmem_req_ready = 1'b1;
  assign dmem_rsp_valid = 1'b0;
  assign dmem_rsp_rdata = '0;
  assign dmem_rsp_error = 1'b0;

  // Cycle-based reset sequence for Verilator
  logic [7:0] cycle_cnt = 8'd0;

  always_ff @(posedge clk) begin
    cycle_cnt <= cycle_cnt + 8'd1;
    if (cycle_cnt < 8'd4) begin
      rst <= 1'b1;
    end else if (cycle_cnt < 8'd20) begin
      rst <= 1'b0;
    end else begin
      $display("G1 elaboration smoke: PASS");
      $finish;
    end
  end

endmodule
