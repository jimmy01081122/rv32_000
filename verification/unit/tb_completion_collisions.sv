
module tb_completion_collisions;
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;

  logic        clk;
  logic        rst;
  logic        flush_valid;

  core_state_e   core_state;
  dmem_pending_t dmem_pending;

  logic        issue_valid;
  exec_req_t   issue_req;
  logic        issue_ready;

  logic        agu_valid;
  exec_req_t   agu_req;
  logic [31:0] agu_addr;
  logic        lsu_ready;

  completion_t int_cmp;
  logic [31:0] int_cmp_pc;

  logic        csr_req_valid;
  csr_ctrl_t   csr_ctrl;
  logic [31:0] csr_wdata;
  logic [31:0] csr_rdata;
  logic        csr_rdata_valid;
  exception_t  csr_exc;

  logic        divider_busy;

  rv32_ooo_int_execute dut (
    .clk              (clk),
    .rst              (rst),
    .flush_valid      (flush_valid),
    .core_state       (core_state),
    .dmem_pending     (dmem_pending),
    .issue_valid      (issue_valid),
    .issue_req        (issue_req),
    .issue_ready      (issue_ready),
    .agu_valid        (agu_valid),
    .agu_req          (agu_req),
    .agu_addr         (agu_addr),
    .lsu_ready        (lsu_ready),
    .int_cmp          (int_cmp),
    .int_cmp_pc       (int_cmp_pc),
    .csr_req_valid    (csr_req_valid),
    .csr_ctrl         (csr_ctrl),
    .csr_wdata        (csr_wdata),
    .csr_rdata        (csr_rdata),
    .csr_rdata_valid  (csr_rdata_valid),
    .csr_exc          (csr_exc),
    .divider_busy     (divider_busy)
  );

  always #5 clk = ~clk;

  // Helper task to initialize signals
  task automatic init_signals();
    rst             <= 1'b1;
    flush_valid     <= 1'b0;
    core_state      <= CORE_RUN;
    dmem_pending    <= '0;
    issue_valid     <= 1'b0;
    issue_req       <= '0;
    lsu_ready       <= 1'b1;
    csr_rdata       <= 32'd0;
    csr_rdata_valid <= 1'b1;
    csr_exc         <= '0;
    @(posedge clk);
    @(posedge clk);
    rst <= 1'b0;
    @(posedge clk);
  endtask

  // Task to send an ALU op
  task automatic send_alu_op(
    input logic [11:0] seq,
    input logic [5:0]  idx,
    input logic [5:0]  dst_phys,
    input logic [31:0] op0,
    input logic [31:0] op1,
    input logic [31:0] pc
  );
    @(posedge clk);
    while (!issue_ready) @(posedge clk);
    issue_valid                 <= 1'b1;
    issue_req.uop.valid         <= 1'b1;
    issue_req.uop.fu_class      <= FU_INT_ALU;
    issue_req.uop.op            <= UOP_ADD;
    issue_req.uop.rob_tag.seq   <= seq;
    issue_req.uop.rob_tag.idx   <= idx;
    issue_req.uop.dst.valid     <= 1'b1;
    issue_req.uop.dst.domain    <= REG_INT;
    issue_req.uop.dst.new_phys  <= dst_phys;
    issue_req.uop.pc            <= pc;
    issue_req.operand0          <= op0;
    issue_req.operand1          <= op1;
    @(posedge clk);
    issue_valid <= 1'b0;
    issue_req   <= '0;
  endtask

  initial begin
    clk = 0;
    $display("=== Starting Completion Collision Unit Tests ===");

    // Test 1: Simple ALU completion
    init_signals();
    send_alu_op(12'd1, 6'd1, 6'd5, 32'd10, 32'd20, 32'h8000_0100);
    @(posedge clk);
    if (!int_cmp.valid || int_cmp.result_data !== 32'd30 || int_cmp.result_phys !== 6'd5) begin
      $display("FAIL [Test 1]: ALU simple completion failed");
      $fatal(1);
    end
    $display("PASS [Test 1]: Single-cycle ALU completion verified");

    // Test 2: Back-to-back MUL completions (1 op/cycle throughput)
    init_signals();
    @(posedge clk);
    // Send 3 back-to-back MULs
    issue_valid                 <= 1'b1;
    issue_req.uop.valid         <= 1'b1;
    issue_req.uop.fu_class      <= FU_INT_MUL;
    issue_req.uop.op            <= UOP_MUL;
    issue_req.uop.rob_tag.seq   <= 12'd10;
    issue_req.uop.rob_tag.idx   <= 6'd1;
    issue_req.uop.dst.valid     <= 1'b1;
    issue_req.uop.dst.domain    <= REG_INT;
    issue_req.uop.dst.new_phys  <= 6'd11;
    issue_req.uop.pc            <= 32'h8000_0200;
    issue_req.operand0          <= 32'd3;
    issue_req.operand1          <= 32'd4;

    @(posedge clk);
    issue_req.uop.rob_tag.seq   <= 12'd11;
    issue_req.uop.rob_tag.idx   <= 6'd2;
    issue_req.uop.dst.new_phys  <= 6'd12;
    issue_req.uop.pc            <= 32'h8000_0204;
    issue_req.operand0          <= 32'd5;
    issue_req.operand1          <= 32'd6;

    @(posedge clk);
    issue_req.uop.rob_tag.seq   <= 12'd12;
    issue_req.uop.rob_tag.idx   <= 6'd3;
    issue_req.uop.dst.new_phys  <= 6'd13;
    issue_req.uop.pc            <= 32'h8000_0208;
    issue_req.operand0          <= 32'd7;
    issue_req.operand1          <= 32'd8;

    @(posedge clk);
    issue_valid <= 1'b0;
    issue_req   <= '0;

    // Check MUL completions on consecutive cycles
    @(posedge clk); // Stage 3 latches MUL 1
    if (!int_cmp.valid || int_cmp.result_data !== 32'd12 || int_cmp.result_phys !== 6'd11) begin
      $display("FAIL [Test 2]: Back-to-back MUL 1 failed: got=%08x, exp=12", int_cmp.result_data);
      $fatal(1);
    end
    @(posedge clk); // Stage 3 latches MUL 2
    if (!int_cmp.valid || int_cmp.result_data !== 32'd30 || int_cmp.result_phys !== 6'd12) begin
      $display("FAIL [Test 2]: Back-to-back MUL 2 failed: got=%08x, exp=30", int_cmp.result_data);
      $fatal(1);
    end
    @(posedge clk); // Stage 3 latches MUL 3
    if (!int_cmp.valid || int_cmp.result_data !== 32'd56 || int_cmp.result_phys !== 6'd13) begin
      $display("FAIL [Test 2]: Back-to-back MUL 3 failed: got=%08x, exp=56", int_cmp.result_data);
      $fatal(1);
    end
    $display("PASS [Test 2]: Back-to-back MUL 1-op/cycle throughput verified");

    // Test 3: MUL completion + ALU completion collision
    init_signals();
    @(posedge clk);
    // Send MUL op (takes 3 cycles)
    issue_valid                 <= 1'b1;
    issue_req.uop.valid         <= 1'b1;
    issue_req.uop.fu_class      <= FU_INT_MUL;
    issue_req.uop.op            <= UOP_MUL;
    issue_req.uop.rob_tag.seq   <= 12'd20;
    issue_req.uop.rob_tag.idx   <= 6'd1;
    issue_req.uop.dst.valid     <= 1'b1;
    issue_req.uop.dst.domain    <= REG_INT;
    issue_req.uop.dst.new_phys  <= 6'd21;
    issue_req.uop.pc            <= 32'h8000_0300;
    issue_req.operand0          <= 32'd10;
    issue_req.operand1          <= 32'd10;
    @(posedge clk);
    issue_valid <= 1'b0; // Cycle 1: MUL stage 1 -> stage 2
    @(posedge clk);      // Cycle 2: MUL stage 2 -> stage 3

    // At cycle 2 posedge, issue an ALU op so it enters FIFO in the same cycle MUL completes!
    issue_valid                 <= 1'b1;
    issue_req.uop.valid         <= 1'b1;
    issue_req.uop.fu_class      <= FU_INT_ALU;
    issue_req.uop.op            <= UOP_ADD;
    issue_req.uop.rob_tag.seq   <= 12'd21;
    issue_req.uop.rob_tag.idx   <= 6'd2;
    issue_req.uop.dst.valid     <= 1'b1;
    issue_req.uop.dst.domain    <= REG_INT;
    issue_req.uop.dst.new_phys  <= 6'd22;
    issue_req.uop.pc            <= 32'h8000_0304;
    issue_req.operand0          <= 32'd100;
    issue_req.operand1          <= 32'd200;
    @(posedge clk);
    issue_valid <= 1'b0;
    issue_req   <= '0;

    // Cycle 3: MUL completion and ALU completion are both ready!
    // Priority: MUL > ALU. int_cmp MUST be MUL, ALU MUST wait in FIFO.
    if (!int_cmp.valid || int_cmp.result_data !== 32'd100 || int_cmp.result_phys !== 6'd21) begin
      $display("FAIL [Test 3]: MUL did not win priority over ALU on collision");
      $fatal(1);
    end
    @(posedge clk);
    // Cycle 4: ALU completion MUST drain from FIFO!
    if (!int_cmp.valid || int_cmp.result_data !== 32'd300 || int_cmp.result_phys !== 6'd22) begin
      $display("FAIL [Test 3]: ALU completion lost or corrupted after MUL collision");
      $fatal(1);
    end
    $display("PASS [Test 3]: MUL + ALU completion collision correctly arbitrated and drained");

    // Test 4: DIV completion + ALU completion collision
    init_signals();
    @(posedge clk);
    // Send DIV op: 100 / 5 = 20 (standard multi-cycle, 32 cycles)
    issue_valid                 <= 1'b1;
    issue_req.uop.valid         <= 1'b1;
    issue_req.uop.fu_class      <= FU_INT_DIV;
    issue_req.uop.op            <= UOP_DIVU;
    issue_req.uop.rob_tag.seq   <= 12'd30;
    issue_req.uop.rob_tag.idx   <= 6'd1;
    issue_req.uop.dst.valid     <= 1'b1;
    issue_req.uop.dst.domain    <= REG_INT;
    issue_req.uop.dst.new_phys  <= 6'd31;
    issue_req.uop.pc            <= 32'h8000_0400;
    issue_req.operand0          <= 32'd100;
    issue_req.operand1          <= 32'd5;
    @(posedge clk);
    issue_valid <= 1'b0;
    issue_req   <= '0;

    // Wait until DIV is about to finish
    repeat (31) @(posedge clk);

    // Issue an ALU op so it enters FIFO on the exact cycle DIV completes
    issue_valid                 <= 1'b1;
    issue_req.uop.valid         <= 1'b1;
    issue_req.uop.fu_class      <= FU_INT_ALU;
    issue_req.uop.op            <= UOP_ADD;
    issue_req.uop.rob_tag.seq   <= 12'd31;
    issue_req.uop.rob_tag.idx   <= 6'd2;
    issue_req.uop.dst.valid     <= 1'b1;
    issue_req.uop.dst.domain    <= REG_INT;
    issue_req.uop.dst.new_phys  <= 6'd32;
    issue_req.uop.pc            <= 32'h8000_0404;
    issue_req.operand0          <= 32'd50;
    issue_req.operand1          <= 32'd50;
    @(posedge clk);
    issue_valid <= 1'b0;
    issue_req   <= '0;

    // Next cycle: DIV completion and ALU completion collide!
    // Priority: DIV > ALU. DIV must drain first!
    if (!int_cmp.valid || int_cmp.result_data !== 32'd20 || int_cmp.result_phys !== 6'd31) begin
      $display("FAIL [Test 4]: DIV did not win priority over ALU on collision");
      $fatal(1);
    end
    @(posedge clk);
    // Following cycle: ALU completion drains from FIFO!
    if (!int_cmp.valid || int_cmp.result_data !== 32'd100 || int_cmp.result_phys !== 6'd32) begin
      $display("FAIL [Test 4]: ALU completion lost or corrupted after DIV collision: got=%08x, exp=100", int_cmp.result_data);
      $fatal(1);
    end
    $display("PASS [Test 4]: DIV + ALU completion collision correctly arbitrated and drained");

    // Test 5: ALU FIFO Full and Backpressure
    init_signals();
    @(posedge clk);
    // Send a DIV op to block the completion arbiter
    issue_valid                 <= 1'b1;
    issue_req.uop.valid         <= 1'b1;
    issue_req.uop.fu_class      <= FU_INT_DIV;
    issue_req.uop.op            <= UOP_DIVU;
    issue_req.uop.rob_tag.seq   <= 12'd40;
    issue_req.uop.rob_tag.idx   <= 6'd1;
    issue_req.uop.dst.valid     <= 1'b1;
    issue_req.uop.dst.domain    <= REG_INT;
    issue_req.uop.dst.new_phys  <= 6'd41;
    issue_req.uop.pc            <= 32'h8000_0500;
    issue_req.operand0          <= 32'd200;
    issue_req.operand1          <= 32'd2;
    @(posedge clk);
    issue_valid <= 1'b0;

    // Wait until DIV is about to finish
    repeat (31) @(posedge clk);

    // Issue ALU 1
    issue_valid                 <= 1'b1;
    issue_req.uop.valid         <= 1'b1;
    issue_req.uop.fu_class      <= FU_INT_ALU;
    issue_req.uop.op            <= UOP_ADD;
    issue_req.uop.rob_tag.seq   <= 12'd41;
    issue_req.uop.rob_tag.idx   <= 6'd2;
    issue_req.uop.dst.valid     <= 1'b1;
    issue_req.uop.dst.domain    <= REG_INT;
    issue_req.uop.dst.new_phys  <= 6'd42;
    issue_req.uop.pc            <= 32'h8000_0504;
    issue_req.operand0          <= 32'd1;
    issue_req.operand1          <= 32'd2;
    @(posedge clk);

    // Issue ALU 2 while DIV is completing and ALU 1 is in FIFO!
    issue_req.uop.rob_tag.seq   <= 12'd42;
    issue_req.uop.rob_tag.idx   <= 6'd3;
    issue_req.uop.dst.new_phys  <= 6'd43;
    issue_req.uop.pc            <= 32'h8000_0508;
    issue_req.operand0          <= 32'd3;
    issue_req.operand1          <= 32'd4;
    @(posedge clk);

    // Now FIFO has 2 entries. Check that issue_ready is deasserted for ALU!
    if (issue_ready !== 1'b0) begin
      $display("FAIL [Test 5]: issue_ready not deasserted when ALU FIFO is full");
      $fatal(1);
    end
    issue_valid <= 1'b0;

    // Drain cycle 1: DIV drains
    @(posedge clk);
    if (!int_cmp.valid || int_cmp.result_data !== 32'd100 || int_cmp.result_phys !== 6'd41) begin
      $display("FAIL [Test 5]: DIV drain failed: got=%08x", int_cmp.result_data);
      $fatal(1);
    end

    // Drain cycle 2: ALU 1 drains
    @(posedge clk);
    if (!int_cmp.valid || int_cmp.result_data !== 32'd3 || int_cmp.result_phys !== 6'd42) begin
      $display("FAIL [Test 5]: ALU 1 corrupted: got=%08x", int_cmp.result_data);
      $fatal(1);
    end

    // Drain cycle 3: ALU 2 drains
    @(posedge clk);
    if (!int_cmp.valid || int_cmp.result_data !== 32'd7 || int_cmp.result_phys !== 6'd43) begin
      $display("FAIL [Test 5]: ALU 2 corrupted: got=%08x", int_cmp.result_data);
      $fatal(1);
    end
    $display("PASS [Test 5]: ALU FIFO full backpressure and drain order verified");

    // Test 6: Flush while MUL pending
    init_signals();
    @(posedge clk);
    issue_valid                 <= 1'b1;
    issue_req.uop.valid         <= 1'b1;
    issue_req.uop.fu_class      <= FU_INT_MUL;
    issue_req.uop.op            <= UOP_MUL;
    issue_req.uop.rob_tag.seq   <= 12'd50;
    issue_req.uop.rob_tag.idx   <= 6'd1;
    issue_req.uop.dst.valid     <= 1'b1;
    issue_req.uop.dst.domain    <= REG_INT;
    issue_req.uop.dst.new_phys  <= 6'd51;
    issue_req.uop.pc            <= 32'h8000_0600;
    issue_req.operand0          <= 32'd10;
    issue_req.operand1          <= 32'd10;
    @(posedge clk);
    issue_valid <= 1'b0;
    @(posedge clk); // MUL in stage 2
    flush_valid <= 1'b1; // Trigger pipeline flush
    @(posedge clk);
    flush_valid <= 1'b0;

    // Wait and verify NO stale completion is ever emitted
    repeat (5) begin
      @(posedge clk);
      if (int_cmp.valid) begin
        $display("FAIL [Test 6]: Stale MUL completion emitted after flush!");
        $fatal(1);
      end
    end
    $display("PASS [Test 6]: Flush while MUL pending correctly cleared");

    // Test 7: Flush while DIV pending
    init_signals();
    @(posedge clk);
    issue_valid                 <= 1'b1;
    issue_req.uop.valid         <= 1'b1;
    issue_req.uop.fu_class      <= FU_INT_DIV;
    issue_req.uop.op            <= UOP_DIVU;
    issue_req.uop.rob_tag.seq   <= 12'd60;
    issue_req.uop.rob_tag.idx   <= 6'd1;
    issue_req.uop.dst.valid     <= 1'b1;
    issue_req.uop.dst.domain    <= REG_INT;
    issue_req.uop.dst.new_phys  <= 6'd61;
    issue_req.uop.pc            <= 32'h8000_0700;
    issue_req.operand0          <= 32'd1000;
    issue_req.operand1          <= 32'd10;
    @(posedge clk);
    issue_valid <= 1'b0;
    repeat (10) @(posedge clk); // Middle of division
    flush_valid <= 1'b1;
    @(posedge clk);
    flush_valid <= 1'b0;

    // Verify divider returned to IDLE and no stale completion is emitted
    repeat (35) begin
      @(posedge clk);
      if (int_cmp.valid) begin
        $display("FAIL [Test 7]: Stale DIV completion emitted after flush!");
        $fatal(1);
      end
    end
    if (divider_busy) begin
      $display("FAIL [Test 7]: Divider still busy after flush!");
      $fatal(1);
    end
    $display("PASS [Test 7]: Flush while DIV pending correctly cleared and divider idle");

    // Test 8: Flush while ALU FIFO contains wrong-path completion
    init_signals();
    @(posedge clk);
    // Push ALU op into FIFO
    issue_valid                 <= 1'b1;
    issue_req.uop.valid         <= 1'b1;
    issue_req.uop.fu_class      <= FU_INT_ALU;
    issue_req.uop.op            <= UOP_ADD;
    issue_req.uop.rob_tag.seq   <= 12'd70;
    issue_req.uop.rob_tag.idx   <= 6'd1;
    issue_req.uop.dst.valid     <= 1'b1;
    issue_req.uop.dst.domain    <= REG_INT;
    issue_req.uop.dst.new_phys  <= 6'd51;
    issue_req.uop.pc            <= 32'h8000_0800;
    issue_req.operand0          <= 32'd123;
    issue_req.operand1          <= 32'd456;
    @(posedge clk);
    issue_valid <= 1'b0;
    // In this cycle, ALU op is in FIFO, but flush happens simultaneously!
    flush_valid <= 1'b1;
    @(posedge clk);
    flush_valid <= 1'b0;

    repeat (5) begin
      if (int_cmp.valid) begin
        $display("FAIL [Test 8]: Wrong-path ALU completion drained after flush!");
        $fatal(1);
      end
      @(posedge clk);
    end
    $display("PASS [Test 8]: Flush while ALU FIFO populated correctly discards wrong-path completion");

    $display("================================================================");
    $display("  ALL 8 COMPLETION COLLISION & FLUSH UNIT TESTS PASSED (100%%)   ");
    $display("================================================================");
    $finish;
  end

endmodule
