// rv32_ooo_core.sv — Top-Level Out-of-Order Core Module
// Integrates Frontend, Dual-Domain Rename, Dual Multi-Port PRFs, Dual IQs, Execution Clusters (Int & FP), CSR, and LSU
// Architecture Spec §5, §9, §11, §23, §24 | Uop Spec §2

module rv32_ooo_core
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic        clk,
  input  logic        rst,          // synchronous active-high (arch_spec §9.2)

  // Instruction memory interface (ready/valid)
  output logic        imem_req_valid,
  output logic [31:0] imem_req_addr,
  input  logic        imem_req_ready,
  input  logic        imem_rsp_valid,
  input  logic [31:0] imem_rsp_rdata,
  input  logic        imem_rsp_error,
  output logic        imem_rsp_ready,

  // Data memory interface (MAX_DMEM_OUTSTANDING=1)
  output logic        dmem_req_valid,
  output logic [31:0] dmem_req_addr,
  output logic [31:0] dmem_req_wdata,
  output logic [3:0]  dmem_req_byte_en,
  output logic        dmem_req_wen,
  input  logic        dmem_req_ready,
  input  logic        dmem_rsp_valid,
  input  logic [31:0] dmem_rsp_rdata,
  input  logic        dmem_rsp_error,
  output logic        dmem_rsp_ready,

  // Commit trace (arch_spec §29.2)
  output commit_trace_t commit_trace
);

  // =========================================================================
  // 1. Internal Signals & Busses
  // =========================================================================

  core_state_e   core_state;
  dmem_pending_t dmem_pending;

  // Fetch Epoch
  logic [FETCH_EPOCH_W-1:0] fetch_epoch;

  // Dynamic Rounding Mode from CSR
  fp_rm_e frm;

  // Frontend → Rename (Decoded uop)
  logic         dec_valid;
  decoded_uop_t dec_uop;
  logic         dec_ready;

  // Rename → Dispatch / ROB / Issue Queue (Renamed uop)
  logic         ren_valid;
  renamed_uop_t ren_uop;
  logic         ren_ready;

  // ROB Allocation
  logic         rob_alloc_valid;
  renamed_uop_t rob_alloc_uop;
  logic         rob_alloc_ready;
  rob_tag_t     rob_alloc_tag;

  // Dispatch into Issue Queues
  wire is_fp_op = (ren_uop.fu_class >= FU_FP_ADD && ren_uop.fu_class <= FU_FP_CONV);

  logic         int_disp_valid;
  renamed_uop_t int_disp_uop;
  logic         int_disp_ready;

  logic         fp_disp_valid;
  renamed_uop_t fp_disp_uop;
  logic         fp_disp_ready;

  // Issue Queue → PRF Read / Execute
  logic         int_issue_valid;
  renamed_uop_t int_issue_uop;
  exec_req_t    int_issue_req;
  logic         int_issue_ready;

  logic         fp_issue_valid;
  renamed_uop_t fp_issue_uop;
  exec_req_t    fp_issue_req;
  logic         fp_issue_ready;

  // PRF Read Data
  logic [XLEN-1:0] int_rd0, int_rd1, int_rd_sq, int_rd_fp;
  logic [FLEN-1:0] fp_rd0,  fp_rd1,  fp_rd2, fp_rd_sq;

  // Completion Busses (§24.1)
  completion_t  int_cmp;
  logic [31:0]  int_cmp_pc;
  completion_t  fp_cmp_raw;
  completion_t  ld_cmp;

  // ROB Retirement & Control Events
  logic         retire_valid;
  rob_entry_t   retire_entry;
  logic         retire_fp_valid;
  fp_flags_t    retire_fflags_delta;

  logic         rollback_valid;
  rob_tag_t     rollback_rob_tag;

  logic         trap_valid;
  logic         mret_valid;
  logic [31:0]  trap_pc, trap_cause, trap_tval;
  logic [31:0]  mtvec_out, mepc_out;

  // CSR Interface (Int Execute ↔ CSR)
  logic         csr_req_valid;
  csr_ctrl_t    csr_ctrl;
  logic [31:0]  csr_wdata;
  logic [31:0]  csr_rdata;
  logic         csr_rdata_valid;
  exception_t   csr_exc;

  // AGU & LSU Interface
  logic         agu_valid;
  exec_req_t    agu_req;
  logic [31:0]  agu_addr;
  logic         lsu_ready;

  logic         sq_retire_valid;
  rob_tag_t     sq_retire_rob_tag;
  logic         sq_retire_ack;
  logic [31:0]  retire_store_addr;
  logic [3:0]   retire_store_mask;
  logic [31:0]  retire_store_data;

  // Flush on Rollback
  logic         flush_valid;
  rob_tag_t     flush_rob_tag;

  assign flush_valid   = rollback_valid || trap_valid || mret_valid;
  assign flush_rob_tag = rollback_rob_tag;

  // =========================================================================
  // 2. Dispatch Arbitration
  // =========================================================================

  assign ren_ready = rob_alloc_ready && (is_fp_op ? fp_disp_ready : int_disp_ready);

  assign rob_alloc_valid = ren_valid && ren_ready;
  assign rob_alloc_uop   = ren_uop;

  assign int_disp_valid  = ren_valid && ren_ready && !is_fp_op;
  always_comb begin
    int_disp_uop         = ren_uop;
    int_disp_uop.rob_tag = rob_alloc_tag;
  end

  assign fp_disp_valid   = ren_valid && ren_ready && is_fp_op;
  always_comb begin
    fp_disp_uop          = ren_uop;
    fp_disp_uop.rob_tag  = rob_alloc_tag;
  end

  // =========================================================================
  // 3. AP1A: PRF Operand Fetch & EX0 Pipeline Stage
  // =========================================================================

  // EX0 Register declarations
  logic      int_ex0_valid_q;
  exec_req_t int_ex0_req_q;
  logic      int_execute_ready;

  // Downstream execution readiness
  wire int_ex0_is_lsu = int_ex0_valid_q && (int_ex0_req_q.uop.fu_class == FU_LSU_AGU);
  wire ex0_out_ready  = int_ex0_is_lsu ? lsu_ready : (core_state == CORE_RUN);
  wire ex0_out_valid  = int_ex0_valid_q;

  // Elastic input handshake to Integer IQ
  wire ex0_in_ready   = !int_ex0_valid_q || (ex0_out_valid && ex0_out_ready);
  assign int_issue_ready = ex0_in_ready;

  // PRF read data with bypass from same-cycle completion buses
  wire [31:0] int_op0_bypassed = (int_issue_uop.src0.phys == 6'd0) ? 32'd0 :
                                 (int_cmp.valid && int_cmp.result_valid && (int_cmp.result_domain == REG_INT) && (int_cmp.result_phys == int_issue_uop.src0.phys)) ? int_cmp.result_data :
                                 (fp_cmp_raw.valid && fp_cmp_raw.result_valid && (fp_cmp_raw.result_domain == REG_INT) && (fp_cmp_raw.result_phys == int_issue_uop.src0.phys)) ? fp_cmp_raw.result_data :
                                 (ld_cmp.valid && ld_cmp.result_valid && (ld_cmp.result_domain == REG_INT) && (ld_cmp.result_phys == int_issue_uop.src0.phys)) ? ld_cmp.result_data :
                                 int_rd0;

  wire [31:0] int_op1_bypassed = (int_issue_uop.src1.phys == 6'd0) ? 32'd0 :
                                 (int_cmp.valid && int_cmp.result_valid && (int_cmp.result_domain == REG_INT) && (int_cmp.result_phys == int_issue_uop.src1.phys)) ? int_cmp.result_data :
                                 (fp_cmp_raw.valid && fp_cmp_raw.result_valid && (fp_cmp_raw.result_domain == REG_INT) && (fp_cmp_raw.result_phys == int_issue_uop.src1.phys)) ? fp_cmp_raw.result_data :
                                 (ld_cmp.valid && ld_cmp.result_valid && (ld_cmp.result_domain == REG_INT) && (ld_cmp.result_phys == int_issue_uop.src1.phys)) ? ld_cmp.result_data :
                                 (int_issue_uop.mem.is_fp ? fp_rd_sq : int_rd1);

  // Integer Execution Request formation at issue
  always_comb begin
    int_issue_req.uop      = int_issue_uop;
    int_issue_req.operand0 = int_op0_bypassed;
    int_issue_req.operand1 = int_op1_bypassed;
    int_issue_req.operand2 = 32'd0;
  end

  // EX0 register sequential update
  always_ff @(posedge clk) begin
    if (rst || flush_valid) begin
      int_ex0_valid_q <= 1'b0;
      int_ex0_req_q   <= '0;
    end else begin
      if (int_issue_valid && ex0_in_ready) begin
        int_ex0_valid_q <= 1'b1;
        int_ex0_req_q   <= int_issue_req;
      end else if (ex0_out_valid && ex0_out_ready) begin
        int_ex0_valid_q <= 1'b0;
        int_ex0_req_q   <= '0;
      end
    end
  end

  // FP Execution Request
  always_comb begin
    fp_issue_req.uop      = fp_issue_uop;
    fp_issue_req.operand0 = (fp_issue_uop.src0.kind == SRC_INT_REG) ? int_rd_fp : fp_rd0;
    fp_issue_req.operand1 = fp_rd1;
    fp_issue_req.operand2 = fp_rd2;
  end

  // =========================================================================
  // 4. Redirect Priority Multiplexer (§11.3)
  // =========================================================================

  logic        redirect_valid;
  logic [31:0] redirect_pc;
  logic [FETCH_EPOCH_W-1:0] redirect_epoch;

  always_comb begin
    redirect_valid = 1'b0;
    redirect_pc    = RESET_PC;
    redirect_epoch = fetch_epoch + 4'd1;

    if (trap_valid) begin
      redirect_valid = 1'b1;
      redirect_pc    = mtvec_out;
    end else if (mret_valid) begin
      redirect_valid = 1'b1;
      redirect_pc    = (retire_entry.op == UOP_FENCE_I) ? (retire_entry.pc + 32'd4) : mepc_out;
    end else if (rollback_valid) begin
      redirect_valid = 1'b1;
      redirect_pc    = retire_entry.branch_target;
    end
  end

  // =========================================================================
  // 5. Sub-Module Instantiations
  // =========================================================================

  rv32_ooo_frontend u_frontend (
    .clk              (clk),
    .rst              (rst),
    .fetch_epoch      (fetch_epoch),
    .core_state       (core_state),
    .imem_req_valid   (imem_req_valid),
    .imem_req_addr    (imem_req_addr),
    .imem_req_ready   (imem_req_ready),
    .imem_rsp_valid   (imem_rsp_valid),
    .imem_rsp_rdata   (imem_rsp_rdata),
    .imem_rsp_error   (imem_rsp_error),
    .imem_rsp_ready   (imem_rsp_ready),
    .int_cmp          (int_cmp),
    .int_cmp_pc       (int_cmp_pc),
    .redirect_valid   (redirect_valid),
    .redirect_pc      (redirect_pc),
    .redirect_epoch   (redirect_epoch),
    .uop_valid        (dec_valid),
    .uop_out          (dec_uop),
    .uop_ready        (dec_ready)
  );

  rv32_ooo_rename u_rename (
    .clk                  (clk),
    .rst                  (rst),
    .core_state           (core_state),
    .dec_valid            (dec_valid),
    .dec_uop              (dec_uop),
    .dec_ready            (dec_ready),
    .ren_valid            (ren_valid),
    .ren_uop              (ren_uop),
    .ren_ready            (ren_ready),
    .int_cmp              (int_cmp),
    .ld_cmp               (ld_cmp),
    .fp_cmp               (fp_cmp_raw),
    .retire_valid         (retire_valid),
    .retire_entry         (retire_entry),
    .rollback_valid       (rollback_valid),
    .rollback_rob_tag     (rollback_rob_tag),
    .trap_recovery_valid  (trap_valid),
    .mret_recovery_valid  (mret_valid),
    .frm                  (frm)
  );

  rv32_ooo_rob u_rob (
    .clk                  (clk),
    .rst                  (rst),
    .core_state           (core_state),
    .dmem_pending         (dmem_pending),
    .alloc_valid          (rob_alloc_valid),
    .alloc_uop            (rob_alloc_uop),
    .alloc_ready          (rob_alloc_ready),
    .alloc_rob_tag        (rob_alloc_tag),
    .int_cmp              (int_cmp),
    .ld_cmp               (ld_cmp),
    .fp_cmp               (fp_cmp_raw),
    .sq_retire_valid      (sq_retire_valid),
    .sq_retire_rob_tag    (sq_retire_rob_tag),
    .sq_retire_ack        (sq_retire_ack),
    .retire_store_addr    (retire_store_addr),
    .retire_store_mask    (retire_store_mask),
    .retire_store_data    (retire_store_data),
    .retire_valid         (retire_valid),
    .retire_entry         (retire_entry),
    .commit_trace         (commit_trace),
    .retire_fp_valid      (retire_fp_valid),
    .retire_fflags_delta  (retire_fflags_delta),
    .rollback_valid       (rollback_valid),
    .rollback_rob_tag     (rollback_rob_tag),
    .trap_valid           (trap_valid),
    .mret_valid           (mret_valid),
    .trap_pc              (trap_pc),
    .trap_cause           (trap_cause),
    .trap_tval            (trap_tval)
  );

  rv32_ooo_int_iq u_int_iq (
    .clk            (clk),
    .rst            (rst),
    .core_state     (core_state),
    .dispatch_valid (int_disp_valid),
    .dispatch_uop   (int_disp_uop),
    .dispatch_ready (int_disp_ready),
    .int_cmp        (int_cmp),
    .ld_cmp         (ld_cmp),
    .fp_cmp         (fp_cmp_raw),
    .issue_valid    (int_issue_valid),
    .issue_uop      (int_issue_uop),
    .issue_ready    (int_issue_ready),
    .flush_valid    (flush_valid),
    .flush_rob_tag  (flush_rob_tag)
  );

  rv32_ooo_int_prf u_int_prf (
    .clk             (clk),
    .rst             (rst),
    .wr0_en          (int_cmp.valid && int_cmp.result_valid && (int_cmp.result_domain == REG_INT)),
    .wr0_addr        (int_cmp.result_phys),
    .wr0_data        (int_cmp.result_data),
    .wr1_en          ((ld_cmp.valid && ld_cmp.result_valid && (ld_cmp.result_domain == REG_INT)) ||
                      (fp_cmp_raw.valid && fp_cmp_raw.result_valid && (fp_cmp_raw.result_domain == REG_INT))),
    .wr1_addr        ((ld_cmp.valid && (ld_cmp.result_domain == REG_INT)) ? ld_cmp.result_phys : fp_cmp_raw.result_phys),
    .wr1_data        ((ld_cmp.valid && (ld_cmp.result_domain == REG_INT)) ? ld_cmp.result_data : fp_cmp_raw.result_data),
    .lsu_bypass_en   (ld_cmp.valid && ld_cmp.result_valid && (ld_cmp.result_domain == REG_INT)),
    .lsu_bypass_addr (ld_cmp.result_phys),
    .lsu_bypass_data (ld_cmp.result_data),
    .rd_addr_0       (int_issue_uop.src0.phys),
    .rd_data_0       (int_rd0),
    .rd_addr_1       (int_issue_uop.src1.phys),
    .rd_data_1       (int_rd1),
    .rd_addr_sq      (int_issue_uop.src1.phys),
    .rd_data_sq      (int_rd_sq),
    .rd_addr_fp      (fp_issue_uop.src0.phys),
    .rd_data_fp      (int_rd_fp)
  );

  rv32_ooo_fp_iq u_fp_iq (
    .clk            (clk),
    .rst            (rst),
    .core_state     (core_state),
    .dispatch_valid (fp_disp_valid),
    .dispatch_uop   (fp_disp_uop),
    .dispatch_ready (fp_disp_ready),
    .int_cmp        (int_cmp),
    .ld_cmp         (ld_cmp),
    .fp_cmp         (fp_cmp_raw),
    .issue_valid    (fp_issue_valid),
    .issue_uop      (fp_issue_uop),
    .issue_ready    (fp_issue_ready),
    .flush_valid    (flush_valid),
    .flush_rob_tag  (flush_rob_tag)
  );

  rv32_ooo_fp_prf u_fp_prf (
    .clk             (clk),
    .rst             (rst),
    .wr0_en          (fp_cmp_raw.valid && fp_cmp_raw.result_valid && (fp_cmp_raw.result_domain == REG_FP)),
    .wr0_addr        (fp_cmp_raw.result_phys),
    .wr0_data        (fp_cmp_raw.result_data),
    .wr1_en          (ld_cmp.valid && ld_cmp.result_valid && (ld_cmp.result_domain == REG_FP)),
    .wr1_addr        (ld_cmp.result_phys),
    .wr1_data        (ld_cmp.result_data),
    .lsu_bypass_en   (ld_cmp.valid && ld_cmp.result_valid && (ld_cmp.result_domain == REG_FP)),
    .lsu_bypass_addr (ld_cmp.result_phys),
    .lsu_bypass_data (ld_cmp.result_data),
    .rd_addr_0       (fp_issue_uop.src0.phys),
    .rd_data_0       (fp_rd0),
    .rd_addr_1       (fp_issue_uop.src1.phys),
    .rd_data_1       (fp_rd1),
    .rd_addr_2       (fp_issue_uop.src2.phys),
    .rd_data_2       (fp_rd2),
    .rd_addr_sq      (int_issue_uop.src1.phys), // FSW store data
    .rd_data_sq      (fp_rd_sq)
  );

  rv32_ooo_int_execute u_int_execute (
    .clk              (clk),
    .rst              (rst),
    .core_state       (core_state),
    .dmem_pending     (dmem_pending),
    .issue_valid      (int_ex0_valid_q),
    .issue_req        (int_ex0_req_q),
    .issue_ready      (int_execute_ready),
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
    .csr_exc          (csr_exc)
  );

  rv32_ooo_fp_execute u_fp_execute (
    .clk         (clk),
    .rst         (rst),
    .core_state  (core_state),
    .issue_valid (fp_issue_valid),
    .issue_req   (fp_issue_req),
    .issue_ready (fp_issue_ready),
    .fp_cmp      (fp_cmp_raw)
  );

  rv32_ooo_lsu u_lsu (
    .clk               (clk),
    .rst               (rst),
    .core_state        (core_state),
    .dmem_pending      (dmem_pending),
    .disp_valid        (int_disp_valid),
    .disp_uop          (int_disp_uop),
    .agu_valid         (agu_valid),
    .agu_req           (agu_req),
    .agu_addr          (agu_addr),
    .int_cmp           (int_cmp),
    .fp_cmp            (fp_cmp_raw),
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

  rv32_ooo_csr u_csr (
    .clk                 (clk),
    .rst                 (rst),
    .core_state          (core_state),
    .csr_req_valid       (csr_req_valid),
    .csr_ctrl            (csr_ctrl),
    .csr_wdata           (csr_wdata),
    .csr_rdata           (csr_rdata),
    .csr_rdata_valid     (csr_rdata_valid),
    .csr_exc             (csr_exc),
    .frm                 (frm),
    .trap_entry_valid    (trap_valid),
    .trap_pc             (trap_pc),
    .trap_cause          (trap_cause),
    .trap_tval           (trap_tval),
    .mtvec_out           (mtvec_out),
    .mret_valid          (mret_valid),
    .mepc_out            (mepc_out),
    .retire_fp_valid     (retire_fp_valid),
    .retire_fflags_delta (retire_fflags_delta),
    .cycle_inc           (1'b1),
    .instret_inc         (retire_valid)
  );

  // =========================================================================
  // AP1A Assertions: Flushed EX0 entry never produces completion
  // =========================================================================
`ifndef SYNTHESIS
  always_ff @(posedge clk) begin
    if (!rst && flush_valid) begin
      // On any flush event, EX0 stage must be invalidated immediately
      assert (!int_ex0_valid_q || (int_issue_valid && ex0_in_ready))
        else $error("[AP1A Assertion Failed] Flushed EX0 entry was not invalidated.");
    end
  end
`endif

endmodule
