// rv32_ooo_fp_execute.sv — IEEE 754-2008 Single-Precision Floating-Point Execution Cluster
// Implements FADD, FSUB, FMUL, FDIV, FSQRT, FMADD, FMSUB, FNMSUB, FNMADD, FSGNJ, FMIN, FMAX,
// FCVT, FMV, FEQ, FLT, FLE, FCLASS with all 5 rounding modes (RNE, RTZ, RDN, RUP, RMM) & accrued flags (NV, DZ, OF, UF, NX)
// architecture_spec.md §23, §24 | uop_spec.md §6, §13, §18–§19

module rv32_ooo_fp_execute
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic        clk,
  input  logic        rst,          // synchronous active-high

  input  core_state_e core_state,

  // Execution request from FP IQ (post PRF read)
  input  logic       issue_valid,
  input  exec_req_t  issue_req,
  output logic       issue_ready,

  // Completion packet to writeback arbiter / ROB
  output completion_t fp_cmp
);

  assign issue_ready = 1'b1;

  wire [31:0] op0 = issue_req.operand0;
  wire [31:0] op1 = issue_req.operand1;
  wire [31:0] op2 = issue_req.operand2;

  wire fp_rm_e rm = issue_req.uop.fp.rm;

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

  function automatic int msb_index_32(input logic [31:0] val);
    int res;
    res = 0;
    for (int i = 0; i < 32; i++) begin
      if (val[i]) res = i;
    end
    return res;
  endfunction

  // Unpack single-precision float into (sign, un-biased exponent, 24-bit mantissa with explicit leading bit at bit 23)
  function automatic void unpack_f32(
    input  logic [31:0] f,
    output logic        s,
    output int          e,
    output logic [23:0] m
  );
    s = f[31];
    if (f[30:23] == 8'd0) begin
      e = -126;
      m = {1'b0, f[22:0]}; // subnormal
    end else begin
      e = int'(f[30:23]) - 127;
      m = {1'b1, f[22:0]}; // normal
    end
  endfunction

  // Standard IEEE 754 Single-Precision Rounding & Packing
  // Input: sign, base exponent, 48-bit mantissa (unit bit 1.0 is at bit 26,
  //   bits 25..3 are the 23 fraction bits, bit 2=G, 1=R, 0=S)
  // Normalization uses barrel-shifters (priority-encode MSB, shift in one step)
  // to avoid O(2^N) process-tree depth from iterative for-loops.
  function automatic void round_and_pack(
    input  logic        sign,
    input  int          exp,
    input  logic [47:0] mantissa,
    input  fp_rm_e      rmode,
    output logic [31:0] out_f,
    output fp_flags_t   flags
  );
    int norm_exp;
    logic [47:0] norm_mant;
    logic guard, round_bit, sticky;
    logic round_up;
    logic [24:0] significand;
    int final_exp;
    // barrel-shift temporaries
    logic [5:0] msb_pos;
    int         shift_amt;
    int         max_lshift;
    logic [47:0] sticky_mask;

    // ─── Initialize all locals ────────────────────────────────────────────
    flags       = '0;
    norm_exp    = exp;
    norm_mant   = mantissa;
    sticky      = 1'b0;
    guard       = 1'b0;
    round_bit   = 1'b0;
    round_up    = 1'b0;
    significand = '0;
    final_exp   = 0;
    out_f       = '0;
    msb_pos     = '0;
    shift_amt   = 0;
    max_lshift  = 0;
    sticky_mask = '0;

    if (norm_mant == 48'd0) begin
      out_f = {sign, 31'd0};
    end else begin
      // ─── 1. Priority-encode MSB position (bit 0..47) ─────────────────────
      // Combinational priority encoder — O(log₂48) mux depth, not O(48).
      if      (norm_mant[47]) msb_pos = 6'd47;
      else if (norm_mant[46]) msb_pos = 6'd46;
      else if (norm_mant[45]) msb_pos = 6'd45;
      else if (norm_mant[44]) msb_pos = 6'd44;
      else if (norm_mant[43]) msb_pos = 6'd43;
      else if (norm_mant[42]) msb_pos = 6'd42;
      else if (norm_mant[41]) msb_pos = 6'd41;
      else if (norm_mant[40]) msb_pos = 6'd40;
      else if (norm_mant[39]) msb_pos = 6'd39;
      else if (norm_mant[38]) msb_pos = 6'd38;
      else if (norm_mant[37]) msb_pos = 6'd37;
      else if (norm_mant[36]) msb_pos = 6'd36;
      else if (norm_mant[35]) msb_pos = 6'd35;
      else if (norm_mant[34]) msb_pos = 6'd34;
      else if (norm_mant[33]) msb_pos = 6'd33;
      else if (norm_mant[32]) msb_pos = 6'd32;
      else if (norm_mant[31]) msb_pos = 6'd31;
      else if (norm_mant[30]) msb_pos = 6'd30;
      else if (norm_mant[29]) msb_pos = 6'd29;
      else if (norm_mant[28]) msb_pos = 6'd28;
      else if (norm_mant[27]) msb_pos = 6'd27;
      else if (norm_mant[26]) msb_pos = 6'd26;
      else if (norm_mant[25]) msb_pos = 6'd25;
      else if (norm_mant[24]) msb_pos = 6'd24;
      else if (norm_mant[23]) msb_pos = 6'd23;
      else if (norm_mant[22]) msb_pos = 6'd22;
      else if (norm_mant[21]) msb_pos = 6'd21;
      else if (norm_mant[20]) msb_pos = 6'd20;
      else if (norm_mant[19]) msb_pos = 6'd19;
      else if (norm_mant[18]) msb_pos = 6'd18;
      else if (norm_mant[17]) msb_pos = 6'd17;
      else if (norm_mant[16]) msb_pos = 6'd16;
      else if (norm_mant[15]) msb_pos = 6'd15;
      else if (norm_mant[14]) msb_pos = 6'd14;
      else if (norm_mant[13]) msb_pos = 6'd13;
      else if (norm_mant[12]) msb_pos = 6'd12;
      else if (norm_mant[11]) msb_pos = 6'd11;
      else if (norm_mant[10]) msb_pos = 6'd10;
      else if (norm_mant[9])  msb_pos = 6'd9;
      else if (norm_mant[8])  msb_pos = 6'd8;
      else if (norm_mant[7])  msb_pos = 6'd7;
      else if (norm_mant[6])  msb_pos = 6'd6;
      else if (norm_mant[5])  msb_pos = 6'd5;
      else if (norm_mant[4])  msb_pos = 6'd4;
      else if (norm_mant[3])  msb_pos = 6'd3;
      else if (norm_mant[2])  msb_pos = 6'd2;
      else if (norm_mant[1])  msb_pos = 6'd1;
      else                    msb_pos = 6'd0;

      // shift_amt > 0 → right (overflow); shift_amt < 0 → left (underflow)
      shift_amt = int'(msb_pos) - 26;

      // ─── 2. Right normalization: barrel shift right ───────────────────────
      if (shift_amt > 0) begin
        // Collect all sticky bits that shift out below the rounding guard
        sticky_mask = (shift_amt >= 48) ? '1 : ((48'd1 << shift_amt) - 48'd1);
        sticky      = |(norm_mant & sticky_mask);
        norm_mant   = (shift_amt >= 48) ? '0 : (norm_mant >> shift_amt);
        norm_exp    = norm_exp + shift_amt;
      end

      // ─── 3. Left normalization: barrel shift left (exponent-limited) ──────
      if (shift_amt < 0) begin
        // How far left can we shift before exponent underflows past -126?
        max_lshift = norm_exp + 126;   // positive = we have room
        if (max_lshift <= 0) begin
          // Already at subnormal floor; adjust exp/mant accordingly
          // shift right by the deficit to represent subnormal
          int sub_rshift = -(norm_exp + 126);
          sticky_mask    = (sub_rshift >= 48) ? '1 : ((48'd1 << sub_rshift) - 48'd1);
          sticky         = |(norm_mant & sticky_mask);
          norm_mant      = (sub_rshift >= 48) ? '0 : (norm_mant >> sub_rshift);
          norm_exp       = -126;
        end else begin
          int lshift = (-shift_amt < max_lshift) ? -shift_amt : max_lshift;
          norm_mant  = norm_mant << lshift;
          norm_exp   = norm_exp - lshift;
        end
      end

      // ─── 4. Extract rounding bits and determine increment ─────────────────
      guard     = norm_mant[2];
      round_bit = norm_mant[1];
      sticky    = sticky | norm_mant[0];

      round_up = 1'b0;
      case (rmode)
        RM_RNE: round_up = guard && (round_bit || sticky || norm_mant[3]);
        RM_RTZ: round_up = 1'b0;
        RM_RDN: round_up = sign && (guard || round_bit || sticky);
        RM_RUP: round_up = !sign && (guard || round_bit || sticky);
        RM_RMM: round_up = guard;
        default: round_up = guard && (round_bit || sticky || norm_mant[3]);
      endcase

      if (guard || round_bit || sticky) begin
        flags.nx = 1'b1; // Inexact
      end

      significand = {1'b0, norm_mant[26:3]} + (round_up ? 25'd1 : 25'd0);
      final_exp   = norm_exp;

      // Handle carry from rounding (e.g. 1.111... + 1 = 2.0)
      if (significand[24]) begin
        significand = {1'b0, significand[24:1]};
        final_exp   = final_exp + 1;
      end

      // Exponent overflow / underflow checks
      if (final_exp >= 128) begin
        flags.of = 1'b1;
        flags.nx = 1'b1;
        case (rmode)
          RM_RNE, RM_RMM: out_f = {sign, 8'hFF, 23'd0}; // Infinity
          RM_RTZ:         out_f = {sign, 8'hFE, 23'h7FFFFF}; // Max normal
          RM_RDN:         out_f = sign ? {1'b1, 8'hFF, 23'd0} : {1'b0, 8'hFE, 23'h7FFFFF};
          RM_RUP:         out_f = sign ? {1'b1, 8'hFE, 23'h7FFFFF} : {1'b0, 8'hFF, 23'd0};
          default:        out_f = {sign, 8'hFF, 23'd0};
        endcase
      end else if (final_exp < -126) begin
        flags.uf = 1'b1;
        flags.nx = 1'b1;
        out_f = {sign, 31'd0};
      end else begin
        out_f = {sign, 8'(final_exp + 127), significand[22:0]};
      end
    end
  endfunction

  // =========================================================================
  // Computation Datapaths
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
        logic is_min = (issue_req.uop.op == UOP_FMIN_S);
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
          logic op0_less;
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

      // ── FCVT.W.S & FCVT.WU.S ─────────────────────────────────────────────
      UOP_FCVT_W_S: begin : blk_fcvt_w
        logic s0; int e0; logic [23:0] m0;
        int int_val;
        logic round_up;
        s0 = 1'b0; e0 = 0; m0 = '0; int_val = 0; round_up = 1'b0;
        res_domain = REG_INT;

        if (is_nan(op0)) begin
          res_flags.nv = 1'b1;
          res_data     = 32'h7FFF_FFFF;
        end else if (is_inf(op0)) begin
          res_flags.nv = 1'b1;
          res_data     = op0[31] ? 32'h8000_0000 : 32'h7FFF_FFFF;
        end else begin
          unpack_f32(op0, s0, e0, m0);
          if (e0 < -1) begin
            res_flags.nx = |op0[30:0];
            res_data     = (rm == RM_RDN && s0 && |op0[30:0]) ? -32'd1 :
                           (rm == RM_RUP && !s0 && |op0[30:0]) ? 32'd1 : 32'd0;
          end else if (e0 > 30) begin
            if (e0 == 31 && s0 && m0[22:0] == 23'd0) begin
              res_data = 32'h8000_0000;
            end else begin
              res_flags.nv = 1'b1;
              res_data     = s0 ? 32'h8000_0000 : 32'h7FFF_FFFF;
            end
          end else begin
            if (e0 >= 23) begin
              int_val = int'(m0[23:0]) << (e0 - 23);
            end else begin
              int shift = 23 - e0;
              logic [23:0] mask = (shift > 1) ? ((24'd1 << (shift - 1)) - 24'd1) : 24'd0;
              logic [23:0] shifted_m0 = m0 >> (shift - 1);
              logic guard = shifted_m0[0];
              logic sticky = |(m0 & mask);
              int_val = int'(m0[23:0]) >> shift;

              round_up = 1'b0;
              case (rm)
                RM_RNE: round_up = guard && (sticky || int_val[0]);
                RM_RTZ: round_up = 1'b0;
                RM_RDN: round_up = s0 && (guard || sticky);
                RM_RUP: round_up = !s0 && (guard || sticky);
                RM_RMM: round_up = guard;
                default: round_up = guard && (sticky || int_val[0]);
              endcase

              if (guard || sticky) res_flags.nx = 1'b1;
              if (round_up) int_val = int_val + 1;
            end
            res_data = s0 ? -int_val : int_val;
          end
        end
      end

      UOP_FCVT_WU_S: begin : blk_fcvt_wu
        logic s0; int e0; logic [23:0] m0;
        int uint_val;
        logic round_up;
        s0 = 1'b0; e0 = 0; m0 = '0; uint_val = 0; round_up = 1'b0;
        res_domain = REG_INT;

        if (is_nan(op0) || (op0[31] && !is_zero(op0))) begin
          res_flags.nv = 1'b1;
          res_data     = is_nan(op0) ? 32'hFFFF_FFFF : 32'd0;
        end else if (is_inf(op0)) begin
          res_flags.nv = 1'b1;
          res_data     = 32'hFFFF_FFFF;
        end else begin
          unpack_f32(op0, s0, e0, m0);
          if (e0 < 0) begin
            res_flags.nx = |op0[30:0];
            res_data     = (rm == RM_RUP && !s0 && |op0[30:0]) ? 32'd1 : 32'd0;
          end else if (e0 >= 32) begin
            res_flags.nv = 1'b1;
            res_data     = 32'hFFFF_FFFF;
          end else begin
            if (e0 >= 23) begin
              uint_val = int'(m0[23:0]) << (e0 - 23);
            end else begin
              int shift = 23 - e0;
              logic [23:0] mask = (shift > 1) ? ((24'd1 << (shift - 1)) - 24'd1) : 24'd0;
              logic [23:0] shifted_m0 = m0 >> (shift - 1);
              logic guard = shifted_m0[0];
              logic sticky = |(m0 & mask);
              uint_val = int'(m0[23:0]) >> shift;

              round_up = 1'b0;
              case (rm)
                RM_RNE: round_up = guard && (sticky || uint_val[0]);
                RM_RTZ: round_up = 1'b0;
                RM_RDN: round_up = 1'b0;
                RM_RUP: round_up = (guard || sticky);
                RM_RMM: round_up = guard;
                default: round_up = guard && (sticky || uint_val[0]);
              endcase

              if (guard || sticky) res_flags.nx = 1'b1;
              if (round_up) uint_val = uint_val + 1;
            end
            res_data = uint_val;
          end
        end
      end

      // ── FCVT.S.W & FCVT.S.WU ─────────────────────────────────────────────
      UOP_FCVT_S_W: begin : blk_fcvt_sw
        logic sign;
        logic [31:0] uval;
        int lz;
        logic [47:0] mant;
        sign = 1'b0; uval = '0; lz = 0; mant = '0;
        res_domain = REG_FP;

        if (op0 == 32'd0) begin
          res_data = 32'd0;
        end else begin
          sign = op0[31];
          uval = sign ? 32'(-int'(op0)) : op0;
          lz   = msb_index_32(uval); // e.g. 5 for 42, 31 for 0x80000000
          if (lz >= 26) begin
            int rshift = lz - 26;
            logic [31:0] rmask = (rshift > 0) ? ((32'd1 << rshift) - 32'd1) : 32'd0;
            mant = {16'd0, (uval >> rshift)} | {47'd0, |(uval & rmask)};
          end else begin
            mant = {16'd0, uval} << (26 - lz); // Align MSB to bit 26
          end
          round_and_pack(sign, lz, mant, rm, res_data, res_flags);
        end
      end

      UOP_FCVT_S_WU: begin : blk_fcvt_swu
        int lz;
        logic [47:0] mant;
        lz = 0; mant = '0;
        res_domain = REG_FP;

        if (op0 == 32'd0) begin
          res_data = 32'd0;
        end else begin
          lz = msb_index_32(op0);
          if (lz >= 26) begin
            int rshift = lz - 26;
            logic [31:0] rmask = (rshift > 0) ? ((32'd1 << rshift) - 32'd1) : 32'd0;
            mant = {16'd0, (op0 >> rshift)} | {47'd0, |(op0 & rmask)};
          end else begin
            mant = {16'd0, op0} << (26 - lz);
          end
          round_and_pack(1'b0, lz, mant, rm, res_data, res_flags);
        end
      end

      // ── FADD.S & FSUB.S ─────────────────────────────────────────────────
      UOP_FADD_S, UOP_FSUB_S: begin : blk_fadd
        logic [31:0] effective_op1;
        logic s0, s1; int e0, e1; logic [23:0] m0, m1;
        int exp_diff;
        logic [47:0] mant0, mant1;
        int base_exp;
        logic [47:0] sum_mant;
        logic res_sign;
        effective_op1 = '0; s0 = '0; s1 = '0; e0 = 0; e1 = 0; m0 = '0; m1 = '0;
        exp_diff = 0; mant0 = '0; mant1 = '0; base_exp = 0; sum_mant = '0; res_sign = 1'b0;

        res_domain = REG_FP;
        effective_op1 = (issue_req.uop.op == UOP_FSUB_S) ? {~op1[31], op1[30:0]} : op1;

        if (is_snan(op0) || is_snan(effective_op1)) begin
          res_flags.nv = 1'b1;
          res_data     = CANONICAL_NAN;
        end else if (is_nan(op0) || is_nan(effective_op1)) begin
          res_data     = CANONICAL_NAN;
        end else if (is_inf(op0) && is_inf(effective_op1)) begin
          if (op0[31] != effective_op1[31]) begin
            res_flags.nv = 1'b1;
            res_data     = CANONICAL_NAN; // +inf - +inf = NaN
          end else begin
            res_data = op0;
          end
        end else if (is_inf(op0)) begin
          res_data = op0;
        end else if (is_inf(effective_op1)) begin
          res_data = effective_op1;
        end else if (is_zero(op0) && is_zero(effective_op1)) begin
          res_sign = (op0[31] == effective_op1[31]) ? op0[31] : (rm == RM_RDN);
          res_data = {res_sign, 31'd0};
        end else begin
          unpack_f32(op0, s0, e0, m0);
          unpack_f32(effective_op1, s1, e1, m1);

          exp_diff = e0 - e1;
          mant0 = {21'd0, m0[23:0], 3'd0}; // Unit bit at 26
          mant1 = {21'd0, m1[23:0], 3'd0}; // Unit bit at 26

          if (exp_diff >= 0) begin
            base_exp = e0;
            if (exp_diff > 47) begin
              mant1 = {47'd0, |mant1};
            end else if (exp_diff > 0) begin
              logic [47:0] mask1 = (48'd1 << exp_diff) - 48'd1;
              mant1 = (mant1 >> exp_diff) | {47'd0, |(mant1 & mask1)};
            end
          end else begin
            int neg_diff = -exp_diff;
            base_exp = e1;
            if (neg_diff > 47) begin
              mant0 = {47'd0, |mant0};
            end else if (neg_diff > 0) begin
              logic [47:0] mask0 = (48'd1 << neg_diff) - 48'd1;
              mant0 = (mant0 >> neg_diff) | {47'd0, |(mant0 & mask0)};
            end
          end

          if (s0 == s1) begin
            res_sign = s0;
            sum_mant = mant0 + mant1;
          end else begin
            if (mant0 >= mant1) begin
              res_sign = s0;
              sum_mant = mant0 - mant1;
            end else begin
              res_sign = s1;
              sum_mant = mant1 - mant0;
            end
          end

          if (sum_mant == 48'd0) begin
            res_data = {(rm == RM_RDN), 31'd0};
          end else begin
            round_and_pack(res_sign, base_exp, sum_mant, rm, res_data, res_flags);
          end
        end
      end

      // ── FMUL.S ──────────────────────────────────────────────────────────
      UOP_FMUL_S: begin : blk_fmul
        logic sign_mul;
        logic s0, s1; int e0, e1; logic [23:0] m0, m1;
        logic [47:0] prod;
        logic [47:0] prod_mant;
        int prod_exp;
        sign_mul = 1'b0; s0 = '0; s1 = '0; e0 = 0; e1 = 0; m0 = '0; m1 = '0;
        prod = '0; prod_mant = '0; prod_exp = 0;

        res_domain = REG_FP;
        sign_mul   = op0[31] ^ op1[31];

        if (is_snan(op0) || is_snan(op1)) begin
          res_flags.nv = 1'b1;
          res_data     = CANONICAL_NAN;
        end else if (is_nan(op0) || is_nan(op1)) begin
          res_data = CANONICAL_NAN;
        end else if ((is_inf(op0) && is_zero(op1)) || (is_zero(op0) && is_inf(op1))) begin
          res_flags.nv = 1'b1;
          res_data     = CANONICAL_NAN; // 0 * inf = NaN
        end else if (is_inf(op0) || is_inf(op1)) begin
          res_data = {sign_mul, 8'hFF, 23'd0};
        end else if (is_zero(op0) || is_zero(op1)) begin
          res_data = {sign_mul, 31'd0};
        end else begin
          unpack_f32(op0, s0, e0, m0);
          unpack_f32(op1, s1, e1, m1);

          prod = 48'(m0[23:0]) * 48'(m1[23:0]); // Unit bit at 46
          prod_mant = {20'd0, prod[47:20]} | {47'd0, |prod[19:0]}; // Unit bit at 26
          prod_exp  = e0 + e1;

          round_and_pack(sign_mul, prod_exp, prod_mant, rm, res_data, res_flags);
        end
      end

      // ── FMA (FMADD, FMSUB, FNMSUB, FNMADD) ──────────────────────────────
      UOP_FMADD_S, UOP_FMSUB_S, UOP_FNMSUB_S, UOP_FNMADD_S: begin : blk_fma
        logic negate_prod, negate_c;
        logic [31:0] c_val;
        logic sign_prod;
        logic s0, s1, sc; int e0, e1, ec; logic [23:0] m0, m1, mc;
        logic [47:0] prod;
        int ep;
        int exp_diff;
        logic [71:0] fma_prod, fma_c, sum;
        logic [47:0] fma_mant;
        int base_exp;
        logic sign_final;
        negate_prod = 1'b0; negate_c = 1'b0; c_val = '0; sign_prod = 1'b0;
        s0 = '0; s1 = '0; sc = '0; e0 = 0; e1 = 0; ec = 0; m0 = '0; m1 = '0; mc = '0;
        prod = '0; ep = 0; exp_diff = 0; fma_prod = '0; fma_c = '0; sum = '0;
        fma_mant = '0; base_exp = 0; sign_final = 1'b0;

        res_domain  = REG_FP;
        negate_prod = (issue_req.uop.op == UOP_FNMSUB_S) || (issue_req.uop.op == UOP_FNMADD_S);
        negate_c    = (issue_req.uop.op == UOP_FMSUB_S)  || (issue_req.uop.op == UOP_FNMADD_S);

        c_val = op2;
        if (negate_c) c_val[31] = ~c_val[31];

        sign_prod = op0[31] ^ op1[31] ^ negate_prod;

        if (is_snan(op0) || is_snan(op1) || is_snan(c_val)) begin
          res_flags.nv = 1'b1;
          res_data     = CANONICAL_NAN;
        end else if (is_nan(op0) || is_nan(op1) || is_nan(c_val)) begin
          res_data = CANONICAL_NAN;
        end else if ((is_inf(op0) && is_zero(op1)) || (is_zero(op0) && is_inf(op1))) begin
          res_flags.nv = 1'b1;
          res_data     = CANONICAL_NAN;
        end else if (is_inf(op0) || is_inf(op1)) begin
          if (is_inf(c_val) && (sign_prod != c_val[31])) begin
            res_flags.nv = 1'b1;
            res_data     = CANONICAL_NAN; // inf - inf
          end else begin
            res_data = {sign_prod, 8'hFF, 23'd0};
          end
        end else if (is_inf(c_val)) begin
          res_data = c_val;
        end else begin
          unpack_f32(op0, s0, e0, m0);
          unpack_f32(op1, s1, e1, m1);
          unpack_f32(c_val, sc, ec, mc);

          prod = 48'(m0[23:0]) * 48'(m1[23:0]); // Unit bit at 46
          ep   = e0 + e1;

          exp_diff = ep - ec;
          fma_prod = {24'd0, prod};           // Unit bit at 46
          fma_c    = {25'd0, mc[23:0], 23'd0}; // Unit bit at 46

          if (exp_diff >= 0) begin
            base_exp = ep;
            fma_c = (exp_diff > 70) ? 72'd0 : (fma_c >> exp_diff);
          end else begin
            base_exp = ec;
            fma_prod = (-exp_diff > 70) ? 72'd0 : (fma_prod >> (-exp_diff));
          end

          if (sign_prod == sc) begin
            sign_final = sign_prod;
            sum = fma_prod + fma_c;
          end else begin
            if (fma_prod >= fma_c) begin
              sign_final = sign_prod;
              sum = fma_prod - fma_c;
            end else begin
              sign_final = sc;
              sum = fma_c - fma_prod;
            end
          end

          // Unit bit was at 46 of sum. Align to unit bit 26 (shift right by 20):
          fma_mant = {sum[67:20]} | {47'd0, |sum[19:0]};

          if (fma_mant == 48'd0) begin
            res_data = {(rm == RM_RDN), 31'd0};
          end else begin
            round_and_pack(sign_final, base_exp, fma_mant, rm, res_data, res_flags);
          end
        end
      end

      // ── FDIV.S ──────────────────────────────────────────────────────────
      UOP_FDIV_S: begin : blk_fdiv
        logic sign_div;
        logic s0, s1; int e0, e1; logic [23:0] m0, m1;
        logic [49:0] dividend;
        logic [49:0] div_res;
        logic [23:0] rem_res;
        logic [47:0] quotient;
        int exp_div;
        sign_div = 1'b0; s0 = '0; s1 = '0; e0 = 0; e1 = 0; m0 = '0; m1 = '0;
        dividend = '0; div_res = '0; rem_res = '0; quotient = '0; exp_div = 0;

        res_domain = REG_FP;
        sign_div   = op0[31] ^ op1[31];

        if (is_snan(op0) || is_snan(op1)) begin
          res_flags.nv = 1'b1;
          res_data     = CANONICAL_NAN;
        end else if (is_nan(op0) || is_nan(op1)) begin
          res_data = CANONICAL_NAN;
        end else if (is_zero(op0) && is_zero(op1)) begin
          res_flags.nv = 1'b1;
          res_data     = CANONICAL_NAN; // 0 / 0 = NaN
        end else if (is_inf(op0) && is_inf(op1)) begin
          res_flags.nv = 1'b1;
          res_data     = CANONICAL_NAN; // inf / inf = NaN
        end else if (is_inf(op0)) begin
          res_data = {sign_div, 8'hFF, 23'd0};
        end else if (is_inf(op1)) begin
          res_data = {sign_div, 31'd0};
        end else if (is_zero(op1)) begin
          res_flags.dz = 1'b1;
          res_data     = {sign_div, 8'hFF, 23'd0}; // Div by zero -> Inf
        end else if (is_zero(op0)) begin
          res_data = {sign_div, 31'd0};
        end else begin
          unpack_f32(op0, s0, e0, m0);
          unpack_f32(op1, s1, e1, m1);

          dividend = {m0[23:0], 26'd0}; // Unit at bit 49
          div_res  = dividend / 50'(m1[23:0]); // Unit at bit 49-23 = 26
          rem_res  = 24'(dividend % 50'(m1[23:0]));
          quotient = {div_res[47:1], div_res[0] | (|rem_res)};
          exp_div  = e0 - e1;

          round_and_pack(sign_div, exp_div, quotient, rm, res_data, res_flags);
        end
      end

      // ── FSQRT.S ─────────────────────────────────────────────────────────
      UOP_FSQRT_S: begin : blk_fsqrt
        logic s0; int e0; logic [23:0] m0;
        logic [55:0] radicand;
        logic [55:0] rem_val;
        int exp_sqrt;
        logic [27:0] q;
        logic [47:0] sqrt_mant;
        s0 = 1'b0; e0 = 0; m0 = '0; radicand = '0; rem_val = '0; exp_sqrt = 0; q = '0; sqrt_mant = '0;

        res_domain = REG_FP;
        if (is_snan(op0)) begin
          res_flags.nv = 1'b1;
          res_data     = CANONICAL_NAN;
        end else if (is_nan(op0)) begin
          res_data = CANONICAL_NAN;
        end else if (op0[31] && !is_zero(op0)) begin
          res_flags.nv = 1'b1;
          res_data     = CANONICAL_NAN; // sqrt(-x) = NaN
        end else if (is_zero(op0) || is_inf(op0)) begin
          res_data = op0;
        end else begin
          unpack_f32(op0, s0, e0, m0);

          if (e0[0]) begin
            radicand = {2'd0, m0[23:0], 30'd0}; // Unit at 53 (2.0 * 2^52)
            exp_sqrt = (e0 < 0) ? ((e0 - 1) / 2) : (e0 / 2);
          end else begin
            radicand = {3'd0, m0[23:0], 29'd0}; // Unit at 52 (1.0 * 2^52)
            exp_sqrt = e0 / 2;
          end

          rem_val = radicand;
          q = 28'd0;
          for (int b = 27; b >= 0; b--) begin
            logic [55:0] sub_val = (56'(q) << (b + 1)) | (56'd1 << (2 * b));
            if (rem_val >= sub_val) begin
              rem_val = rem_val - sub_val;
              q = q | 28'(1 << b);
            end
          end

          sqrt_mant = {21'd0, q[26:0]};
          round_and_pack(1'b0, exp_sqrt, sqrt_mant, rm, res_data, res_flags);
        end
      end

      default: begin
        res_data   = 32'd0;
        res_domain = REG_FP;
      end
    endcase
  end

  // =========================================================================
  // Completion Packet Formation
  // =========================================================================

  always_comb begin
    fp_cmp = '0;

    if (issue_valid) begin
      fp_cmp.valid          = 1'b1;
      fp_cmp.rob_tag        = issue_req.uop.rob_tag;
      fp_cmp.result_valid   = issue_req.uop.dst.valid;
      fp_cmp.result_domain  = res_domain;
      fp_cmp.result_phys    = issue_req.uop.dst.new_phys;
      fp_cmp.result_data    = res_data;
      fp_cmp.fp_flags_valid = 1'b1;
      fp_cmp.fp_flags       = res_flags;
      fp_cmp.exception      = issue_req.uop.exception;
    end
  end

endmodule
