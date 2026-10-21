// rv32_ooo_fp_simple.sv — Dedicated Simple Floating-Point Execution Unit
// Implements low-complexity RV32F instructions:
//   FMV.X.W, FMV.W.X, FSGNJ.S, FSGNJN.S, FSGNJX.S,
//   FEQ.S, FLT.S, FLE.S, FCLASS.S, FMIN.S, FMAX.S
// Features independent registered holding output stage to isolate from heavy arithmetic.
// architecture_spec.md §23, §24 | uop_spec.md §6, §13, §18–§19

module rv32_ooo_fp_simple
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic        clk,
  input  logic        rst,          // synchronous active-high
  input  logic        flush_valid,  // pipeline flush

  // Execution request from FP EX0
  input  logic        issue_valid,
  input  exec_req_t   issue_req,
  output logic        issue_ready,

  // Registered completion packet to completion arbiter
  output logic        cmp_valid,
  output completion_t cmp_data,
  input  logic        cmp_ready
);

  wire [31:0] op0 = issue_req.operand0;
  wire [31:0] op1 = issue_req.operand1;

  localparam logic [31:0] CANONICAL_NAN = 32'h7FC0_0000;

  // Helper classification functions
  function automatic logic is_nan(input logic [31:0] f);
    return (f[30:23] == 8'hFF) && (f[22:0] != 23'd0);
  endfunction

  function automatic logic is_snan(input logic [31:0] f);
    return (f[30:23] == 8'hFF) && (f[22] == 1'b0) && (f[21:0] != 22'd0);
  endfunction

  function automatic logic is_qnan(input logic [31:0] f);
    return (f[30:23] == 8'hFF) && (f[22] == 1'b1);
  endfunction

  function automatic logic is_inf(input logic [31:0] f);
    return (f[30:23] == 8'hFF) && (f[22:0] == 23'd0);
  endfunction

  function automatic logic is_zero(input logic [31:0] f);
    return (f[30:0] == 31'd0);
  endfunction

  function automatic logic is_subnormal(input logic [31:0] f);
    return (f[30:23] == 8'd0) && (f[22:0] != 23'd0);
  endfunction

  // =========================================================================
  // Computation Datapath
  // =========================================================================

  logic [31:0] res_data;
  reg_domain_e res_domain;
  fp_flags_t   res_flags;

  always_comb begin
    res_data   = 32'd0;
    res_domain = REG_FP;
    res_flags  = '0;

    case (issue_req.uop.op)
      // ── FMV.X.W ─────────────────────────────────────────────────────────
      UOP_FMV_X_W: begin
        res_data   = op0;
        res_domain = REG_INT;
      end

      // ── FMV.W.X ─────────────────────────────────────────────────────────
      UOP_FMV_W_X: begin
        res_data   = op0;
        res_domain = REG_FP;
      end

      // ── FSGNJ.S, FSGNJN.S, FSGNJX.S ──────────────────────────────────────
      UOP_FSGNJ_S: begin
        res_data   = {op1[31], op0[30:0]};
        res_domain = REG_FP;
      end

      UOP_FSGNJN_S: begin
        res_data   = {~op1[31], op0[30:0]};
        res_domain = REG_FP;
      end

      UOP_FSGNJX_S: begin
        res_data   = {op0[31] ^ op1[31], op0[30:0]};
        res_domain = REG_FP;
      end

      // ── FMIN.S & FMAX.S ──────────────────────────────────────────────────
      UOP_FMIN_S, UOP_FMAX_S: begin : blk_fminmax
        logic is_min;
        logic op0_less;
        is_min = (issue_req.uop.op == UOP_FMIN_S);
        res_domain = REG_FP;

        if (is_snan(op0) || is_snan(op1)) begin
          res_flags.nv = 1'b1;
        end

        if (is_nan(op0) && is_nan(op1)) begin
          res_data = CANONICAL_NAN;
        end else if (is_nan(op0)) begin
          res_data = op1;
        end else if (is_nan(op1)) begin
          res_data = op0;
        end else if (is_zero(op0) && is_zero(op1)) begin
          // -0.0 is considered smaller than +0.0
          if (op0[31] != op1[31]) begin
            res_data = is_min ? (op0[31] ? op0 : op1) : (op0[31] ? op1 : op0);
          end else begin
            res_data = op0;
          end
        end else begin
          if (op0[31] != op1[31]) begin
            op0_less = op0[31]; // negative is smaller
          end else if (op0[31]) begin
            op0_less = (op0[30:0] > op1[30:0]); // both neg
          end else begin
            op0_less = (op0[30:0] < op1[30:0]); // both pos
          end

          if (is_min) begin
            res_data = op0_less ? op0 : op1;
          end else begin
            res_data = op0_less ? op1 : op0;
          end
        end
      end

      // ── FEQ.S, FLT.S, FLE.S ──────────────────────────────────────────────
      UOP_FEQ_S: begin
        res_domain = REG_INT;
        if (is_snan(op0) || is_snan(op1)) res_flags.nv = 1'b1;
        if (is_nan(op0) || is_nan(op1)) begin
          res_data = 32'd0;
        end else if (is_zero(op0) && is_zero(op1)) begin
          res_data = 32'd1; // +0.0 == -0.0
        end else begin
          res_data = (op0 == op1) ? 32'd1 : 32'd0;
        end
      end

      UOP_FLT_S: begin
        res_domain = REG_INT;
        if (is_nan(op0) || is_nan(op1)) begin
          res_flags.nv = 1'b1;
          res_data     = 32'd0;
        end else if (is_zero(op0) && is_zero(op1)) begin
          res_data = 32'd0;
        end else if (op0[31] != op1[31]) begin
          res_data = op0[31] ? 32'd1 : 32'd0;
        end else if (op0[31]) begin
          res_data = (op0[30:0] > op1[30:0]) ? 32'd1 : 32'd0; // both neg
        end else begin
          res_data = (op0[30:0] < op1[30:0]) ? 32'd1 : 32'd0; // both pos
        end
      end

      UOP_FLE_S: begin
        res_domain = REG_INT;
        if (is_nan(op0) || is_nan(op1)) begin
          res_flags.nv = 1'b1;
          res_data     = 32'd0;
        end else if (is_zero(op0) && is_zero(op1)) begin
          res_data = 32'd1;
        end else if (op0 == op1) begin
          res_data = 32'd1;
        end else if (op0[31] != op1[31]) begin
          res_data = op0[31] ? 32'd1 : 32'd0;
        end else if (op0[31]) begin
          res_data = (op0[30:0] >= op1[30:0]) ? 32'd1 : 32'd0; // both neg
        end else begin
          res_data = (op0[30:0] <= op1[30:0]) ? 32'd1 : 32'd0; // both pos
        end
      end

      // ── FCLASS.S ─────────────────────────────────────────────────────────
      UOP_FCLASS_S: begin
        res_domain = REG_INT;
        res_data   = 32'd0;
        if (is_snan(op0))                       res_data[8] = 1'b1; // signaling NaN
        else if (is_qnan(op0))                  res_data[9] = 1'b1; // quiet NaN
        else if (op0[31] && is_inf(op0))        res_data[0] = 1'b1; // -inf
        else if (op0[31] && is_subnormal(op0))  res_data[2] = 1'b1; // -subnormal
        else if (op0[31] && is_zero(op0))       res_data[3] = 1'b1; // -0.0
        else if (op0[31])                       res_data[1] = 1'b1; // -normal
        else if (!op0[31] && is_zero(op0))      res_data[4] = 1'b1; // +0.0
        else if (!op0[31] && is_subnormal(op0)) res_data[5] = 1'b1; // +subnormal
        else if (!op0[31] && is_inf(op0))       res_data[7] = 1'b1; // +inf
        else                                    res_data[6] = 1'b1; // +normal
      end

      default: begin
        res_data   = 32'd0;
        res_domain = REG_FP;
        res_flags  = '0;
      end
    endcase
  end

  // =========================================================================
  // Combinational Completion Packet Formation
  // =========================================================================

  completion_t comb_cmp;

  always_comb begin
    comb_cmp = '0;
    if (issue_valid) begin
      comb_cmp.valid          = 1'b1;
      comb_cmp.rob_tag        = issue_req.uop.rob_tag;
      comb_cmp.result_valid   = issue_req.uop.dst.valid;
      comb_cmp.result_domain  = res_domain;
      comb_cmp.result_phys    = issue_req.uop.dst.new_phys;
      comb_cmp.result_data    = res_data;
      comb_cmp.fp_flags_valid = 1'b1;
      comb_cmp.fp_flags       = res_flags;
      comb_cmp.exception      = issue_req.uop.exception;
    end
  end

  // =========================================================================
  // Independent Registered Holding Output Stage
  // =========================================================================

  logic        holding_valid;
  completion_t holding_data;

  wire can_accept = !holding_valid || cmp_ready;
  assign issue_ready = can_accept;

  always_ff @(posedge clk) begin
    if (rst || flush_valid) begin
      holding_valid <= 1'b0;
      holding_data  <= '0;
    end else begin
      if (can_accept) begin
        holding_valid <= issue_valid;
        if (issue_valid) begin
          holding_data <= comb_cmp;
        end else begin
          holding_data <= '0;
        end
      end
    end
  end

  assign cmp_valid = holding_valid;
  assign cmp_data  = holding_data;

endmodule
