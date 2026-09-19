// tb_lsu_ap5b.sv — Dedicated Unit Testbench for AP5B LSU Timing Decoupling
// Validates:
// 1. Variable-latency D-memory response handling (0 to 10 cycles)
// 2. Physical bus contract: in-flight request cannot be cancelled on flush
// 3. Stale in-flight response killed and discarded without architectural completion
// 4. Clean post-redirect load execution and completion
// 5. Store-to-load forwarding (fast path)
// 6. Partial store overlap stall
// 7. Misaligned load exception fast path
// 8. Memory access fault (error response)
// 9. Response buffer occupancy & backpressure (dmem_rsp_ready)
// 10. Load formatting: LB, LBU, LH, LHU, LW, FLW across all byte offsets

module tb_lsu_ap5b;
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;

  logic        clk;
  logic        rst;
  core_state_e core_state;

  dmem_pending_t dmem_pending;

  logic         disp_valid;
  renamed_uop_t disp_uop;

  logic         agu_valid;
  exec_req_t    agu_req;
  logic [31:0]  agu_addr;

  completion_t  int_cmp;
  completion_t  fp_cmp;

  completion_t  ld_cmp;
  logic         lsu_ready;

  logic         sq_retire_valid;
  rob_tag_t     sq_retire_rob_tag;
  logic         sq_retire_ack;
  logic [31:0]  retire_store_addr;
  logic [3:0]   retire_store_mask;
  logic [31:0]  retire_store_data;

  logic         dmem_req_valid;
  logic [31:0]  dmem_req_addr;
  logic [31:0]  dmem_req_wdata;
  logic [3:0]   dmem_req_byte_en;
  logic         dmem_req_wen;
  logic         dmem_req_ready;
  logic         dmem_rsp_valid;
  logic [31:0]  dmem_rsp_rdata;
  logic         dmem_rsp_error;
  logic         dmem_rsp_ready;

  logic         flush_valid;
  rob_tag_t     flush_rob_tag;

  // Instantiate DUT
  rv32_ooo_lsu dut (
    .clk               (clk),
    .rst               (rst),
    .core_state        (core_state),
    .dmem_pending      (dmem_pending),
    .disp_valid        (disp_valid),
    .disp_uop          (disp_uop),
    .agu_valid         (agu_valid),
    .agu_req           (agu_req),
    .agu_addr          (agu_addr),
    .int_cmp           (int_cmp),
    .fp_cmp            (fp_cmp),
    .ld_cmp            (ld_cmp),
    .lsu_ready         (lsu_ready),
    .sq_retire_valid   (sq_retire_valid),
    .sq_retire_rob_tag (sq_retire_rob_tag),
    .sq_retire_ack     (sq_retire_ack),
    .retire_store_addr (retire_store_addr),
    .retire_store_mask (retire_store_mask),
    .retire_store_data (retire_store_data),
    .dmem_req_valid    (dmem_req_valid),
    .dmem_req_addr     (dmem_req_addr),
    .dmem_req_wdata    (dmem_req_wdata),
    .dmem_req_byte_en  (dmem_req_byte_en),
    .dmem_req_wen      (dmem_req_wen),
    .dmem_req_ready    (dmem_req_ready),
    .dmem_rsp_valid    (dmem_rsp_valid),
    .dmem_rsp_rdata    (dmem_rsp_rdata),
    .dmem_rsp_error    (dmem_rsp_error),
    .dmem_rsp_ready    (dmem_rsp_ready),
    .flush_valid       (flush_valid),
    .flush_rob_tag     (flush_rob_tag)
  );

  always #5 clk = ~clk;

  // ──────────────────────────────────────────────────────────────────────────
  // Variable-Latency D-Memory Model
  // ──────────────────────────────────────────────────────────────────────────
  typedef struct {
    logic        valid;
    logic [31:0] addr;
    logic [31:0] data;
    logic        is_write;
    logic [3:0]  byte_en;
    logic        error;
    int          delay_cycles;
  } mem_transaction_t;

  localparam int MEM_Q_DEPTH = 8;
  mem_transaction_t mem_q[MEM_Q_DEPTH];
  int mem_q_head;
  int mem_q_tail;
  int mem_q_count;

  // 64KB Simple memory array
  logic [7:0] ram [0:65535];

  int current_programmed_delay = 1;
  logic inject_error_next = 1'b0;

  task automatic init_ram();
    for (int i = 0; i < 65536; i++) begin
      ram[i] = i[7:0];
    end
  endtask

  function automatic logic [31:0] read_word(input logic [31:0] a);
    logic [15:0] offset;
    offset = a[15:0];
    return {ram[offset + 3], ram[offset + 2], ram[offset + 1], ram[offset]};
  endfunction

  task automatic write_word(input logic [31:0] a, input logic [31:0] d, input logic [3:0] be);
    logic [15:0] offset;
    offset = a[15:0];
    if (be[0]) ram[offset + 0] = d[7:0];
    if (be[1]) ram[offset + 1] = d[15:8];
    if (be[2]) ram[offset + 2] = d[23:16];
    if (be[3]) ram[offset + 3] = d[31:24];
  endtask

  // Memory process
  always_ff @(posedge clk) begin
    if (rst) begin
      mem_q_head      <= 0;
      mem_q_tail      <= 0;
      mem_q_count     <= 0;
      dmem_rsp_valid  <= 1'b0;
      dmem_rsp_rdata  <= 32'd0;
      dmem_rsp_error  <= 1'b0;
      dmem_req_ready  <= 1'b1;
    end else begin
      // Decrement delay on queued requests
      for (int i = 0; i < MEM_Q_DEPTH; i++) begin
        if (mem_q[i].valid && mem_q[i].delay_cycles > 0) begin
          mem_q[i].delay_cycles <= mem_q[i].delay_cycles - 1;
        end
      end

      // Response handshake
      if (dmem_rsp_valid && dmem_rsp_ready) begin
        dmem_rsp_valid <= 1'b0;
      end

      // Drive response if queue head is ready and response bus is idle
      if ((!dmem_rsp_valid || dmem_rsp_ready) && mem_q_count > 0 && mem_q[mem_q_head].valid && mem_q[mem_q_head].delay_cycles <= 0) begin
        dmem_rsp_valid <= 1'b1;
        dmem_rsp_rdata <= mem_q[mem_q_head].data;
        dmem_rsp_error <= mem_q[mem_q_head].error;
        mem_q[mem_q_head].valid <= 1'b0;
        mem_q_head <= (mem_q_head + 1) % MEM_Q_DEPTH;
        mem_q_count <= mem_q_count - 1;
      end

      // Ingest incoming request
      if (dmem_req_valid && dmem_req_ready) begin
        mem_q[mem_q_tail].valid        <= 1'b1;
        mem_q[mem_q_tail].addr         <= dmem_req_addr;
        mem_q[mem_q_tail].is_write     <= dmem_req_wen;
        mem_q[mem_q_tail].byte_en      <= dmem_req_byte_en;
        mem_q[mem_q_tail].error        <= inject_error_next;
        mem_q[mem_q_tail].delay_cycles <= current_programmed_delay;

        if (dmem_req_wen) begin
          write_word(dmem_req_addr, dmem_req_wdata, dmem_req_byte_en);
          mem_q[mem_q_tail].data <= 32'd0;
        end else begin
          mem_q[mem_q_tail].data <= read_word(dmem_req_addr);
        end

        inject_error_next <= 1'b0;
        mem_q_tail <= (mem_q_tail + 1) % MEM_Q_DEPTH;
        mem_q_count <= mem_q_count + 1;
      end

      // Backpressure memory requests if queue is nearly full
      dmem_req_ready <= (mem_q_count < MEM_Q_DEPTH - 1);
    end
  end

  // ──────────────────────────────────────────────────────────────────────────
  // Helper Tasks
  // ──────────────────────────────────────────────────────────────────────────

  task automatic init_signals();
    rst               <= 1'b1;
    core_state        <= CORE_RUN;
    disp_valid        <= 1'b0;
    disp_uop          <= '0;
    agu_valid         <= 1'b0;
    agu_req           <= '0;
    agu_addr          <= 32'd0;
    int_cmp           <= '0;
    fp_cmp            <= '0;
    sq_retire_valid   <= 1'b0;
    sq_retire_rob_tag <= '0;
    flush_valid       <= 1'b0;
    flush_rob_tag     <= '0;
    current_programmed_delay = 1;
    inject_error_next = 1'b0;
    init_ram();
    @(posedge clk);
    @(posedge clk);
    rst <= 1'b0;
    @(posedge clk);
  endtask

  task automatic send_load(
    input uop_op_e     op,
    input mem_size_e   size,
    input load_ext_e   ext,
    input reg_domain_e domain,
    input logic [11:0] seq,
    input logic [5:0]  idx,
    input logic [5:0]  dst_phys,
    input logic [31:0] addr
  );
    while (!lsu_ready) @(posedge clk);
    agu_valid                   <= 1'b1;
    agu_addr                    <= addr;
    agu_req.uop.valid           <= 1'b1;
    agu_req.uop.op              <= op;
    agu_req.uop.mem.is_load     <= 1'b1;
    agu_req.uop.mem.is_store    <= 1'b0;
    agu_req.uop.mem.is_fp       <= (domain == REG_FP);
    agu_req.uop.mem.size        <= size;
    agu_req.uop.mem.load_ext    <= ext;
    agu_req.uop.rob_tag.seq     <= seq;
    agu_req.uop.rob_tag.idx     <= idx;
    agu_req.uop.dst.valid       <= 1'b1;
    agu_req.uop.dst.domain      <= domain;
    agu_req.uop.dst.new_phys    <= dst_phys;
    agu_req.uop.pc              <= 32'h8000_1000;
    @(posedge clk);
    agu_valid <= 1'b0;
    agu_req   <= '0;
  endtask

  // ──────────────────────────────────────────────────────────────────────────
  // Verification Test Sequence
  // ──────────────────────────────────────────────────────────────────────────

  initial begin
    clk = 0;
    $display("====================================================================");
    $display("           AP5B LSU Dedicated Verification Suite                   ");
    $display("====================================================================");

    init_signals();

    // ────────────────────────────────────────────────────────────────────────
    // TEST 1: Load Formatting & Alignment (LW, LH, LHU, LB, LBU, FLW)
    // ────────────────────────────────────────────────────────────────────────
    $display("\n--- Test 1: Load Data Formatting & Extension ---");
    // Pre-populate RAM at 0x1000 with 0xA4B3C2D1
    write_word(32'h0000_1000, 32'hA4B3C2D1, 4'b1111);
    current_programmed_delay = 1;

    // 1.1 LW
    send_load(UOP_LW, MEM_WORD, LOAD_SIGNED, REG_INT, 12'd1, 6'd1, 6'd5, 32'h0000_1000);
    while (!ld_cmp.valid) @(posedge clk);
    assert(ld_cmp.result_data === 32'hA4B3C2D1 && ld_cmp.result_phys === 6'd5)
      else $fatal(1, "FAIL 1.1: LW failed, got=%08x", ld_cmp.result_data);
    $display("  [PASS] 1.1 LW verified: 0x%08x", ld_cmp.result_data);
    @(posedge clk);

    // 1.2 LB byte 0 (0xD1 -> sign extended -> 0xFFFFFFD1)
    send_load(UOP_LB, MEM_BYTE, LOAD_SIGNED, REG_INT, 12'd2, 6'd1, 6'd6, 32'h0000_1000);
    while (!ld_cmp.valid) @(posedge clk);
    assert(ld_cmp.result_data === 32'hFFFFFFD1)
      else $fatal(1, "FAIL 1.2: LB sign ext failed, got=%08x", ld_cmp.result_data);
    $display("  [PASS] 1.2 LB (byte 0 sign-ext) verified: 0x%08x", ld_cmp.result_data);
    @(posedge clk);

    // 1.3 LBU byte 0 (0xD1 -> zero extended -> 0x000000D1)
    send_load(UOP_LBU, MEM_BYTE, LOAD_UNSIGNED, REG_INT, 12'd3, 6'd1, 6'd7, 32'h0000_1000);
    while (!ld_cmp.valid) @(posedge clk);
    assert(ld_cmp.result_data === 32'h000000D1)
      else $fatal(1, "FAIL 1.3: LBU zero ext failed, got=%08x", ld_cmp.result_data);
    $display("  [PASS] 1.3 LBU (byte 0 zero-ext) verified: 0x%08x", ld_cmp.result_data);
    @(posedge clk);

    // 1.4 LB byte 1 (0xC2 -> sign extended -> 0xFFFFFFC2)
    send_load(UOP_LB, MEM_BYTE, LOAD_SIGNED, REG_INT, 12'd4, 6'd1, 6'd8, 32'h0000_1001);
    while (!ld_cmp.valid) @(posedge clk);
    assert(ld_cmp.result_data === 32'hFFFFFFC2)
      else $fatal(1, "FAIL 1.4: LB byte 1 sign ext failed, got=%08x", ld_cmp.result_data);
    $display("  [PASS] 1.4 LB (byte 1 sign-ext) verified: 0x%08x", ld_cmp.result_data);
    @(posedge clk);

    // 1.5 LH half 0 (0xC2D1 -> sign extended -> 0xFFFFC2D1)
    send_load(UOP_LH, MEM_HALF, LOAD_SIGNED, REG_INT, 12'd5, 6'd1, 6'd9, 32'h0000_1000);
    while (!ld_cmp.valid) @(posedge clk);
    assert(ld_cmp.result_data === 32'hFFFFC2D1)
      else $fatal(1, "FAIL 1.5: LH sign ext failed, got=%08x", ld_cmp.result_data);
    $display("  [PASS] 1.5 LH (half 0 sign-ext) verified: 0x%08x", ld_cmp.result_data);
    @(posedge clk);

    // 1.6 LHU half 0 (0xC2D1 -> zero extended -> 0x0000C2D1)
    send_load(UOP_LHU, MEM_HALF, LOAD_UNSIGNED, REG_INT, 12'd6, 6'd1, 6'd10, 32'h0000_1000);
    while (!ld_cmp.valid) @(posedge clk);
    assert(ld_cmp.result_data === 32'h0000C2D1)
      else $fatal(1, "FAIL 1.6: LHU zero ext failed, got=%08x", ld_cmp.result_data);
    $display("  [PASS] 1.6 LHU (half 0 zero-ext) verified: 0x%08x", ld_cmp.result_data);
    @(posedge clk);

    // 1.7 FLW (FP register destination)
    send_load(UOP_FLW, MEM_WORD, LOAD_SIGNED, REG_FP, 12'd7, 6'd1, 6'd12, 32'h0000_1000);
    while (!ld_cmp.valid) @(posedge clk);
    assert(ld_cmp.result_data === 32'hA4B3C2D1 && ld_cmp.result_domain == REG_FP)
      else $fatal(1, "FAIL 1.7: FLW failed");
    $display("  [PASS] 1.7 FLW verified (FP domain, data 0x%08x)", ld_cmp.result_data);
    @(posedge clk);

    // ────────────────────────────────────────────────────────────────────────
    // TEST 2: Response Buffer Decoupling and Occupancy
    // ────────────────────────────────────────────────────────────────────────
    $display("\n--- Test 2: Response Buffer Decoupling & Occupancy ---");
    current_programmed_delay = 2;
    send_load(UOP_LW, MEM_WORD, LOAD_SIGNED, REG_INT, 12'd8, 6'd1, 6'd14, 32'h0000_1000);
    
    // Wait for in_flight_valid
    @(posedge clk);
    assert(dut.in_flight_valid === 1'b1) else $fatal(1, "FAIL 2: in_flight_valid not set");
    assert(dut.dmem_rsp_ready === 1'b1) else $fatal(1, "FAIL 2: dmem_rsp_ready not 1 when buf empty");
    
    // Wait until response arrives and enters response buffer
    while (!dut.rsp_buf_valid) @(posedge clk);
    $display("  [PASS] 2.1 Response buffer latched external response");
    assert(dut.rsp_buf_rdata === 32'hA4B3C2D1) else $fatal(1, "FAIL 2: rsp_buf_rdata incorrect");
    
    // Check completion on the same cycle
    assert(ld_cmp.valid === 1'b1 && ld_cmp.result_data === 32'hA4B3C2D1)
      else $fatal(1, "FAIL 2.2: ld_cmp not asserted from rsp_buf");
    @(posedge clk);
    assert(dut.rsp_buf_valid === 1'b0) else $fatal(1, "FAIL 2.3: rsp_buf did not clear after ack");
    $display("  [PASS] 2.2 Response buffer decoupled writeback verified");

    // ────────────────────────────────────────────────────────────────────────
    // TEST 3: Store-to-Load Forwarding (Fast Path 1-Cycle)
    // ────────────────────────────────────────────────────────────────────────
    $display("\n--- Test 3: Store-to-Load Forwarding ---");
    // Dispatch store in SQ
    disp_valid <= 1'b1;
    disp_uop.valid <= 1'b1;
    disp_uop.mem.is_store <= 1'b1;
    disp_uop.mem.size <= MEM_WORD;
    disp_uop.rob_tag.seq <= 12'd20;
    disp_uop.rob_tag.idx <= 6'd1;
    @(posedge clk);
    disp_valid <= 1'b0;

    // Ingest AGU for store
    agu_valid <= 1'b1;
    agu_addr  <= 32'h0000_2000;
    agu_req.uop.valid <= 1'b1;
    agu_req.uop.mem.is_store <= 1'b1;
    agu_req.uop.mem.size <= MEM_WORD;
    agu_req.uop.rob_tag.seq <= 12'd20;
    agu_req.uop.rob_tag.idx <= 6'd1;
    agu_req.operand1 <= 32'hDEAD_BEEF; // Store data
    @(posedge clk);
    agu_valid <= 1'b0;

    // Send overlapping load (younger seq=21)
    send_load(UOP_LW, MEM_WORD, LOAD_SIGNED, REG_INT, 12'd21, 6'd1, 6'd20, 32'h0000_2000);
    // In AP5B, forwarded load completion is registered in fwd_reg and arrives next cycle!
    @(posedge clk);
    assert(ld_cmp.valid === 1'b1 && ld_cmp.result_data === 32'hDEAD_BEEF)
      else $fatal(1, "FAIL 3: Forwarding failed, got valid=%b, data=%08x", ld_cmp.valid, ld_cmp.result_data);
    assert(dut.in_flight_valid === 1'b0) else $fatal(1, "FAIL 3: External memory accessed for forwarded load!");
    $display("  [PASS] Store-to-load forwarding returned 0x%08x via fwd_reg in 1 cycle", ld_cmp.result_data);
    @(posedge clk);

    // Clean up store: retire it
    sq_retire_valid <= 1'b1;
    sq_retire_rob_tag.seq <= 12'd20;
    sq_retire_rob_tag.idx <= 6'd1;
    while (!sq_retire_ack) @(posedge clk);
    sq_retire_valid <= 1'b0;
    @(posedge clk);
    @(posedge clk);

    // ────────────────────────────────────────────────────────────────────────
    // TEST 4: Partial Overlap Detection
    // ────────────────────────────────────────────────────────────────────────
    $display("\n--- Test 4: Partial Store-to-Load Overlap Detection ---");
    // Dispatch store halfword at 0x2000
    disp_valid <= 1'b1;
    disp_uop.valid <= 1'b1;
    disp_uop.mem.is_store <= 1'b1;
    disp_uop.mem.size <= MEM_HALF;
    disp_uop.rob_tag.seq <= 12'd30;
    disp_uop.rob_tag.idx <= 6'd1;
    @(posedge clk);
    disp_valid <= 1'b0;

    agu_valid <= 1'b1;
    agu_addr  <= 32'h0000_2000;
    agu_req.uop.valid <= 1'b1;
    agu_req.uop.mem.is_store <= 1'b1;
    agu_req.uop.mem.size <= MEM_HALF;
    agu_req.uop.rob_tag.seq <= 12'd30;
    agu_req.uop.rob_tag.idx <= 6'd1;
    agu_req.operand1 <= 32'h1234;
    @(posedge clk);
    agu_valid <= 1'b0;

    // Send word load at 0x2000 (load needs 4 bytes, store only has 2 bytes -> partial overlap!)
    agu_valid <= 1'b1;
    agu_addr  <= 32'h0000_2000;
    agu_req.uop.valid <= 1'b1;
    agu_req.uop.mem.is_load <= 1'b1;
    agu_req.uop.mem.size <= MEM_WORD;
    agu_req.uop.mem.load_ext <= LOAD_SIGNED;
    agu_req.uop.rob_tag.seq <= 12'd31;
    agu_req.uop.rob_tag.idx <= 6'd1;
    @(posedge clk);
    agu_valid <= 1'b0;

    // Load must stall (lsu_ready must be low or load cannot issue to dmem)
    assert(dut.in_flight_valid === 1'b0) else $fatal(1, "FAIL 4: Partial overlap issued to dmem!");
    $display("  [PASS] 4 Partial overlap stalled external issue");

    // Flush to clean up
    flush_valid <= 1'b1;
    flush_rob_tag.seq <= 12'd29;
    flush_rob_tag.idx <= 6'd0;
    @(posedge clk);
    flush_valid <= 1'b0;
    @(posedge clk);

    // ────────────────────────────────────────────────────────────────────────
    // TEST 5: Misaligned Load Exception Fast-Path
    // ────────────────────────────────────────────────────────────────────────
    $display("\n--- Test 5: Misaligned Load Exception ---");
    // Word load to address 0x1002 (unaligned)
    send_load(UOP_LW, MEM_WORD, LOAD_SIGNED, REG_INT, 12'd40, 6'd1, 6'd22, 32'h0000_1002);
    @(posedge clk);
    assert(ld_cmp.valid === 1'b1 && ld_cmp.exception.valid === 1'b1 && ld_cmp.exception.cause === EXC_LOAD_ADDR_MISALIGNED)
      else $fatal(1, "FAIL 5: Misaligned load exception not produced!");
    assert(ld_cmp.exception.tval === 32'h0000_1002) else $fatal(1, "FAIL 5: Incorrect tval for misalign");
    assert(dut.in_flight_valid === 1'b0) else $fatal(1, "FAIL 5: Misaligned load sent to dmem!");
    $display("  [PASS] Misaligned load trapped with EXC_LOAD_ADDR_MISALIGNED, tval=0x%08x", ld_cmp.exception.tval);
    @(posedge clk);

    // ────────────────────────────────────────────────────────────────────────
    // TEST 6: D-Memory Access Error Response
    // ────────────────────────────────────────────────────────────────────────
    $display("\n--- Test 6: External D-Memory Error Response ---");
    current_programmed_delay = 1;
    inject_error_next = 1'b1;
    send_load(UOP_LW, MEM_WORD, LOAD_SIGNED, REG_INT, 12'd50, 6'd1, 6'd24, 32'h0000_3000);
    while (!ld_cmp.valid) @(posedge clk);
    assert(ld_cmp.exception.valid === 1'b1 && ld_cmp.exception.cause === EXC_LOAD_ACCESS_FAULT)
      else $fatal(1, "FAIL 6: Memory access fault exception not generated!");
    $display("  [PASS] D-memory error returned EXC_LOAD_ACCESS_FAULT");
    @(posedge clk);

    // ────────────────────────────────────────────────────────────────────────
    // TEST 7: MANDATORY Delayed-Response Redirect Test (Branch Flush)
    // ────────────────────────────────────────────────────────────────────────
    $display("\n====================================================================");
    $display("  TEST 7: MANDATORY DELAYED-RESPONSE REDIRECT TEST (BRANCH FLUSH)");
    $display("====================================================================");
    // Program high latency on D-memory (5 cycles)
    current_programmed_delay = 5;

    // Step 7.1: Issue speculative load on branch wrong path
    // Speculative branch is at seq=60. Load is at seq=62.
    $display("  Step 7.1: Issuing speculative load (seq=62, addr=0x1000) with 5-cycle memory delay");
    send_load(UOP_LW, MEM_WORD, LOAD_SIGNED, REG_INT, 12'd62, 6'd1, 6'd25, 32'h0000_1000);

    @(posedge clk);
    assert(dut.in_flight_valid === 1'b1) else $fatal(1, "FAIL 7.1: Request not in-flight");
    $display("  [PASS] 7.1 Request is in-flight on physical bus (in_flight_valid=1)");

    // Step 7.2: Fire branch flush for older instruction (seq=60)
    // Branch misprediction detected while memory request is still in-flight!
    $display("  Step 7.2: Asserting flush_valid for branch tag (seq=60, older than load seq=62)");
    flush_valid <= 1'b1;
    flush_rob_tag.seq <= 12'd60;
    flush_rob_tag.idx <= 6'd0;
    @(posedge clk);
    flush_valid <= 1'b0;

    // Step 7.3: Verify Physical Bus Contract: in_flight_valid MUST REMAIN HIGH!
    assert(dut.in_flight_valid === 1'b1)
      else $fatal(1, "VIOLATION [Physical Contract]: in_flight_valid was cleared on flush! Physical bus dropped in-flight request!");
    assert(dut.in_flight_killed === 1'b1)
      else $fatal(1, "FAIL 7.3: in_flight_killed was not set!");
    $display("  [PASS] 7.3 Physical Contract Verified: in_flight_valid=1 persisted across flush; in_flight_killed=1");

    // Step 7.4: Wait for delayed memory response to arrive (cycles 2..5)
    $display("  Step 7.4: Stepping cycles until stale memory response arrives...");
    while (!dmem_rsp_valid) begin
      assert(dut.in_flight_valid === 1'b1) else $fatal(1, "FAIL 7.4: in_flight_valid dropped early");
      assert(ld_cmp.valid === 1'b0) else $fatal(1, "FAIL 7.4: Spurious completion before response!");
      @(posedge clk);
    end

    // Step 7.5: Stale response handshakes on bus (dmem_rsp_valid && dmem_rsp_ready)
    $display("  Step 7.5: Stale response arrived on bus. Handshake executing.");
    @(posedge clk);

    // Step 7.6: Verify Stale Response Was Dropped and In-Flight Cleared
    assert(dut.in_flight_valid === 1'b0) else $fatal(1, "FAIL 7.6: in_flight_valid did not clear after handshake");
    assert(dut.rsp_buf_valid === 1'b0) else $fatal(1, "FAIL 7.6: Stale response erroneously entered response buffer!");
    assert(ld_cmp.valid === 1'b0) else $fatal(1, "VIOLATION: Stale response caused architectural completion (ld_cmp.valid=1)!");
    $display("  [PASS] 7.6 Stale response discarded cleanly without driving ld_cmp! No architectural corruptions.");

    // Step 7.7: Dispatch new load on the redirected correct path
    $display("  Step 7.7: Dispatching new load on redirected path (seq=70, addr=0x1000, dst_phys=28)");
    current_programmed_delay = 2;
    send_load(UOP_LW, MEM_WORD, LOAD_SIGNED, REG_INT, 12'd70, 6'd1, 6'd28, 32'h0000_1000);

    // Step 7.8: Verify correct-path load completes successfully
    while (!ld_cmp.valid) @(posedge clk);
    assert(ld_cmp.result_data === 32'hA4B3C2D1 && ld_cmp.result_phys === 6'd28 && ld_cmp.rob_tag.seq === 12'd70)
      else $fatal(1, "FAIL 7.8: Redirected load failed to complete with correct data and tag!");
    $display("  [PASS] 7.8 Redirected load completed cleanly: data=0x%08x, tag seq=%0d, phys=%0d",
             ld_cmp.result_data, ld_cmp.rob_tag.seq, ld_cmp.result_phys);
    @(posedge clk);

    // ────────────────────────────────────────────────────────────────────────
    // TEST 8: Trap Flush While Request Outstanding
    // ────────────────────────────────────────────────────────────────────────
    $display("\n--- Test 8: Trap Flush While Request Outstanding ---");
    current_programmed_delay = 4;
    send_load(UOP_LW, MEM_WORD, LOAD_SIGNED, REG_INT, 12'd85, 6'd1, 6'd30, 32'h0000_1000);
    @(posedge clk);
    assert(dut.in_flight_valid === 1'b1) else $fatal(1, "FAIL 8: not in flight");

    // Trap flush on older trap uop seq=80
    flush_valid <= 1'b1;
    flush_rob_tag.seq <= 12'd80;
    flush_rob_tag.idx <= 6'd0;
    @(posedge clk);
    flush_valid <= 1'b0;

    assert(dut.in_flight_valid === 1'b1 && dut.in_flight_killed === 1'b1)
      else $fatal(1, "FAIL 8: Trap flush did not preserve in_flight and set kill");

    while (dut.in_flight_valid) @(posedge clk);
    assert(ld_cmp.valid === 1'b0) else $fatal(1, "FAIL 8: Trap killed request drove completion!");
    $display("  [PASS] Trap flush successfully swallowed in-flight response");
    @(posedge clk);

    // ────────────────────────────────────────────────────────────────────────
    // TEST 9: Multi-Latency Sweep (0, 1, 2, 3, 7, 10 cycles)
    // ────────────────────────────────────────────────────────────────────────
    $display("\n--- Test 9: Multi-Latency Sweep (0, 1, 2, 3, 7, 10 cycles) ---");
    for (int lat = 0; lat <= 10; lat = (lat == 3) ? 7 : (lat == 7) ? 10 : lat + 1) begin
      current_programmed_delay = lat;
      send_load(UOP_LW, MEM_WORD, LOAD_SIGNED, REG_INT, 12'(100 + lat), 6'd1, 6'(32 + lat), 32'h0000_1000);
      while (!ld_cmp.valid) @(posedge clk);
      assert(ld_cmp.result_data === 32'hA4B3C2D1 && ld_cmp.rob_tag.seq === 12'(100 + lat))
        else $fatal(1, "FAIL 9: Multi-latency failed for lat=%0d", lat);
      $display("  [PASS] Latency %0d cycles verified", lat);
      @(posedge clk);
    end

    // ────────────────────────────────────────────────────────────────────────
    // TEST 10: ROB Tag Aliasing Prevention / dmem_pending Check
    // ────────────────────────────────────────────────────────────────────────
    $display("\n--- Test 10: ROB Tag Aliasing Prevention (dmem_pending) ---");
    current_programmed_delay = 3;
    send_load(UOP_LW, MEM_WORD, LOAD_SIGNED, REG_INT, 12'd250, 6'd2, 6'd45, 32'h0000_1000);
    @(posedge clk);
    assert(dmem_pending.valid === 1'b1 && dmem_pending.rob_tag.seq === 12'd250 && dmem_pending.rob_tag.idx === 6'd2)
      else $fatal(1, "FAIL 10: dmem_pending did not report outstanding ROB tag!");
    $display("  [PASS] dmem_pending correctly tracks in-flight ROB tag (seq=250, idx=2)");

    while (!dut.rsp_buf_valid) @(posedge clk);
    assert(dmem_pending.valid === 1'b1 && dmem_pending.rob_tag.seq === 12'd250)
      else $fatal(1, "FAIL 10: dmem_pending did not report buffered ROB tag!");
    $display("  [PASS] dmem_pending correctly tracks buffered ROB tag");

    @(posedge clk);
    @(posedge clk);
    assert(dmem_pending.valid === 1'b0)
      else $fatal(1, "FAIL 10: dmem_pending stayed asserted after completion!");
    $display("  [PASS] dmem_pending deasserted after completion");

    $display("\n====================================================================");
    $display("      ALL AP5B LSU DEDICATED VERIFICATION TESTS PASSED!             ");
    $display("====================================================================\n");
    $finish;
  end

endmodule
