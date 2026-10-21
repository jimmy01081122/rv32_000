// rv32_ooo_int_execute.sv — Integer Execution Cluster
// Implements ALU, Branch / Jump unit, Multiplier, Iterative Divider (RV32M), AGU, and CSR execution
// architecture_spec.md §18, §19, §20, §21, §22 | uop_spec.md §3–§5, §18–§19

module rv32_ooo_int_execute
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic        clk,
  input  logic        rst,          // synchronous active-high
  input  logic        flush_valid,  // pipeline flush/recovery

  input  core_state_e    core_state,
  input  dmem_pending_t  dmem_pending,

  // Execution request from Issue Queue (post PRF read)
  input  logic        issue_valid,
  input  exec_req_t   issue_req,
  output logic        issue_ready,

  // AGU interface to LSU
  output logic        agu_valid,
  output exec_req_t   agu_req,
  output logic [31:0] agu_addr,
  input  logic        lsu_ready,

  // Completion packet to writeback arbiter / ROB
  output completion_t int_cmp,
  output logic [31:0] int_cmp_pc,

  // CSR access interface
  output logic        csr_req_valid,
  output csr_ctrl_t   csr_ctrl,
  output logic [31:0] csr_wdata,
  input  logic [31:0] csr_rdata,
  input  logic        csr_rdata_valid,
  input  exception_t  csr_exc,

  // Functional unit status to Issue Queue
  output logic        divider_busy
);

  wire is_lsu_op = (issue_req.uop.fu_class == FU_LSU_AGU);
  wire is_div_op = (issue_req.uop.fu_class == FU_INT_DIV);
  wire is_mul_op = (issue_req.uop.fu_class == FU_INT_MUL);

  wire [31:0] op0 = issue_req.operand0;
  wire [31:0] op1 = issue_req.operand1;
  wire [31:0] imm = issue_req.uop.imm;
  wire [31:0] pc  = issue_req.uop.pc;
  wire [4:0]  shamt = (issue_req.uop.op == UOP_SLLI ||
                       issue_req.uop.op == UOP_SRLI ||
                       issue_req.uop.op == UOP_SRAI) ? imm[4:0] : op1[4:0];

  // =========================================================================
  // 1. Integer ALU
  // =========================================================================

  logic [31:0] alu_result;

  always_comb begin
    alu_result = 32'd0;
    case (issue_req.uop.op)
      UOP_ADD:  alu_result = op0 + op1;
      UOP_ADDI: alu_result = op0 + imm;
      UOP_SUB:  alu_result = op0 - op1;
      UOP_LUI:  alu_result = imm;
      UOP_AUIPC: alu_result = pc + imm;

      UOP_AND, UOP_ANDI:  alu_result = op0 & ((issue_req.uop.op == UOP_ANDI) ? imm : op1);
      UOP_OR,  UOP_ORI:   alu_result = op0 | ((issue_req.uop.op == UOP_ORI)  ? imm : op1);
      UOP_XOR, UOP_XORI:  alu_result = op0 ^ ((issue_req.uop.op == UOP_XORI) ? imm : op1);

      UOP_SLL, UOP_SLLI:  alu_result = op0 << shamt;
      UOP_SRL, UOP_SRLI:  alu_result = op0 >> shamt;
      UOP_SRA, UOP_SRAI:  alu_result = $signed(op0) >>> shamt;

      UOP_SLT, UOP_SLTI:  alu_result = ($signed(op0) < $signed((issue_req.uop.op == UOP_SLTI) ? imm : op1)) ? 32'd1 : 32'd0;
      UOP_SLTU, UOP_SLTIU: alu_result = (op0 < ((issue_req.uop.op == UOP_SLTIU) ? imm : op1)) ? 32'd1 : 32'd0;

      default: alu_result = 32'd0;
    endcase
  end

  // =========================================================================
  // 2. Branch & Jump Evaluation Unit
  // =========================================================================

  logic        branch_taken;
  logic [31:0] branch_target;
  logic        branch_mispredict;
  logic [31:0] link_data;

  always_comb begin
    branch_taken      = 1'b0;
    branch_target     = pc + imm;
    branch_mispredict = 1'b0;
    link_data         = pc + 32'd4;

    case (issue_req.uop.op)
      UOP_JAL: begin
        branch_taken      = 1'b1;
        branch_target     = pc + imm;
        branch_mispredict = 1'b1; // Redirect frontend to jump target
      end

      UOP_JALR: begin
        branch_taken      = 1'b1;
        branch_target     = (op0 + imm) & ~32'd1;
        branch_mispredict = 1'b1; // Resolved at execute
      end

      UOP_BEQ:  branch_taken = (op0 == op1);
      UOP_BNE:  branch_taken = (op0 != op1);
      UOP_BLT:  branch_taken = ($signed(op0) < $signed(op1));
      UOP_BGE:  branch_taken = ($signed(op0) >= $signed(op1));
      UOP_BLTU: branch_taken = (op0 < op1);
      UOP_BGEU: branch_taken = (op0 >= op1);
      default:  branch_taken = 1'b0;
    endcase

    if (issue_req.uop.fu_class == FU_BRANCH) begin
      if (issue_req.uop.op == UOP_JAL) begin
        branch_mispredict = (!issue_req.uop.fetch.predicted_taken) || (issue_req.uop.fetch.predicted_target != branch_target);
      end else if (issue_req.uop.op == UOP_JALR) begin
        branch_mispredict = (!issue_req.uop.fetch.predicted_taken) || (issue_req.uop.fetch.predicted_target != branch_target);
      end else begin
        // Conditional branch: compare outcome and target with prediction
        branch_mispredict = (branch_taken != issue_req.uop.fetch.predicted_taken) ||
                            (branch_taken && (issue_req.uop.fetch.predicted_target != branch_target));
      end
    end
  end

  // =========================================================================
  // =========================================================================
  // 3. Pipelined Integer Multiplier (RV32M MUL, MULH, MULHSU, MULHU)
  // =========================================================================

  logic        mul_req_valid;
  logic        mul_req_ready;
  logic        mul_rsp_valid;
  logic [31:0] mul_rsp_result;
  rob_tag_t    mul_rsp_rob_tag;
  phys_reg_t   mul_rsp_dest_phys;
  reg_domain_e mul_rsp_dest_domain;
  logic [31:0] mul_rsp_pc;
  logic        mul_rsp_ready;
  logic        multiplier_busy;

  assign mul_req_valid = issue_valid && is_mul_op;

  rv32_ooo_multiplier #(
    .LATENCY(3)
  ) u_multiplier (
    .clk              (clk),
    .rst              (rst),
    .flush_valid      (flush_valid),
    .req_valid        (mul_req_valid),
    .req_op           (issue_req.uop.op),
    .req_op0          (op0),
    .req_op1          (op1),
    .req_rob_tag      (issue_req.uop.rob_tag),
    .req_dest_phys    (issue_req.uop.dst.new_phys),
    .req_dest_domain  (issue_req.uop.dst.domain),
    .req_pc           (pc),
    .req_ready        (mul_req_ready),
    .rsp_valid        (mul_rsp_valid),
    .rsp_result       (mul_rsp_result),
    .rsp_rob_tag      (mul_rsp_rob_tag),
    .rsp_dest_phys    (mul_rsp_dest_phys),
    .rsp_dest_domain  (mul_rsp_dest_domain),
    .rsp_pc           (mul_rsp_pc),
    .rsp_ready        (mul_rsp_ready),
    .busy             (multiplier_busy)
  );

  // =========================================================================
  // 4. Multi-Cycle Iterative Divider (RV32M DIV, DIVU, REM, REMU)
  // =========================================================================

  logic        div_req_valid;
  logic        div_req_ready;
  logic        div_rsp_valid;
  logic [31:0] div_rsp_result;
  rob_tag_t    div_rsp_rob_tag;
  phys_reg_t   div_rsp_dest_phys;
  reg_domain_e div_rsp_dest_domain;
  logic [31:0] div_rsp_pc;
  logic        div_rsp_ready;

  assign div_req_valid = issue_valid && is_div_op;

  rv32_ooo_divider u_divider (
    .clk              (clk),
    .rst              (rst),
    .flush_valid      (flush_valid),
    .req_valid        (div_req_valid),
    .req_op           (issue_req.uop.op),
    .req_op0          (op0),
    .req_op1          (op1),
    .req_rob_tag      (issue_req.uop.rob_tag),
    .req_dest_phys    (issue_req.uop.dst.new_phys),
    .req_dest_domain  (issue_req.uop.dst.domain),
    .req_pc           (pc),
    .req_ready        (div_req_ready),
    .rsp_valid        (div_rsp_valid),
    .rsp_result       (div_rsp_result),
    .rsp_rob_tag      (div_rsp_rob_tag),
    .rsp_dest_phys    (div_rsp_dest_phys),
    .rsp_dest_domain  (div_rsp_dest_domain),
    .rsp_pc           (div_rsp_pc),
    .rsp_ready        (div_rsp_ready),
    .busy             (divider_busy)
  );

  wire is_load = is_lsu_op && issue_req.uop.mem.is_load;

  // =========================================================================
  // 5. AP2C: 2-Entry ALU Completion FIFO & Independent Holding Buffer
  // =========================================================================

  completion_t alu_fifo_cmp [1:0];
  logic [31:0] alu_fifo_pc  [1:0];
  logic        alu_fifo_head;
  logic        alu_fifo_tail;
  logic [1:0]  alu_fifo_count;

  wire alu_fifo_has_space = (alu_fifo_count < 2'd2);
  wire alu_fifo_empty     = (alu_fifo_count == 2'd0);
  wire alu_in_valid       = issue_valid && issue_ready && !is_load && !is_div_op && !is_mul_op;
  wire alu_can_passthru   = alu_fifo_empty && !div_has_cmp && !mul_has_cmp && alu_in_valid;
  wire alu_fifo_push      = alu_in_valid && !alu_can_passthru;
  wire alu_fifo_pop; // Driven by completion arbiter grant

  // Issue ready logic: completely decoupled per functional unit class
  always_comb begin
    if (is_div_op) begin
      issue_ready = div_req_ready;
    end else if (is_mul_op) begin
      issue_ready = mul_req_ready;
    end else if (is_lsu_op) begin
      issue_ready = is_load ? lsu_ready : (lsu_ready && alu_fifo_has_space);
    end else begin
      issue_ready = (core_state == CORE_RUN) && alu_fifo_has_space;
    end
  end

  // =========================================================================
  // 6. AGU Interface to LSU
  // =========================================================================

  assign agu_valid = issue_valid && is_lsu_op;
  assign agu_req   = issue_req;
  assign agu_addr  = op0 + imm;

  // =========================================================================
  // 7. CSR Access Interface
  // =========================================================================

  assign csr_req_valid = issue_valid && (issue_req.uop.fu_class == FU_CSR_SERIAL) && issue_req.uop.csr.valid;
  assign csr_ctrl      = issue_req.uop.csr;
  assign csr_wdata     = issue_req.uop.csr.use_zimm ? imm : op0;

  // =========================================================================
  // 8. Completion Packet Formation & Independent Producer Holding
  // =========================================================================

  completion_t alu_cmp_in;
  completion_t div_cmp;
  completion_t mul_cmp;

  // Single-cycle ALU / Branch / CSR / AGU store completion formation (into FIFO)
  always_comb begin
    alu_cmp_in = '0;

    if (issue_valid) begin
      // Loads, divide, and multiply operations do not complete in single-cycle path
      if ((issue_req.uop.fu_class == FU_LSU_AGU && issue_req.uop.mem.is_load) ||
          (issue_req.uop.fu_class == FU_INT_DIV) ||
          (issue_req.uop.fu_class == FU_INT_MUL)) begin
        alu_cmp_in.valid = 1'b0;
      end else begin
        alu_cmp_in.valid     = 1'b1;
        alu_cmp_in.rob_tag   = issue_req.uop.rob_tag;
        alu_cmp_in.exception = issue_req.uop.exception;

        // Branch resolution
        if (issue_req.uop.fu_class == FU_BRANCH) begin
          alu_cmp_in.branch_valid      = 1'b1;
          alu_cmp_in.branch_taken      = branch_taken;
          alu_cmp_in.branch_target     = branch_taken ? branch_target : (pc + 32'd4);
          alu_cmp_in.branch_mispredict = branch_mispredict;
        end

        // Result data routing
        if (issue_req.uop.dst.valid && (issue_req.uop.dst.domain == REG_INT)) begin
          alu_cmp_in.result_valid  = 1'b1;
          alu_cmp_in.result_domain = REG_INT;
          alu_cmp_in.result_phys   = issue_req.uop.dst.new_phys;

          if (issue_req.uop.fu_class == FU_INT_ALU) begin
            alu_cmp_in.result_data = alu_result;
          end else if (issue_req.uop.fu_class == FU_BRANCH) begin
            alu_cmp_in.result_data = link_data; // JAL / JALR link register
          end else if (issue_req.uop.fu_class == FU_CSR_SERIAL) begin
            alu_cmp_in.result_data = csr_rdata;
            if (csr_exc.valid) begin
              alu_cmp_in.exception = csr_exc;
            end
          end
        end
      end
    end
  end

  // Sequential update of 2-entry ALU Completion FIFO
  always_ff @(posedge clk) begin
    if (rst || flush_valid) begin
      alu_fifo_head   <= 1'b0;
      alu_fifo_tail   <= 1'b0;
      alu_fifo_count  <= 2'd0;
      alu_fifo_cmp[0] <= '0;
      alu_fifo_cmp[1] <= '0;
      alu_fifo_pc[0]  <= 32'd0;
      alu_fifo_pc[1]  <= 32'd0;
    end else begin
      case ({alu_fifo_push, alu_fifo_pop})
        2'b10: alu_fifo_count <= alu_fifo_count + 2'd1;
        2'b01: alu_fifo_count <= alu_fifo_count - 2'd1;
        default: ; // 2'b00 or 2'b11: count unchanged
      endcase

      if (alu_fifo_push) begin
        alu_fifo_cmp[alu_fifo_tail] <= alu_cmp_in;
        alu_fifo_pc[alu_fifo_tail]  <= pc;
        alu_fifo_tail               <= ~alu_fifo_tail;
      end

      if (alu_fifo_pop) begin
        alu_fifo_head               <= ~alu_fifo_head;
      end
    end
  end

  // Multi-cycle Divider completion packet
  always_comb begin
    div_cmp = '0;
    div_cmp.valid         = div_rsp_valid;
    div_cmp.rob_tag       = div_rsp_rob_tag;
    div_cmp.exception     = '0;
    div_cmp.result_valid  = (div_rsp_dest_domain == REG_INT);
    div_cmp.result_domain = div_rsp_dest_domain;
    div_cmp.result_phys   = div_rsp_dest_phys;
    div_cmp.result_data   = div_rsp_result;
  end

  // Multi-cycle Multiplier completion packet
  always_comb begin
    mul_cmp = '0;
    mul_cmp.valid         = mul_rsp_valid;
    mul_cmp.rob_tag       = mul_rsp_rob_tag;
    mul_cmp.exception     = '0;
    mul_cmp.result_valid  = (mul_rsp_dest_domain == REG_INT);
    mul_cmp.result_domain = mul_rsp_dest_domain;
    mul_cmp.result_phys   = mul_rsp_dest_phys;
    mul_cmp.result_data   = mul_rsp_result;
  end

  // =========================================================================
  // 9. Completion Arbiter (Drain at most 1 completion/cycle: DIV > MUL > ALU)
  // =========================================================================

  wire div_has_cmp = div_rsp_valid;
  wire mul_has_cmp = mul_rsp_valid;
  wire alu_has_cmp = !alu_fifo_empty || alu_can_passthru;

  wire grant_div = div_has_cmp;
  wire grant_mul = !grant_div && mul_has_cmp;
  wire grant_alu = !grant_div && !grant_mul && alu_has_cmp;

  assign div_rsp_ready = grant_div;
  assign mul_rsp_ready = grant_mul;
  assign alu_fifo_pop  = !grant_div && !grant_mul && !alu_fifo_empty;

  always_comb begin
    if (flush_valid) begin
      int_cmp    = '0;
      int_cmp_pc = 32'd0;
    end else if (grant_div) begin
      int_cmp    = div_cmp;
      int_cmp_pc = div_rsp_pc;
    end else if (grant_mul) begin
      int_cmp    = mul_cmp;
      int_cmp_pc = mul_rsp_pc;
    end else if (!alu_fifo_empty) begin
      int_cmp    = alu_fifo_cmp[alu_fifo_head];
      int_cmp_pc = alu_fifo_pc[alu_fifo_head];
    end else if (alu_can_passthru) begin
      int_cmp    = alu_cmp_in;
      int_cmp_pc = pc;
    end else begin
      int_cmp    = '0;
      int_cmp_pc = 32'd0;
    end
  end

  // =========================================================================
  // 10. Performance & Collision Counters (AP2C)
  // =========================================================================

  logic [31:0] alu_completion_wait_cycles;
  logic [31:0] mul_completion_wait_cycles;
  logic [31:0] div_completion_wait_cycles;
  logic [31:0] completion_collision_count;

  wire collision = (div_has_cmp && mul_has_cmp) ||
                   (div_has_cmp && alu_has_cmp) ||
                   (mul_has_cmp && alu_has_cmp);

  wire alu_wait = alu_has_cmp && !grant_alu;
  wire mul_wait = mul_has_cmp && !grant_mul;
  wire div_wait = div_has_cmp && !grant_div;

  always_ff @(posedge clk) begin
    if (rst) begin
      alu_completion_wait_cycles <= 32'd0;
      mul_completion_wait_cycles <= 32'd0;
      div_completion_wait_cycles <= 32'd0;
      completion_collision_count <= 32'd0;
    end else begin
      if (collision) completion_collision_count <= completion_collision_count + 32'd1;
      if (alu_wait)  alu_completion_wait_cycles <= alu_completion_wait_cycles + 32'd1;
      if (mul_wait)  mul_completion_wait_cycles <= mul_completion_wait_cycles + 32'd1;
      if (div_wait)  div_completion_wait_cycles <= div_completion_wait_cycles + 32'd1;
    end
  end


endmodule
