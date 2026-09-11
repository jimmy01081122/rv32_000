// rv32_ooo_divider.sv — Multi-Cycle Iterative Radix-2 Divider
// Implements RV32M DIV, DIVU, REM, REMU with exact RISC-V semantics (§19)
// Radix-2 restoring division (32 cycles calculation, 1 cycle special-case fast path)

module rv32_ooo_divider
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic        clk,
  input  logic        rst,          // synchronous active-high
  input  logic        flush_valid,  // pipeline flush/recovery

  // Request interface (from EX0)
  input  logic        req_valid,
  input  uop_op_e     req_op,
  input  logic [31:0] req_op0,
  input  logic [31:0] req_op1,
  input  rob_tag_t    req_rob_tag,
  input  phys_reg_t   req_dest_phys,
  input  reg_domain_e req_dest_domain,
  input  logic [31:0] req_pc,
  output logic        req_ready,

  // Response / Completion interface (to writeback arbitration)
  output logic        rsp_valid,
  output logic [31:0] rsp_result,
  output rob_tag_t    rsp_rob_tag,
  output phys_reg_t   rsp_dest_phys,
  output reg_domain_e rsp_dest_domain,
  output logic [31:0] rsp_pc,
  input  logic        rsp_ready,

  // Status to Issue Queue
  output logic        busy
);

  typedef enum logic [1:0] {
    DIV_IDLE,
    DIV_CALC,
    DIV_DONE
  } div_state_e;

  div_state_e state_q, state_d;

  // Latched metadata
  uop_op_e     op_q;
  rob_tag_t    rob_tag_q;
  phys_reg_t   dest_phys_q;
  reg_domain_e dest_domain_q;
  logic [31:0] pc_q;
  logic [31:0] result_q;

  // Calculation registers
  logic [31:0] divisor_q;
  logic [31:0] rem_q;
  logic [31:0] quot_q;
  logic [5:0]  count_q;
  logic        res_sign_quot_q;
  logic        res_sign_rem_q;
  logic        is_rem_op_q;

  // Decode operation properties
  wire is_signed_op = (req_op == UOP_DIV) || (req_op == UOP_REM);
  wire op0_neg      = is_signed_op && req_op0[31];
  wire op1_neg      = is_signed_op && req_op1[31];

  wire [31:0] abs_op0 = op0_neg ? (-req_op0) : req_op0;
  wire [31:0] abs_op1 = op1_neg ? (-req_op1) : req_op1;

  wire div_by_zero  = (req_op1 == 32'd0);
  wire div_overflow = is_signed_op && (req_op0 == 32'h8000_0000) && (req_op1 == 32'hFFFF_FFFF);

  // Special-case result calculation
  logic [31:0] special_result;
  always_comb begin
    special_result = 32'd0;
    if (div_by_zero) begin
      case (req_op)
        UOP_DIV:  special_result = 32'hFFFF_FFFF;
        UOP_DIVU: special_result = 32'hFFFF_FFFF;
        UOP_REM:  special_result = req_op0;
        UOP_REMU: special_result = req_op0;
        default:  special_result = 32'd0;
      endcase
    end else if (div_overflow) begin
      case (req_op)
        UOP_DIV:  special_result = 32'h8000_0000;
        UOP_REM:  special_result = 32'd0;
        default:  special_result = 32'd0;
      endcase
    end
  end

  // Iteration arithmetic step
  wire [63:0] shifted      = {rem_q, quot_q} << 1;
  wire [32:0] sub_res      = {1'b0, shifted[63:32]} - {1'b0, divisor_q};
  wire        can_sub      = !sub_res[32]; // no borrow (rem >= divisor)
  wire [31:0] next_rem     = can_sub ? sub_res[31:0] : shifted[63:32];
  wire [31:0] next_quot    = {shifted[31:1], can_sub};

  // Final adjusted quotient and remainder at step 32
  wire [31:0] adj_quot = res_sign_quot_q ? (-next_quot) : next_quot;
  wire [31:0] adj_rem  = res_sign_rem_q  ? (-next_rem)  : next_rem;
  wire [31:0] calc_final_result = is_rem_op_q ? adj_rem : adj_quot;

  // FSM and Datapath
  always_comb begin
    state_d   = state_q;
    req_ready = 1'b0;
    rsp_valid = 1'b0;

    case (state_q)
      DIV_IDLE: begin
        req_ready = 1'b1;
        if (req_valid) begin
          if (div_by_zero || div_overflow) begin
            state_d = DIV_DONE;
          end else begin
            state_d = DIV_CALC;
          end
        end
      end

      DIV_CALC: begin
        req_ready = 1'b0;
        if (count_q == 6'd31) begin
          state_d = DIV_DONE;
        end
      end

      DIV_DONE: begin
        rsp_valid = 1'b1;
        if (rsp_ready) begin
          if (req_valid) begin
            // Immediately accept back-to-back request
            req_ready = 1'b1;
            if (div_by_zero || div_overflow) begin
              state_d = DIV_DONE;
            end else begin
              state_d = DIV_CALC;
            end
          end else begin
            state_d = DIV_IDLE;
          end
        end
      end

      default: state_d = DIV_IDLE;
    endcase
  end

  // Sequential state and registers
  always_ff @(posedge clk) begin
    if (rst || flush_valid) begin
      state_q         <= DIV_IDLE;
      op_q            <= UOP_INVALID;
      rob_tag_q       <= '0;
      dest_phys_q     <= '0;
      dest_domain_q   <= REG_NONE;
      pc_q            <= 32'd0;
      result_q        <= 32'd0;
      divisor_q       <= 32'd0;
      rem_q           <= 32'd0;
      quot_q          <= 32'd0;
      count_q         <= 6'd0;
      res_sign_quot_q <= 1'b0;
      res_sign_rem_q  <= 1'b0;
      is_rem_op_q     <= 1'b0;
    end else begin
      state_q <= state_d;

      case (state_q)
        DIV_IDLE: begin
          if (req_valid) begin
            op_q            <= req_op;
            rob_tag_q       <= req_rob_tag;
            dest_phys_q     <= req_dest_phys;
            dest_domain_q   <= req_dest_domain;
            pc_q            <= req_pc;

            if (div_by_zero || div_overflow) begin
              result_q <= special_result;
            end else begin
              divisor_q       <= abs_op1;
              rem_q           <= 32'd0;
              quot_q          <= abs_op0;
              count_q         <= 6'd0;
              res_sign_quot_q <= is_signed_op && (op0_neg ^ op1_neg);
              res_sign_rem_q  <= is_signed_op && op0_neg;
              is_rem_op_q     <= (req_op == UOP_REM) || (req_op == UOP_REMU);
            end
          end
        end

        DIV_CALC: begin
          rem_q   <= next_rem;
          quot_q  <= next_quot;
          count_q <= count_q + 6'd1;

          if (count_q == 6'd31) begin
            result_q <= calc_final_result;
          end
        end

        DIV_DONE: begin
          if (rsp_ready && req_valid) begin
            op_q            <= req_op;
            rob_tag_q       <= req_rob_tag;
            dest_phys_q     <= req_dest_phys;
            dest_domain_q   <= req_dest_domain;
            pc_q            <= req_pc;

            if (div_by_zero || div_overflow) begin
              result_q <= special_result;
            end else begin
              divisor_q       <= abs_op1;
              rem_q           <= 32'd0;
              quot_q          <= abs_op0;
              count_q         <= 6'd0;
              res_sign_quot_q <= is_signed_op && (op0_neg ^ op1_neg);
              res_sign_rem_q  <= is_signed_op && op0_neg;
              is_rem_op_q     <= (req_op == UOP_REM) || (req_op == UOP_REMU);
            end
          end
        end

        default: ;
      endcase
    end
  end

  // Outputs
  assign rsp_result      = result_q;
  assign rsp_rob_tag     = rob_tag_q;
  assign rsp_dest_phys   = dest_phys_q;
  assign rsp_dest_domain = dest_domain_q;
  assign rsp_pc          = pc_q;
  assign busy            = (state_q != DIV_IDLE);

endmodule
