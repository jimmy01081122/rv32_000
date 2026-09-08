`timescale 1ns/1ps

module tb_multiplier;
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

  rv32_ooo_multiplier dut (.*);

  always #5 clk = ~clk;

  task automatic run_mul_test(
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
    req_rob_tag.seq <= 12'd1;
    req_rob_tag.idx <= 6'd2;
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
      $display("PASS [%s]: a=%0d (0x%08x), b=%0d (0x%08x) -> got=%0d (0x%08x)",
               test_name, $signed(a), a, $signed(b), b, $signed(rsp_result), rsp_result);
    end
  endtask

  initial begin
    clk = 0;
    rst = 1;
    flush_valid = 0;
    req_valid = 0;
    req_op = UOP_INVALID;
    req_op0 = 0;
    req_op1 = 0;
    req_rob_tag = '0;
    req_dest_phys = '0;
    req_dest_domain = REG_NONE;
    req_pc = 0;
    rsp_ready = 1;

    repeat (5) @(posedge clk);
    rst = 0;
    repeat (2) @(posedge clk);

    $display("=== 1. Basic Multiplications (MUL) ===");
    run_mul_test(UOP_MUL, 32'd20, 32'd3, 32'd60, "mul_pos_pos");
    run_mul_test(UOP_MUL, -32'd20, 32'd3, -32'd60, "mul_neg_pos");
    run_mul_test(UOP_MUL, -32'd20, -32'd3, 32'd60, "mul_neg_neg");
    run_mul_test(UOP_MUL, 32'd0, 32'd12345, 32'd0, "mul_zero");
    run_mul_test(UOP_MUL, 32'hFFFF_FFFF, 32'd1, 32'hFFFF_FFFF, "mul_all_ones_times_one");
    run_mul_test(UOP_MUL, 32'hFFFF_FFFF, 32'hFFFF_FFFF, 32'd1, "mul_minus_one_squared");

    $display("=== 2. High Signed x Signed (MULH) ===");
    run_mul_test(UOP_MULH, 32'd20, 32'd3, 32'd0, "mulh_small");
    run_mul_test(UOP_MULH, 32'h7FFF_FFFF, 32'h7FFF_FFFF, 32'h3FFF_FFFE, "mulh_max_pos");
    run_mul_test(UOP_MULH, 32'h8000_0000, 32'h8000_0000, 32'h4000_0000, "mulh_max_neg");
    run_mul_test(UOP_MULH, 32'h8000_0000, 32'hFFFF_FFFF, 32'd0, "mulh_max_neg_times_minus_one");

    $display("=== 3. High Signed x Unsigned (MULHSU) ===");
    run_mul_test(UOP_MULHSU, -32'd5, 32'd10, 32'hFFFF_FFFF, "mulhsu_neg_pos");
    run_mul_test(UOP_MULHSU, 32'd5, 32'd10, 32'd0, "mulhsu_pos_pos");
    run_mul_test(UOP_MULHSU, 32'hFFFF_FFFF, 32'h8000_0000, 32'hFFFF_FFFF, "mulhsu_minus_one_times_high");

    $display("=== 4. High Unsigned x Unsigned (MULHU) ===");
    run_mul_test(UOP_MULHU, 32'hFFFF_FFFF, 32'hFFFF_FFFF, 32'hFFFF_FFFE, "mulhu_max_unsigned");
    run_mul_test(UOP_MULHU, 32'd1000, 32'd2000, 32'd0, "mulhu_small");

    $display("=== 5. Pipelining Test: Back-to-Back Throughput ===");
    @(posedge clk);
    req_valid <= 1'b1;
    req_op <= UOP_MUL;
    req_op0 <= 32'd10;
    req_op1 <= 32'd10;
    req_pc  <= 32'h8000_2000;
    @(posedge clk);
    req_op0 <= 32'd20;
    req_op1 <= 32'd20;
    req_pc  <= 32'h8000_2004;
    @(posedge clk);
    req_op0 <= 32'd30;
    req_op1 <= 32'd30;
    req_pc  <= 32'h8000_2008;
    @(posedge clk);
    req_valid <= 1'b0;

    // Check responses arrived back-to-back
    while (!rsp_valid) @(posedge clk);
    assert(rsp_result == 32'd100) else $fatal(1, "Back-to-back 1 failed: got %d", rsp_result);
    $display("Back-to-back op 1 PASS: got %0d", rsp_result);

    @(posedge clk);
    assert(rsp_valid && rsp_result == 32'd400) else $fatal(1, "Back-to-back 2 failed: got %d", rsp_result);
    $display("Back-to-back op 2 PASS: got %0d", rsp_result);

    @(posedge clk);
    assert(rsp_valid && rsp_result == 32'd900) else $fatal(1, "Back-to-back 3 failed: got %d", rsp_result);
    $display("Back-to-back op 3 PASS: got %0d", rsp_result);

    $display("=== 6. Flush Test ===");
    @(posedge clk);
    req_valid <= 1'b1;
    req_op <= UOP_MUL;
    req_op0 <= 32'd50;
    req_op1 <= 32'd50;
    @(posedge clk);
    req_valid <= 1'b0;
    flush_valid <= 1'b1;
    @(posedge clk);
    flush_valid <= 1'b0;
    repeat (5) @(posedge clk);
    assert(!rsp_valid) else $fatal(1, "Flushed instruction produced response!");
    $display("Flush test PASS: in-flight multiply was properly killed.");

    $display("\nALL 16 MULTIPLIER UNIT TESTS PASSED SUCCESSFULLY!");
    $finish(0);
  end

endmodule
