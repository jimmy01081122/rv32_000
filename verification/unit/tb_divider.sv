`timescale 1ns/1ps

module tb_divider;
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;

  logic        clk;
  logic        rst;
  logic        flush_valid;
  logic        req_valid;
  uop_op_e     req_op;
  logic [31:0] req_op0;
  logic [31:0] req_op1;
  rob_tag_t    req_rob_tag;
  phys_reg_t   req_dest_phys;
  reg_domain_e req_dest_domain;
  logic [31:0] req_pc;
  logic        req_ready;

  logic        rsp_valid;
  logic [31:0] rsp_result;
  rob_tag_t    rsp_rob_tag;
  phys_reg_t   rsp_dest_phys;
  reg_domain_e rsp_dest_domain;
  logic [31:0] rsp_pc;
  logic        rsp_ready;
  logic        busy;

  rv32_ooo_divider dut (.*);

  always #5 clk = ~clk;

  task automatic run_div_test(
    input uop_op_e     op,
    input logic [31:0] a,
    input logic [31:0] b,
    input logic [31:0] exp_res,
    input string       test_name
  );
    @(posedge clk);
    while (!req_ready) @(posedge clk);
    req_valid       <= 1'b1;
    req_op          <= op;
    req_op0         <= a;
    req_op1         <= b;
    req_rob_tag.seq <= 8'd1;
    req_rob_tag.idx <= 4'd2;
    req_dest_phys   <= 6'd10;
    req_dest_domain <= REG_INT;
    req_pc          <= 32'h8000_1000;
    rsp_ready       <= 1'b1;

    @(posedge clk);
    req_valid <= 1'b0;

    while (!rsp_valid) @(posedge clk);
    if (rsp_result !== exp_res) begin
      $display("FAIL [%s]: a=%08x, b=%08x, got=%08x, exp=%08x", test_name, a, b, rsp_result, exp_res);
      $fatal(1);
    end else begin
      $display("PASS [%s]: a=%08x, b=%08x, res=%08x", test_name, a, b, rsp_result);
    end
    @(posedge clk);
  endtask

  initial begin
    clk = 0;
    rst = 1;
    flush_valid = 0;
    req_valid = 0;
    rsp_ready = 1;
    req_op = UOP_DIV;
    req_op0 = 0;
    req_op1 = 0;
    req_rob_tag = '0;
    req_dest_phys = '0;
    req_dest_domain = REG_NONE;
    req_pc = 0;

    #20;
    rst = 0;
    #20;

    // Normal cases
    run_div_test(UOP_DIV,  32'd20,  32'd4,   32'd5,   "DIV 20/4");
    run_div_test(UOP_DIV, -32'd20,  32'd4,  -32'd5,   "DIV -20/4");
    run_div_test(UOP_DIV,  32'd20, -32'd4,  -32'd5,   "DIV 20/-4");
    run_div_test(UOP_DIV, -32'd20, -32'd4,   32'd5,   "DIV -20/-4");

    run_div_test(UOP_REM,  32'd23,  32'd4,   32'd3,   "REM 23%4");
    run_div_test(UOP_REM, -32'd23,  32'd4,  -32'd3,   "REM -23%4");
    run_div_test(UOP_REM,  32'd23, -32'd4,   32'd3,   "REM 23%-4");
    run_div_test(UOP_REM, -32'd23, -32'd4,  -32'd3,   "REM -23%-4");

    run_div_test(UOP_DIVU, 32'hFFFF_FFFF, 32'd2, 32'h7FFF_FFFF, "DIVU max/2");
    run_div_test(UOP_REMU, 32'hFFFF_FFFF, 32'd2, 32'd1,         "REMU max%2");

    // Corner cases: Divide by zero
    run_div_test(UOP_DIV,   32'd100, 32'd0, 32'hFFFF_FFFF, "DIV x/0");
    run_div_test(UOP_DIVU,  32'd100, 32'd0, 32'hFFFF_FFFF, "DIVU x/0");
    run_div_test(UOP_REM,   32'd100, 32'd0, 32'd100,       "REM x/0");
    run_div_test(UOP_REMU,  32'd100, 32'd0, 32'd100,       "REMU x/0");

    // Corner cases: Overflow INT_MIN / -1
    run_div_test(UOP_DIV,  32'h8000_0000, 32'hFFFF_FFFF, 32'h8000_0000, "DIV INT_MIN/-1");
    run_div_test(UOP_REM,  32'h8000_0000, 32'hFFFF_FFFF, 32'd0,         "REM INT_MIN/-1");

    // Backpressure test
    @(posedge clk);
    req_valid <= 1'b1;
    req_op    <= UOP_DIV;
    req_op0   <= 32'd100;
    req_op1   <= 32'd10;
    rsp_ready <= 1'b0; // hold backpressure
    @(posedge clk);
    req_valid <= 1'b0;

    while (!rsp_valid) @(posedge clk);
    #30; // wait with rsp_valid asserted under backpressure
    if (rsp_result !== 32'd10) begin
      $display("FAIL [Backpressure hold]: got %08x", rsp_result);
      $fatal(1);
    end
    @(posedge clk);
    rsp_ready <= 1'b1; // release backpressure
    @(posedge clk);
    $display("PASS [Backpressure release]");

    // Flush test
    @(posedge clk);
    req_valid <= 1'b1;
    req_op    <= UOP_DIV;
    req_op0   <= 32'd1000;
    req_op1   <= 32'd3;
    @(posedge clk);
    req_valid <= 1'b0;
    #20;
    flush_valid <= 1'b1; // abort in middle of calculation
    @(posedge clk);
    flush_valid <= 1'b0;
    #20;
    if (busy || rsp_valid) begin
      $display("FAIL [Flush]: divider not cleared");
      $fatal(1);
    end
    $display("PASS [Flush abort]");

    $display("\n=======================================================");
    $display("  ALL tb_divider TESTS PASSED!");
    $display("=======================================================");
    $finish;
  end

endmodule
