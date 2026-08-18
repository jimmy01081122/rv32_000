// rv32_ooo_int_execute.sv — Integer Execution Cluster
// Implements ALU, Branch / Jump unit, Multiplier / Divider (RV32M), AGU, and CSR execution
// architecture_spec.md §18, §19, §20, §21, §22 | uop_spec.md §3–§5, §18–§19

module rv32_ooo_int_execute
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic        clk,
  input  logic        rst,          // synchronous active-high

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
  input  exception_t  csr_exc
);

  wire is_lsu_op = (issue_req.uop.fu_class == FU_LSU_AGU);

  // Issue ready logic: stalls AGU if LSU cannot accept request
  assign issue_ready = is_lsu_op ? lsu_ready : (core_state == CORE_RUN);

  wire [31:0] op0 = issue_req.operand0;
  wire [31:0] op1 = issue_req.operand1;
  wire [31:0] imm = issue_req.uop.imm;
  wire [31:0] pc  = issue_req.uop.pc;
  wire [4:0]  shamt = (issue_req.uop.op == UOP_SLLI ||
                       issue_req.uop.op == UOP_SRLI ||
                       issue_req.uop.op == UOP_SRAI) ? imm[4:0] : op1[4:0];

  assign int_cmp_pc = pc;

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
  // 3. Integer Multiplier & Divider (RV32M)
  // =========================================================================

  logic [31:0] muldiv_result;

  // 64-bit products
  wire signed [63:0] mul_ss = $signed(op0) * $signed(op1);
  wire signed [63:0] mul_su = $signed(op0) * $signed({1'b0, op1});
  wire        [63:0] mul_uu = {32'd0, op0} * {32'd0, op1};

  // Division with RISC-V corner-case semantics
  wire div_by_zero = (op1 == 32'd0);
  wire div_overflow = ($signed(op0) == -32'sd2147483648) && ($signed(op1) == -32'sd1);

  always_comb begin
    muldiv_result = 32'd0;
    case (issue_req.uop.op)
      UOP_MUL:    muldiv_result = mul_ss[31:0];
      UOP_MULH:   muldiv_result = mul_ss[63:32];
      UOP_MULHSU: muldiv_result = mul_su[63:32];
      UOP_MULHU:  muldiv_result = mul_uu[63:32];

      UOP_DIV: begin
        if (div_by_zero)       muldiv_result = -32'd1;
        else if (div_overflow) muldiv_result = op0;
        else                   muldiv_result = $signed(op0) / $signed(op1);
      end

      UOP_DIVU: begin
        if (div_by_zero) muldiv_result = 32'hFFFF_FFFF;
        else             muldiv_result = op0 / op1;
      end

      UOP_REM: begin
        if (div_by_zero)       muldiv_result = op0;
        else if (div_overflow) muldiv_result = 32'd0;
        else                   muldiv_result = $signed(op0) % $signed(op1);
      end

      UOP_REMU: begin
        if (div_by_zero) muldiv_result = op0;
        else             muldiv_result = op0 % op1;
      end

      default: muldiv_result = 32'd0;
    endcase
  end

  // =========================================================================
  // 4. AGU Interface to LSU
  // =========================================================================

  assign agu_valid = issue_valid && is_lsu_op;
  assign agu_req   = issue_req;
  assign agu_addr  = op0 + imm;

  // =========================================================================
  // 5. CSR Access Interface
  // =========================================================================

  assign csr_req_valid = issue_valid && (issue_req.uop.fu_class == FU_CSR_SERIAL) && issue_req.uop.csr.valid;
  assign csr_ctrl      = issue_req.uop.csr;
  assign csr_wdata     = op0;

  // =========================================================================
  // 6. Completion Packet Formation
  // =========================================================================

  always_comb begin
    int_cmp = '0;

    if (issue_valid) begin
      // Loads do not complete in AGU; completion packet is emitted by LSU upon memory response
      if (issue_req.uop.fu_class == FU_LSU_AGU && issue_req.uop.mem.is_load) begin
        int_cmp.valid = 1'b0;
      end else begin
        int_cmp.valid     = 1'b1;
        int_cmp.rob_tag   = issue_req.uop.rob_tag;
        int_cmp.exception = issue_req.uop.exception;

        // Branch resolution
        if (issue_req.uop.fu_class == FU_BRANCH) begin
          int_cmp.branch_valid      = 1'b1;
          int_cmp.branch_taken      = branch_taken;
          int_cmp.branch_target     = branch_taken ? branch_target : (pc + 32'd4);
          int_cmp.branch_mispredict = branch_mispredict;
        end

        // Result data routing
        if (issue_req.uop.dst.valid && (issue_req.uop.dst.domain == REG_INT)) begin
          int_cmp.result_valid  = 1'b1;
          int_cmp.result_domain = REG_INT;
          int_cmp.result_phys   = issue_req.uop.dst.new_phys;

          if (issue_req.uop.fu_class == FU_INT_ALU) begin
            int_cmp.result_data = alu_result;
          end else if (issue_req.uop.fu_class == FU_BRANCH) begin
            int_cmp.result_data = link_data; // JAL / JALR link register
          end else if (issue_req.uop.fu_class == FU_INT_MUL || issue_req.uop.fu_class == FU_INT_DIV) begin
            int_cmp.result_data = muldiv_result;
          end else if (issue_req.uop.fu_class == FU_CSR_SERIAL) begin
            int_cmp.result_data = csr_rdata;
            if (csr_exc.valid) begin
              int_cmp.exception = csr_exc;
            end
          end
        end
      end
    end
  end

endmodule
