// rv32_ooo_frontend.sv — Instruction Fetch & Decode Engine
// Pipelined instruction fetch, dynamic branch predictor (BTB + 2-bit BHT + RAS),
// and single-cycle RV32I / RV32M / RV32F / Zicsr decoder.
// Architecture Spec §12, §13, §23 | Uop Spec §4–§15

module rv32_ooo_frontend
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic clk,
  input  logic rst,          // synchronous active-high (arch_spec §9.2)

  // Current fetch epoch for tag comparison
  output logic [FETCH_EPOCH_W-1:0] fetch_epoch,

  // Core state from ROB
  input  core_state_e core_state,

  // Instruction memory interface (Pipelined ready/valid)
  output logic        imem_req_valid,
  output logic [31:0] imem_req_addr,
  input  logic        imem_req_ready,
  input  logic        imem_rsp_valid,
  input  logic [31:0] imem_rsp_rdata,
  input  logic        imem_rsp_error,
  output logic        imem_rsp_ready,

  // Branch prediction update / training from execution
  input  completion_t               int_cmp,
  input  logic [31:0]               int_cmp_pc,

  // Redirect interface (from ROB: rollback, trap, mret)
  input  logic                      redirect_valid,
  input  logic [31:0]               redirect_pc,
  input  logic [FETCH_EPOCH_W-1:0]  redirect_epoch,

  // Output to Rename stage (decoded uop)
  output logic         uop_valid,
  output decoded_uop_t uop_out,
  input  logic         uop_ready
);

  // =========================================================================
  // 1. Branch Predictor (64-entry BTB + 64-entry 2-bit BHT + 4-entry RAS)
  // =========================================================================

  localparam int BTB_ENTRIES = 64;
  localparam int BTB_INDEX_BITS = 6;
  localparam int BTB_TAG_BITS = 10;

  typedef struct packed {
    logic                    valid;
    logic [BTB_TAG_BITS-1:0] tag;
    logic [31:0]             target;
    logic                    is_jump;
  } btb_entry_t;

  btb_entry_t btb [BTB_ENTRIES-1:0];
  logic [1:0] bht [BTB_ENTRIES-1:0];

  // Current PC and epoch registers
  logic [31:0]              fetch_pc;
  logic [FETCH_EPOCH_W-1:0] current_epoch;

  assign fetch_epoch = current_epoch;

  // BTB / BHT lookup for current fetch_pc
  wire [BTB_INDEX_BITS-1:0] fetch_idx = fetch_pc[BTB_INDEX_BITS+1:2];
  wire [BTB_TAG_BITS-1:0]   fetch_tag = fetch_pc[BTB_INDEX_BITS+1+BTB_TAG_BITS : BTB_INDEX_BITS+2];

  wire btb_hit = btb[fetch_idx].valid && (btb[fetch_idx].tag == fetch_tag);
  wire bht_taken = (bht[fetch_idx] >= 2'b10);

  wire pred_taken = btb_hit && (btb[fetch_idx].is_jump || bht_taken);
  wire [31:0] pred_target = btb_hit ? btb[fetch_idx].target : (fetch_pc + 32'd4);

  wire [31:0] next_fetch_pc = pred_taken ? pred_target : (fetch_pc + 32'd4);

  // =========================================================================
  // 2. In-Flight Instruction Request Tracking (Depth 4)
  // =========================================================================

  localparam int INFLIGHT_DEPTH = 4;
  typedef struct packed {
    logic [31:0]              pc;
    logic [FETCH_EPOCH_W-1:0] epoch;
    logic                     pred_taken;
    logic [31:0]              pred_target;
  } inflight_req_t;

  inflight_req_t if_queue [INFLIGHT_DEPTH-1:0];
  logic [1:0] if_head_ptr, if_tail_ptr;
  logic [2:0] if_count;

  wire if_full  = (if_count == INFLIGHT_DEPTH[2:0]);
  wire if_empty = (if_count == 3'd0);

  // =========================================================================
  // 3. Instruction Queue FIFO (Depth 8)
  // =========================================================================

  localparam int IQ_DEPTH = 8;
  typedef struct packed {
    logic [31:0]              pc;
    logic [31:0]              insn;
    logic [FETCH_EPOCH_W-1:0] epoch;
    logic                     pred_taken;
    logic [31:0]              pred_target;
    exception_t               exception;
  } iq_entry_t;

  iq_entry_t iq_mem [IQ_DEPTH-1:0];
  logic [2:0] iq_head_ptr, iq_tail_ptr;
  logic [3:0] iq_count;

  wire iq_full  = (iq_count == IQ_DEPTH[3:0]);
  wire iq_empty = (iq_count == 4'd0);

  // Pipelined Fetch handshake: can send request as long as total in-flight + queued < IQ_DEPTH
  wire can_fetch = !if_full && ((iq_count + {1'b0, if_count}) < (IQ_DEPTH[3:0] - 4'd1)) && (core_state == CORE_RUN);

  assign imem_req_valid = can_fetch && !rst;
  assign imem_req_addr  = fetch_pc;
  assign imem_rsp_ready = 1'b1;

  // Decode-Stage Fast JAL / BTFN Correction
  iq_entry_t iq_head_peek;
  assign iq_head_peek = iq_mem[iq_head_ptr];

  wire [31:0] dec_peek_insn   = iq_head_peek.insn;
  wire [6:0]  dec_peek_op     = dec_peek_insn[6:0];
  wire [31:0] dec_peek_imm_j  = {{11{dec_peek_insn[31]}}, dec_peek_insn[31], dec_peek_insn[19:12], dec_peek_insn[20], dec_peek_insn[30:21], 1'b0};
  wire [31:0] dec_peek_imm_b  = {{19{dec_peek_insn[31]}}, dec_peek_insn[31], dec_peek_insn[7], dec_peek_insn[30:25], dec_peek_insn[11:8], 1'b0};

  wire dec_jal_redirect  = !iq_empty && (dec_peek_op == 7'b1101111) && !iq_head_peek.pred_taken && (iq_head_peek.epoch == current_epoch);
  wire [31:0] dec_jal_target = iq_head_peek.pc + dec_peek_imm_j;

  wire dec_loop_redirect = !iq_empty && (dec_peek_op == 7'b1100011) && (dec_peek_imm_b[31] == 1'b1) && !iq_head_peek.pred_taken && (iq_head_peek.epoch == current_epoch);
  wire [31:0] dec_loop_target = iq_head_peek.pc + dec_peek_imm_b;

  wire dec_redirect_valid  = (dec_jal_redirect || dec_loop_redirect) && (core_state == CORE_RUN);
  wire [31:0] dec_redirect_pc = dec_jal_redirect ? dec_jal_target : dec_loop_target;

  // Sequential Fetch Control & Queue Updates
  always_ff @(posedge clk) begin
    if (rst) begin
      fetch_pc      <= RESET_PC;
      current_epoch <= '0;
      iq_head_ptr   <= '0;
      iq_tail_ptr   <= '0;
      iq_count      <= '0;
      if_head_ptr   <= '0;
      if_tail_ptr   <= '0;
      if_count      <= '0;

      for (int k = 0; k < BTB_ENTRIES; k++) begin
        btb[k] <= '0;
        bht[k] <= 2'b01;
      end
    end else begin
      // Branch Predictor Training from Integer Execution
      if (int_cmp.valid && int_cmp.branch_valid) begin
        logic [BTB_INDEX_BITS-1:0] train_idx;
        logic [BTB_TAG_BITS-1:0]   train_tag;
        train_idx = int_cmp_pc[BTB_INDEX_BITS+1:2];
        train_tag = int_cmp_pc[BTB_INDEX_BITS+1+BTB_TAG_BITS : BTB_INDEX_BITS+2];

        btb[train_idx].valid   <= 1'b1;
        btb[train_idx].tag     <= train_tag;
        btb[train_idx].target  <= int_cmp.branch_target;
        btb[train_idx].is_jump <= (int_cmp.result_valid && (int_cmp.result_data == (int_cmp_pc + 32'd4)));

        if (int_cmp.branch_taken) begin
          if (bht[train_idx] != 2'b11) bht[train_idx] <= bht[train_idx] + 2'b01;
        end else begin
          if (bht[train_idx] != 2'b00) bht[train_idx] <= bht[train_idx] - 2'b01;
        end
      end

      // Priority 1: ROB Pipeline Redirect (Trap / Mispredict Rollback)
      if (redirect_valid) begin
        fetch_pc      <= redirect_pc;
        current_epoch <= redirect_epoch;
        iq_head_ptr   <= '0;
        iq_tail_ptr   <= '0;
        iq_count      <= '0;
        if_head_ptr   <= '0;
        if_tail_ptr   <= '0;
        if_count      <= '0;
      end
      // Priority 2: Normal Pipelined Fetch & Queue Processing
      else begin
        if (imem_req_valid && imem_req_ready) begin
          if_queue[if_tail_ptr].pc          <= fetch_pc;
          if_queue[if_tail_ptr].epoch       <= current_epoch;
          if_queue[if_tail_ptr].pred_taken  <= pred_taken;
          if_queue[if_tail_ptr].pred_target <= pred_target;
          if_tail_ptr                       <= if_tail_ptr + 2'd1;
          fetch_pc                          <= next_fetch_pc;
        end

        if (imem_rsp_valid && imem_rsp_ready && !if_empty) begin
          inflight_req_t resp_req;
          resp_req = if_queue[if_head_ptr];
          if_head_ptr <= if_head_ptr + 2'd1;

          if (resp_req.epoch == current_epoch) begin
            iq_mem[iq_tail_ptr].pc          <= resp_req.pc;
            iq_mem[iq_tail_ptr].insn        <= imem_rsp_rdata;
            iq_mem[iq_tail_ptr].epoch       <= resp_req.epoch;
            iq_mem[iq_tail_ptr].pred_taken  <= resp_req.pred_taken;
            iq_mem[iq_tail_ptr].pred_target <= resp_req.pred_target;

            if (imem_rsp_error) begin
              iq_mem[iq_tail_ptr].exception <= '{valid: 1'b1, cause: EXC_INST_ACCESS_FAULT, tval: resp_req.pc};
            end else if (resp_req.pc[1:0] != 2'b00) begin
              iq_mem[iq_tail_ptr].exception <= '{valid: 1'b1, cause: EXC_INST_ADDR_MISALIGNED, tval: resp_req.pc};
            end else begin
              iq_mem[iq_tail_ptr].exception <= '{valid: 1'b0, cause: 5'd0, tval: 32'd0};
            end

            iq_tail_ptr <= iq_tail_ptr + 3'd1;
          end
        end

        if (uop_valid && uop_ready) begin
          iq_head_ptr <= iq_head_ptr + 3'd1;
        end

        begin : blk_occupancy
          logic if_pushed;
          logic if_popped;
          logic iq_pushed;
          logic iq_popped;

          if_pushed = (imem_req_valid && imem_req_ready);
          if_popped = (imem_rsp_valid && imem_rsp_ready && !if_empty);
          case ({if_pushed, if_popped})
            2'b10: if_count <= if_count + 3'd1;
            2'b01: if_count <= if_count - 3'd1;
            default: ;
          endcase

          iq_pushed = (imem_rsp_valid && imem_rsp_ready && !if_empty && (if_queue[if_head_ptr].epoch == current_epoch));
          iq_popped = (uop_valid && uop_ready);
          case ({iq_pushed, iq_popped})
            2'b10: iq_count <= iq_count + 4'd1;
            2'b01: iq_count <= iq_count - 4'd1;
            default: ;
          endcase
        end
      end
    end
  end

// 4. Instruction Decoder & Uop Generator (Comb)
  // =========================================================================

  iq_entry_t iq_head;
  assign iq_head = iq_mem[iq_head_ptr];

  wire [31:0] insn = iq_head.insn;
  wire [6:0]  opcode = insn[6:0];
  wire [2:0]  funct3 = insn[14:12];
  wire [6:0]  funct7 = insn[31:25];
  wire [4:0]  rd     = insn[11:7];
  wire [4:0]  rs1    = insn[19:15];
  wire [4:0]  rs2    = insn[24:20];
  wire [4:0]  rs3    = insn[31:27];

  // Immediate Formations
  wire [31:0] imm_i     = {{20{insn[31]}}, insn[31:20]};
  wire [31:0] imm_s     = {{20{insn[31]}}, insn[31:25], insn[11:7]};
  wire [31:0] imm_b     = {{19{insn[31]}}, insn[31], insn[7], insn[30:25], insn[11:8], 1'b0};
  wire [31:0] imm_u     = {insn[31:12], 12'b0};
  wire [31:0] imm_j     = {{11{insn[31]}}, insn[31], insn[19:12], insn[20], insn[30:21], 1'b0};
  wire [31:0] imm_shamt = {27'd0, insn[24:20]};
  wire [31:0] imm_zimm  = {27'd0, insn[19:15]};

  decoded_uop_t dec;

  always_comb begin
    // Default assignments
    dec.pc                     = iq_head.pc;
    dec.insn                   = iq_head.insn;
    dec.fetch.epoch            = iq_head.epoch;
    dec.fetch.predicted_taken  = iq_head.pred_taken;
    dec.fetch.predicted_target = iq_head.pred_target;
    dec.op                     = UOP_INVALID;
    dec.fu_class               = FU_INT_ALU;
    dec.src0                   = '{kind: SRC_NONE, arch: 5'd0};
    dec.src1                   = '{kind: SRC_NONE, arch: 5'd0};
    dec.src2                   = '{kind: SRC_NONE, arch: 5'd0};
    dec.dst                    = '{valid: 1'b0, domain: REG_INT, arch: 5'd0};
    dec.imm_kind               = IMM_NONE;
    dec.imm                    = 32'd0;
    dec.mem                    = '{is_load: 1'b0, is_store: 1'b0, is_fp: 1'b0, size: MEM_WORD, load_ext: LOAD_UNSIGNED};
    dec.branch                 = '{kind: BR_NONE, writes_link: 1'b0};
    dec.csr                    = '{valid: 1'b0, cmd: CSR_NONE, addr: 12'd0, use_zimm: 1'b0, read_enable: 1'b0, write_enable: 1'b0};
    dec.fp                     = '{valid: 1'b0, uses_rm: 1'b0, rm: RM_RNE, may_set_flags: 1'b0};
    dec.serializing       = 1'b0;
    dec.requires_rob_head = 1'b0;
    dec.alloc_lq          = 1'b0;
    dec.alloc_sq          = 1'b0;
    dec.exception         = iq_head.exception;

    if (!iq_head.exception.valid) begin
      case (opcode)
        // ── LUI ────────────────────────────────────────────────────────────
        7'b0110111: begin
          dec.op       = UOP_LUI;
          dec.fu_class = FU_INT_ALU;
          dec.dst      = '{valid: 1'b1, domain: REG_INT, arch: rd};
          dec.src0     = '{kind: SRC_NONE, arch: 5'd0};
          dec.imm_kind = IMM_U;
          dec.imm      = imm_u;
        end

        // ── AUIPC ──────────────────────────────────────────────────────────
        7'b0010111: begin
          dec.op       = UOP_AUIPC;
          dec.fu_class = FU_INT_ALU;
          dec.dst      = '{valid: 1'b1, domain: REG_INT, arch: rd};
          dec.src0     = '{kind: SRC_PC, arch: 5'd0};
          dec.imm_kind = IMM_U;
          dec.imm      = imm_u;
        end

        // ── JAL ───────────────────────────────────────────────────────────
        7'b1101111: begin
          dec.op          = UOP_JAL;
          dec.fu_class    = FU_BRANCH;
          dec.dst         = '{valid: 1'b1, domain: REG_INT, arch: rd};
          dec.src0        = '{kind: SRC_PC, arch: 5'd0};
          dec.imm_kind    = IMM_J;
          dec.imm         = imm_j;
          dec.branch.kind = BR_JAL;
          dec.branch.writes_link = (rd != 5'd0);
        end

        // ── JALR ──────────────────────────────────────────────────────────
        7'b1100111: begin
          if (funct3 == 3'b000) begin
            dec.op          = UOP_JALR;
            dec.fu_class    = FU_BRANCH;
            dec.dst         = '{valid: 1'b1, domain: REG_INT, arch: rd};
            dec.src0        = '{kind: SRC_INT_REG, arch: rs1};
            dec.imm_kind    = IMM_I;
            dec.imm         = imm_i;
            dec.branch.kind = BR_JALR;
            dec.branch.writes_link = (rd != 5'd0);
          end else begin
            dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
          end
        end

        // ── BRANCH ────────────────────────────────────────────────────────
        7'b1100011: begin
          dec.fu_class    = FU_BRANCH;
          dec.src0        = '{kind: SRC_INT_REG, arch: rs1};
          dec.src1        = '{kind: SRC_INT_REG, arch: rs2};
          dec.imm_kind    = IMM_B;
          dec.imm         = imm_b;
          case (funct3)
            3'b000: begin dec.op = UOP_BEQ;  dec.branch.kind = BR_EQ;  end
            3'b001: begin dec.op = UOP_BNE;  dec.branch.kind = BR_NE;  end
            3'b100: begin dec.op = UOP_BLT;  dec.branch.kind = BR_LT;  end
            3'b101: begin dec.op = UOP_BGE;  dec.branch.kind = BR_GE;  end
            3'b110: begin dec.op = UOP_BLTU; dec.branch.kind = BR_LTU; end
            3'b111: begin dec.op = UOP_BGEU; dec.branch.kind = BR_GEU; end
            default: dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
          endcase
        end

        // ── LOAD ──────────────────────────────────────────────────────────
        7'b0000011: begin
          dec.fu_class    = FU_LSU_AGU;
          dec.dst         = '{valid: 1'b1, domain: REG_INT, arch: rd};
          dec.src0        = '{kind: SRC_INT_REG, arch: rs1};
          dec.imm_kind    = IMM_I;
          dec.imm         = imm_i;
          dec.alloc_lq    = 1'b1;
          dec.mem.is_load = 1'b1;
          case (funct3)
            3'b000: begin dec.op = UOP_LB;  dec.mem.size = MEM_BYTE; dec.mem.load_ext = LOAD_SIGNED;   end
            3'b001: begin dec.op = UOP_LH;  dec.mem.size = MEM_HALF; dec.mem.load_ext = LOAD_SIGNED;   end
            3'b010: begin dec.op = UOP_LW;  dec.mem.size = MEM_WORD; dec.mem.load_ext = LOAD_SIGNED;   end
            3'b100: begin dec.op = UOP_LBU; dec.mem.size = MEM_BYTE; dec.mem.load_ext = LOAD_UNSIGNED; end
            3'b101: begin dec.op = UOP_LHU; dec.mem.size = MEM_HALF; dec.mem.load_ext = LOAD_UNSIGNED; end
            default: dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
          endcase
        end

        // ── STORE ─────────────────────────────────────────────────────────
        7'b0100011: begin
          dec.fu_class     = FU_LSU_AGU;
          dec.src0         = '{kind: SRC_INT_REG, arch: rs1};
          dec.src1         = '{kind: SRC_INT_REG, arch: rs2};
          dec.imm_kind     = IMM_S;
          dec.imm          = imm_s;
          dec.alloc_sq     = 1'b1;
          dec.mem.is_store = 1'b1;
          case (funct3)
            3'b000: begin dec.op = UOP_SB; dec.mem.size = MEM_BYTE; end
            3'b001: begin dec.op = UOP_SH; dec.mem.size = MEM_HALF; end
            3'b010: begin dec.op = UOP_SW; dec.mem.size = MEM_WORD; end
            default: dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
          endcase
        end

        // ── OP-IMM ────────────────────────────────────────────────────────
        7'b0010011: begin
          dec.fu_class = FU_INT_ALU;
          dec.dst      = '{valid: 1'b1, domain: REG_INT, arch: rd};
          dec.src0     = '{kind: SRC_INT_REG, arch: rs1};
          dec.imm_kind = IMM_I;
          dec.imm      = imm_i;
          case (funct3)
            3'b000: dec.op = UOP_ADDI;
            3'b010: dec.op = UOP_SLTI;
            3'b011: dec.op = UOP_SLTIU;
            3'b100: dec.op = UOP_XORI;
            3'b110: dec.op = UOP_ORI;
            3'b111: dec.op = UOP_ANDI;
            3'b001: begin
              if (funct7 == 7'b0000000) begin
                dec.op       = UOP_SLLI;
                dec.imm_kind = IMM_SHAMT;
                dec.imm      = imm_shamt;
              end else begin
                dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
              end
            end
            3'b101: begin
              dec.imm_kind = IMM_SHAMT;
              dec.imm      = imm_shamt;
              if (funct7 == 7'b0000000)      dec.op = UOP_SRLI;
              else if (funct7 == 7'b0100000) dec.op = UOP_SRAI;
              else dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
            end
            default: dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
          endcase
        end

        // ── OP & M-Extension ──────────────────────────────────────────────
        7'b0110011: begin
          dec.dst  = '{valid: 1'b1, domain: REG_INT, arch: rd};
          dec.src0 = '{kind: SRC_INT_REG, arch: rs1};
          dec.src1 = '{kind: SRC_INT_REG, arch: rs2};
          if (funct7 == 7'b0000000) begin
            dec.fu_class = FU_INT_ALU;
            case (funct3)
              3'b000: dec.op = UOP_ADD;
              3'b001: dec.op = UOP_SLL;
              3'b010: dec.op = UOP_SLT;
              3'b011: dec.op = UOP_SLTU;
              3'b100: dec.op = UOP_XOR;
              3'b101: dec.op = UOP_SRL;
              3'b110: dec.op = UOP_OR;
              3'b111: dec.op = UOP_AND;
              default: dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
            endcase
          end else if (funct7 == 7'b0100000) begin
            dec.fu_class = FU_INT_ALU;
            case (funct3)
              3'b000: dec.op = UOP_SUB;
              3'b101: dec.op = UOP_SRA;
              default: dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
            endcase
          end else if (funct7 == 7'b0000001) begin
            // RV32M Extension
            case (funct3)
              3'b000: begin dec.op = UOP_MUL;    dec.fu_class = FU_INT_MUL; end
              3'b001: begin dec.op = UOP_MULH;   dec.fu_class = FU_INT_MUL; end
              3'b010: begin dec.op = UOP_MULHSU; dec.fu_class = FU_INT_MUL; end
              3'b011: begin dec.op = UOP_MULHU;  dec.fu_class = FU_INT_MUL; end
              3'b100: begin dec.op = UOP_DIV;    dec.fu_class = FU_INT_DIV; end
              3'b101: begin dec.op = UOP_DIVU;   dec.fu_class = FU_INT_DIV; end
              3'b110: begin dec.op = UOP_REM;    dec.fu_class = FU_INT_DIV; end
              3'b111: begin dec.op = UOP_REMU;   dec.fu_class = FU_INT_DIV; end
              default: dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
            endcase
          end else begin
            dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
          end
        end

        // ── LOAD-FP (FLW) ─────────────────────────────────────────────────
        7'b0000111: begin
          if (funct3 == 3'b010) begin
            dec.fu_class     = FU_LSU_AGU;
            dec.op           = UOP_FLW;
            dec.dst          = '{valid: 1'b1, domain: REG_FP, arch: rd};
            dec.src0         = '{kind: SRC_INT_REG, arch: rs1};
            dec.imm_kind     = IMM_I;
            dec.imm          = imm_i;
            dec.alloc_lq     = 1'b1;
            dec.mem.is_load  = 1'b1;
            dec.mem.is_fp    = 1'b1;
            dec.mem.size     = MEM_WORD;
            dec.mem.load_ext = LOAD_UNSIGNED;
          end else begin
            dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
          end
        end

        // ── STORE-FP (FSW) ────────────────────────────────────────────────
        7'b0100111: begin
          if (funct3 == 3'b010) begin
            dec.fu_class     = FU_LSU_AGU;
            dec.op           = UOP_FSW;
            dec.src0         = '{kind: SRC_INT_REG, arch: rs1};
            dec.src1         = '{kind: SRC_FP_REG, arch: rs2};
            dec.imm_kind     = IMM_S;
            dec.imm          = imm_s;
            dec.alloc_sq     = 1'b1;
            dec.mem.is_store = 1'b1;
            dec.mem.is_fp    = 1'b1;
            dec.mem.size     = MEM_WORD;
          end else begin
            dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
          end
        end

        // ── FMADD.S ───────────────────────────────────────────────────────
        7'b1000011: begin
          dec.fu_class = FU_FP_FMA;
          dec.op       = UOP_FMADD_S;
          dec.dst      = '{valid: 1'b1, domain: REG_FP, arch: rd};
          dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
          dec.src1     = '{kind: SRC_FP_REG, arch: rs2};
          dec.src2     = '{kind: SRC_FP_REG, arch: rs3};
          dec.fp       = '{valid: 1'b1, uses_rm: 1'b1, rm: fp_rm_e'(funct3), may_set_flags: 1'b1};
        end

        // ── FMSUB.S ───────────────────────────────────────────────────────
        7'b1000111: begin
          dec.fu_class = FU_FP_FMA;
          dec.op       = UOP_FMSUB_S;
          dec.dst      = '{valid: 1'b1, domain: REG_FP, arch: rd};
          dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
          dec.src1     = '{kind: SRC_FP_REG, arch: rs2};
          dec.src2     = '{kind: SRC_FP_REG, arch: rs3};
          dec.fp       = '{valid: 1'b1, uses_rm: 1'b1, rm: fp_rm_e'(funct3), may_set_flags: 1'b1};
        end

        // ── FNMSUB.S ──────────────────────────────────────────────────────
        7'b1001011: begin
          dec.fu_class = FU_FP_FMA;
          dec.op       = UOP_FNMSUB_S;
          dec.dst      = '{valid: 1'b1, domain: REG_FP, arch: rd};
          dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
          dec.src1     = '{kind: SRC_FP_REG, arch: rs2};
          dec.src2     = '{kind: SRC_FP_REG, arch: rs3};
          dec.fp       = '{valid: 1'b1, uses_rm: 1'b1, rm: fp_rm_e'(funct3), may_set_flags: 1'b1};
        end

        // ── FNMADD.S ──────────────────────────────────────────────────────
        7'b1001111: begin
          dec.fu_class = FU_FP_FMA;
          dec.op       = UOP_FNMADD_S;
          dec.dst      = '{valid: 1'b1, domain: REG_FP, arch: rd};
          dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
          dec.src1     = '{kind: SRC_FP_REG, arch: rs2};
          dec.src2     = '{kind: SRC_FP_REG, arch: rs3};
          dec.fp       = '{valid: 1'b1, uses_rm: 1'b1, rm: fp_rm_e'(funct3), may_set_flags: 1'b1};
        end

        // ── OP-FP (FADD, FSUB, FMUL, FDIV, FSQRT, FSGNJ, FMIN, FCVT, FMV, FEQ...) ──
        7'b1010011: begin
          case (funct7)
            7'b0000000: begin // FADD.S
              dec.fu_class = FU_FP_ADD;
              dec.op       = UOP_FADD_S;
              dec.dst      = '{valid: 1'b1, domain: REG_FP, arch: rd};
              dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
              dec.src1     = '{kind: SRC_FP_REG, arch: rs2};
              dec.fp       = '{valid: 1'b1, uses_rm: 1'b1, rm: fp_rm_e'(funct3), may_set_flags: 1'b1};
            end

            7'b0000100: begin // FSUB.S
              dec.fu_class = FU_FP_ADD;
              dec.op       = UOP_FSUB_S;
              dec.dst      = '{valid: 1'b1, domain: REG_FP, arch: rd};
              dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
              dec.src1     = '{kind: SRC_FP_REG, arch: rs2};
              dec.fp       = '{valid: 1'b1, uses_rm: 1'b1, rm: fp_rm_e'(funct3), may_set_flags: 1'b1};
            end

            7'b0001000: begin // FMUL.S
              dec.fu_class = FU_FP_MUL;
              dec.op       = UOP_FMUL_S;
              dec.dst      = '{valid: 1'b1, domain: REG_FP, arch: rd};
              dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
              dec.src1     = '{kind: SRC_FP_REG, arch: rs2};
              dec.fp       = '{valid: 1'b1, uses_rm: 1'b1, rm: fp_rm_e'(funct3), may_set_flags: 1'b1};
            end

            7'b0001100: begin // FDIV.S
              dec.fu_class = FU_FP_DIVSQRT;
              dec.op       = UOP_FDIV_S;
              dec.dst      = '{valid: 1'b1, domain: REG_FP, arch: rd};
              dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
              dec.src1     = '{kind: SRC_FP_REG, arch: rs2};
              dec.fp       = '{valid: 1'b1, uses_rm: 1'b1, rm: fp_rm_e'(funct3), may_set_flags: 1'b1};
            end

            7'b0101100: begin // FSQRT.S (rs2 must be 0)
              if (rs2 == 5'd0) begin
                dec.fu_class = FU_FP_DIVSQRT;
                dec.op       = UOP_FSQRT_S;
                dec.dst      = '{valid: 1'b1, domain: REG_FP, arch: rd};
                dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
                dec.fp       = '{valid: 1'b1, uses_rm: 1'b1, rm: fp_rm_e'(funct3), may_set_flags: 1'b1};
              end else begin
                dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
              end
            end

            7'b0010000: begin // FSGNJ.S, FSGNJN.S, FSGNJX.S
              dec.fu_class = FU_FP_MISC;
              dec.dst      = '{valid: 1'b1, domain: REG_FP, arch: rd};
              dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
              dec.src1     = '{kind: SRC_FP_REG, arch: rs2};
              dec.fp       = '{valid: 1'b1, uses_rm: 1'b0, rm: RM_RNE, may_set_flags: 1'b0};
              case (funct3)
                3'b000: dec.op = UOP_FSGNJ_S;
                3'b001: dec.op = UOP_FSGNJN_S;
                3'b010: dec.op = UOP_FSGNJX_S;
                default: dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
              endcase
            end

            7'b0010100: begin // FMIN.S, FMAX.S
              dec.fu_class = FU_FP_MISC;
              dec.dst      = '{valid: 1'b1, domain: REG_FP, arch: rd};
              dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
              dec.src1     = '{kind: SRC_FP_REG, arch: rs2};
              dec.fp       = '{valid: 1'b1, uses_rm: 1'b0, rm: RM_RNE, may_set_flags: 1'b1};
              case (funct3)
                3'b000: dec.op = UOP_FMIN_S;
                3'b001: dec.op = UOP_FMAX_S;
                default: dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
              endcase
            end

            7'b1100000: begin // FCVT.W.S, FCVT.WU.S (FP -> INT)
              dec.fu_class = FU_FP_CONV;
              dec.dst      = '{valid: 1'b1, domain: REG_INT, arch: rd};
              dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
              dec.fp       = '{valid: 1'b1, uses_rm: 1'b1, rm: fp_rm_e'(funct3), may_set_flags: 1'b1};
              if (rs2 == 5'b00000)      dec.op = UOP_FCVT_W_S;
              else if (rs2 == 5'b00001) dec.op = UOP_FCVT_WU_S;
              else dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
            end

            7'b1110000: begin // FMV.X.W, FCLASS.S (FP -> INT)
              if (rs2 == 5'd0) begin
                dec.fu_class = FU_FP_MISC;
                dec.dst      = '{valid: 1'b1, domain: REG_INT, arch: rd};
                dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
                dec.fp       = '{valid: 1'b1, uses_rm: 1'b0, rm: RM_RNE, may_set_flags: 1'b0};
                if (funct3 == 3'b000)      dec.op = UOP_FMV_X_W;
                else if (funct3 == 3'b001) dec.op = UOP_FCLASS_S;
                else dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
              end else begin
                dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
              end
            end

            7'b1010000: begin // FEQ.S, FLT.S, FLE.S (FP -> INT)
              dec.fu_class = FU_FP_MISC;
              dec.dst      = '{valid: 1'b1, domain: REG_INT, arch: rd};
              dec.src0     = '{kind: SRC_FP_REG, arch: rs1};
              dec.src1     = '{kind: SRC_FP_REG, arch: rs2};
              dec.fp       = '{valid: 1'b1, uses_rm: 1'b0, rm: RM_RNE, may_set_flags: 1'b1};
              case (funct3)
                3'b010: dec.op = UOP_FEQ_S;
                3'b001: dec.op = UOP_FLT_S;
                3'b000: dec.op = UOP_FLE_S;
                default: dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
              endcase
            end

            7'b1101000: begin // FCVT.S.W, FCVT.S.WU (INT -> FP)
              dec.fu_class = FU_FP_CONV;
              dec.dst      = '{valid: 1'b1, domain: REG_FP, arch: rd};
              dec.src0     = '{kind: SRC_INT_REG, arch: rs1};
              dec.fp       = '{valid: 1'b1, uses_rm: 1'b1, rm: fp_rm_e'(funct3), may_set_flags: 1'b1};
              if (rs2 == 5'b00000)      dec.op = UOP_FCVT_S_W;
              else if (rs2 == 5'b00001) dec.op = UOP_FCVT_S_WU;
              else dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
            end

            7'b1111000: begin // FMV.W.X (INT -> FP)
              if (rs2 == 5'd0 && funct3 == 3'b000) begin
                dec.fu_class = FU_FP_MISC;
                dec.op       = UOP_FMV_W_X;
                dec.dst      = '{valid: 1'b1, domain: REG_FP, arch: rd};
                dec.src0     = '{kind: SRC_INT_REG, arch: rs1};
                dec.fp       = '{valid: 1'b1, uses_rm: 1'b0, rm: RM_RNE, may_set_flags: 1'b0};
              end else begin
                dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
              end
            end

            default: dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
          endcase
        end

        // ── SYSTEM & CSR (Zicsr) ──────────────────────────────────────────
        7'b1110011: begin
          dec.fu_class          = FU_CSR_SERIAL;
          dec.serializing       = 1'b1;
          dec.requires_rob_head = 1'b1;
          if (funct3 == 3'b000) begin
            // Non-CSR system instructions
            case (insn[31:20])
              12'h000: begin dec.op = UOP_ECALL;  dec.exception = '{valid: 1'b1, cause: EXC_ECALL_M, tval: 32'd0}; end
              12'h001: begin dec.op = UOP_EBREAK; dec.exception = '{valid: 1'b1, cause: EXC_BREAKPOINT, tval: 32'd0}; end
              12'h302: begin dec.op = UOP_MRET; end
              12'h105: begin dec.op = UOP_ADDI; end // WFI treated as NOP in simulation
              default: dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
            endcase
          end else begin
            // Zicsr instructions
            dec.dst              = '{valid: (rd != 5'd0), domain: REG_INT, arch: rd};
            dec.csr.valid        = 1'b1;
            dec.csr.addr         = insn[31:20];
            dec.csr.read_enable  = (rd != 5'd0);
            dec.csr.write_enable = (funct3[1:0] == 2'b01) || (rs1 != 5'd0);
            dec.csr.use_zimm     = funct3[2];

            if (funct3[2]) begin
              dec.src0     = '{kind: SRC_CSR_ZIMM, arch: 5'd0};
              dec.imm_kind = IMM_CSR_ZIMM;
              dec.imm      = imm_zimm;
            end else begin
              dec.src0     = '{kind: SRC_INT_REG, arch: rs1};
            end

            case (funct3[1:0])
              2'b01: begin dec.op = UOP_CSRRW; dec.csr.cmd = CSR_WRITE; end
              2'b10: begin dec.op = UOP_CSRRS; dec.csr.cmd = CSR_SET;   end
              2'b11: begin dec.op = UOP_CSRRC; dec.csr.cmd = CSR_CLEAR; end
              default: dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
            endcase
          end
        end

        // ── FENCE / FENCE.I ───────────────────────────────────────────────
        7'b0001111: begin
          dec.op                = UOP_FENCE;
          dec.fu_class          = FU_INT_ALU;
          dec.serializing       = 1'b1;
          dec.requires_rob_head = 1'b1;
        end

        default: begin
          dec.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: insn};
        end
      endcase
    end
  end

  // Output to Rename Stage
  assign uop_valid = !iq_empty && (core_state == CORE_RUN);
  assign uop_out   = dec;

endmodule
