// rv32_ooo_fp_divsqrt.sv — Dedicated Iterative Floating-Point DIV/SQRT Unit
// Implements sequential radix-2 FDIV.S and digit-by-digit FSQRT.S (IEEE 754-2008 single-precision)
// Completely eliminates combinational division and unrolled square-root arrays from synthesis.
// architecture_spec.md §23, §24 | uop_spec.md §6, §13, §18–§19 | AP4F Specification

module rv32_ooo_fp_divsqrt
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

  // Completion packet to 3:1 completion arbiter
  output logic        cmp_valid,
  output completion_t cmp_data,
  input  logic        cmp_ready
);

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

  // Unpack single-precision float
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

  // Count leading zeros of a 24-bit value
  function automatic int clz24(input logic [23:0] val);
    int res;
    res = 24;
    for (int i = 23; i >= 0; i--) begin
      if (val[i]) begin
        res = 23 - i;
        break;
      end
    end
    return res;
  endfunction

  // Standard IEEE 754 Single-Precision Rounding & Packing
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
    logic [5:0] msb_pos;
    int         shift_amt;
    int         max_lshift;
    logic [47:0] sticky_mask;

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

      shift_amt = int'(msb_pos) - 26;

      if (shift_amt > 0) begin
        sticky_mask = (shift_amt >= 48) ? '1 : ((48'd1 << shift_amt) - 48'd1);
        sticky      = |(norm_mant & sticky_mask);
        norm_mant   = (shift_amt >= 48) ? '0 : (norm_mant >> shift_amt);
        norm_exp    = norm_exp + shift_amt;
      end

      if (shift_amt < 0) begin
        max_lshift = norm_exp + 126;
        if (max_lshift <= 0) begin
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

      if (guard || round_bit || sticky) flags.nx = 1'b1;

      significand = {1'b0, norm_mant[26:3]};
      if (round_up) significand = significand + 25'd1;

      final_exp = norm_exp;
      if (significand[24]) begin
        significand = significand >> 1;
        final_exp   = final_exp + 1;
      end

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

  // Completion packet helper
  function automatic completion_t make_completion(
    input renamed_uop_t uop_in,
    input logic [31:0]  data_in,
    input fp_flags_t    flags_in
  );
    completion_t cmp;
    cmp = '0;
    cmp.valid          = 1'b1;
    cmp.rob_tag        = uop_in.rob_tag;
    cmp.result_valid   = uop_in.dst.valid;
    cmp.result_domain  = REG_FP;
    cmp.result_phys    = uop_in.dst.new_phys;
    cmp.result_data    = data_in;
    cmp.fp_flags_valid = 1'b1;
    cmp.fp_flags       = flags_in;
    cmp.exception      = uop_in.exception;
    return cmp;
  endfunction

  // =========================================================================
  // FSM State Definitions & Registers
  // =========================================================================

  typedef enum logic [2:0] {
    DIVSQRT_IDLE,
    DIVSQRT_SPECIAL,
    DIVSQRT_DIV_ITER,
    DIVSQRT_SQRT_ITER,
    DIVSQRT_ROUND,
    DIVSQRT_HOLD
  } divsqrt_state_e;

  divsqrt_state_e state;

  // Metadata registers preserved throughout iterative computation
  renamed_uop_t uop_saved;
  fp_rm_e       rm_saved;
  uop_op_e      op_saved;
  logic         sign_reg;
  int           exp_reg;

  // Special-case storage
  logic [31:0]  special_res_data;
  fp_flags_t    special_res_flags;

  // Iteration datapath registers
  logic [55:0]  rem;
  logic [24:0]  divisor_reg;
  logic [27:0]  q;
  logic [4:0]   count;

  // Holding output stage
  logic         holding_valid;
  completion_t  holding_data;

  // Issue readiness: only ready when idle and holding register empty
  // Purely dependent on local flip-flop state to avoid combinational loop into FP IQ.
  assign issue_ready = (state == DIVSQRT_IDLE) && !holding_valid;

  // =========================================================================
  // Early Special-Case Decoding
  // =========================================================================

  wire [31:0] op0 = issue_req.operand0;
  wire [31:0] op1 = issue_req.operand1;

  logic        is_div_special;
  logic [31:0] div_special_data;
  fp_flags_t   div_special_flags;

  always_comb begin
    is_div_special    = 1'b0;
    div_special_data  = '0;
    div_special_flags = '0;

    if (issue_req.uop.op == UOP_FDIV_S) begin
      logic sign_div = op0[31] ^ op1[31];
      if (is_snan(op0) || is_snan(op1)) begin
        is_div_special       = 1'b1;
        div_special_flags.nv = 1'b1;
        div_special_data     = CANONICAL_NAN;
      end else if (is_nan(op0) || is_nan(op1)) begin
        is_div_special   = 1'b1;
        div_special_data = CANONICAL_NAN;
      end else if (is_zero(op0) && is_zero(op1)) begin
        is_div_special       = 1'b1;
        div_special_flags.nv = 1'b1;
        div_special_data     = CANONICAL_NAN;
      end else if (is_inf(op0) && is_inf(op1)) begin
        is_div_special       = 1'b1;
        div_special_flags.nv = 1'b1;
        div_special_data     = CANONICAL_NAN;
      end else if (is_inf(op0)) begin
        is_div_special   = 1'b1;
        div_special_data = {sign_div, 8'hFF, 23'd0};
      end else if (is_inf(op1)) begin
        is_div_special   = 1'b1;
        div_special_data = {sign_div, 31'd0};
      end else if (is_zero(op1)) begin
        is_div_special       = 1'b1;
        div_special_flags.dz = 1'b1;
        div_special_data     = {sign_div, 8'hFF, 23'd0};
      end else if (is_zero(op0)) begin
        is_div_special   = 1'b1;
        div_special_data = {sign_div, 31'd0};
      end
    end
  end

  logic        is_sqrt_special;
  logic [31:0] sqrt_special_data;
  fp_flags_t   sqrt_special_flags;

  always_comb begin
    is_sqrt_special    = 1'b0;
    sqrt_special_data  = '0;
    sqrt_special_flags = '0;

    if (issue_req.uop.op == UOP_FSQRT_S) begin
      if (is_snan(op0)) begin
        is_sqrt_special       = 1'b1;
        sqrt_special_flags.nv = 1'b1;
        sqrt_special_data     = CANONICAL_NAN;
      end else if (is_nan(op0)) begin
        is_sqrt_special   = 1'b1;
        sqrt_special_data = CANONICAL_NAN;
      end else if (op0[31] && !is_zero(op0)) begin
        is_sqrt_special       = 1'b1;
        sqrt_special_flags.nv = 1'b1;
        sqrt_special_data     = CANONICAL_NAN;
      end else if (is_zero(op0) || is_inf(op0)) begin
        is_sqrt_special   = 1'b1;
        sqrt_special_data = op0;
      end
    end
  end

  // =========================================================================
  // Unpack and Normalization (Combinational at Issue)
  // =========================================================================

  logic s0_unpk, s1_unpk;
  int   e0_unpk, e1_unpk;
  logic [23:0] m0_unpk, m1_unpk;
  int   lz0, lz1;
  logic [23:0] norm_m0, norm_m1;
  int   norm_e0, norm_e1;

  always_comb begin
    unpack_f32(op0, s0_unpk, e0_unpk, m0_unpk);
    unpack_f32(op1, s1_unpk, e1_unpk, m1_unpk);

    lz0 = clz24(m0_unpk);
    lz1 = clz24(m1_unpk);

    norm_m0 = m0_unpk << lz0;
    norm_e0 = e0_unpk - lz0;

    norm_m1 = m1_unpk << lz1;
    norm_e1 = e1_unpk - lz1;
  end

  // =========================================================================
  // Iteration Math (Single Radix-2 Step per Clock Cycle)
  // =========================================================================

  // Radix-2 division step
  wire [24:0] div_curr_rem = rem[24:0];
  wire        div_sub_ok   = (div_curr_rem >= divisor_reg);
  wire [24:0] div_diff     = div_sub_ok ? (div_curr_rem - divisor_reg) : div_curr_rem;
  wire [27:0] next_div_q   = {q[26:0], div_sub_ok};

  // Digit-by-digit square root step
  wire [55:0] sqrt_sub_val = (56'(q) << (count + 5'd1)) | (56'd1 << (2 * count));
  wire        sqrt_sub_ok  = (rem >= sqrt_sub_val);
  wire [55:0] next_sqrt_rem = sqrt_sub_ok ? (rem - sqrt_sub_val) : rem;
  wire [27:0] next_sqrt_q   = sqrt_sub_ok ? (q | (28'd1 << count)) : q;

  // =========================================================================
  // Rounding & Completion Formation
  // =========================================================================

  logic [31:0] round_data;
  fp_flags_t   round_flags;
  completion_t round_cmp;

  always_comb begin
    logic [47:0] mant;
    round_data  = '0;
    round_flags = '0;

    if (op_saved == UOP_FDIV_S) begin
      mant = {21'd0, q[26:1], q[0] | (|rem)};
      round_and_pack(sign_reg, exp_reg, mant, rm_saved, round_data, round_flags);
    end else begin
      mant = {21'd0, q[26:1], q[0] | (|rem)};
      round_and_pack(1'b0, exp_reg, mant, rm_saved, round_data, round_flags);
    end

    round_cmp = make_completion(uop_saved, round_data, round_flags);
  end

  completion_t special_cmp;
  assign special_cmp = make_completion(uop_saved, special_res_data, special_res_flags);

  // Output completion bus multiplexer
  always_comb begin
    if (state == DIVSQRT_HOLD) begin
      cmp_valid = 1'b1;
      cmp_data  = holding_data;
    end else if (state == DIVSQRT_ROUND) begin
      cmp_valid = 1'b1;
      cmp_data  = round_cmp;
    end else if (state == DIVSQRT_SPECIAL) begin
      cmp_valid = 1'b1;
      cmp_data  = special_cmp;
    end else begin
      cmp_valid = 1'b0;
      cmp_data  = '0;
    end
  end

  // =========================================================================
  // Sequential FSM & Register Updates
  // =========================================================================

  always_ff @(posedge clk) begin
    if (rst || flush_valid) begin
      state             <= DIVSQRT_IDLE;
      holding_valid     <= 1'b0;
      holding_data      <= '0;
      rem               <= '0;
      divisor_reg       <= '0;
      q                 <= '0;
      count             <= '0;
      sign_reg          <= 1'b0;
      exp_reg           <= 0;
      special_res_data  <= '0;
      special_res_flags <= '0;
      uop_saved         <= '0;
      rm_saved          <= RM_RNE;
      op_saved          <= UOP_FDIV_S;
    end else begin
      case (state)
        DIVSQRT_IDLE: begin
          if (issue_valid && issue_ready) begin
            uop_saved <= issue_req.uop;
            rm_saved  <= issue_req.uop.fp.rm;
            op_saved  <= issue_req.uop.op;

            if (issue_req.uop.op == UOP_FDIV_S) begin
              if (is_div_special) begin
                special_res_data  <= div_special_data;
                special_res_flags <= div_special_flags;
                state             <= DIVSQRT_SPECIAL;
              end else begin
                sign_reg    <= s0_unpk ^ s1_unpk;
                exp_reg     <= norm_e0 - norm_e1;
                rem         <= {32'd0, norm_m0};
                divisor_reg <= {1'b0, norm_m1};
                q           <= 28'd0;
                count       <= 5'd26; // 27 iterations: 26 down to 0
                state       <= DIVSQRT_DIV_ITER;
              end
            end else if (issue_req.uop.op == UOP_FSQRT_S) begin
              if (is_sqrt_special) begin
                special_res_data  <= sqrt_special_data;
                special_res_flags <= sqrt_special_flags;
                state             <= DIVSQRT_SPECIAL;
              end else begin
                sign_reg <= 1'b0;
                q        <= 28'd0;
                count    <= 5'd27; // 28 iterations: 27 down to 0
                state    <= DIVSQRT_SQRT_ITER;
                if (norm_e0[0]) begin
                  rem     <= {2'd0, norm_m0, 30'd0};
                  exp_reg <= (norm_e0 < 0) ? ((norm_e0 - 1) / 2) : (norm_e0 / 2);
                end else begin
                  rem     <= {3'd0, norm_m0, 29'd0};
                  exp_reg <= norm_e0 / 2;
                end
              end
            end
          end
        end

        DIVSQRT_SPECIAL: begin
          if (cmp_ready) begin
            holding_valid <= 1'b0;
            holding_data  <= '0;
            state         <= DIVSQRT_IDLE;
          end else begin
            holding_valid <= 1'b1;
            holding_data  <= special_cmp;
            state         <= DIVSQRT_HOLD;
          end
        end

        DIVSQRT_DIV_ITER: begin
          if (count == 5'd0) begin
            rem   <= {31'd0, div_diff}; // final remainder
            q     <= next_div_q;
            state <= DIVSQRT_ROUND;
          end else begin
            rem   <= {30'd0, div_diff, 1'b0};
            q     <= next_div_q;
            count <= count - 5'd1;
          end
        end

        DIVSQRT_SQRT_ITER: begin
          rem <= next_sqrt_rem;
          q   <= next_sqrt_q;
          if (count == 5'd0) begin
            state <= DIVSQRT_ROUND;
          end else begin
            count <= count - 5'd1;
          end
        end

        DIVSQRT_ROUND: begin
          if (cmp_ready) begin
            holding_valid <= 1'b0;
            holding_data  <= '0;
            state         <= DIVSQRT_IDLE;
          end else begin
            holding_valid <= 1'b1;
            holding_data  <= round_cmp;
            state         <= DIVSQRT_HOLD;
          end
        end

        DIVSQRT_HOLD: begin
          if (cmp_ready) begin
            holding_valid <= 1'b0;
            holding_data  <= '0;
            state         <= DIVSQRT_IDLE;
          end
        end

        default: begin
          state <= DIVSQRT_IDLE;
        end
      endcase
    end
  end

endmodule
