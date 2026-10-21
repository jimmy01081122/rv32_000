// rv32_ooo_multiplier.sv — Pipelined Integer Multiplier (RV32M)
// Implements MUL, MULH, MULHSU, MULHU with a parameterized fixed-latency pipeline
// Supports back-to-back issue (1 op/cycle throughput), ready/valid backpressure, and synchronous flush
// architecture_spec.md §21.2, Appendix C §1 | uop_spec.md §17

module rv32_ooo_multiplier
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
#(
  parameter int LATENCY = 3 // 3-cycle baseline pipelined multiplier (architecture_spec.md Appendix C)
)(
  input  logic        clk,
  input  logic        rst,          // synchronous active-high reset
  input  logic        flush_valid,  // synchronous flush (kills in-flight instructions)

  // Request interface (from Integer Execute Issue)
  input  logic        req_valid,
  input  uop_op_e     req_op,
  input  logic [31:0] req_op0,
  input  logic [31:0] req_op1,
  input  rob_tag_t    req_rob_tag,
  input  phys_reg_t   req_dest_phys,
  input  reg_domain_e req_dest_domain,
  input  logic [31:0] req_pc,
  output logic        req_ready,

  // Response interface (to Completion Arbiter)
  output logic        rsp_valid,
  output logic [31:0] rsp_result,
  output rob_tag_t    rsp_rob_tag,
  output phys_reg_t   rsp_dest_phys,
  output reg_domain_e rsp_dest_domain,
  output logic [31:0] rsp_pc,
  input  logic        rsp_ready,

  // Status
  output logic        busy
);

  // =========================================================================
  // 1. Operand Conditioning (Sign Extension to 33-bit Signed)
  // =========================================================================

  wire sign_a = (req_op == UOP_MUL) || (req_op == UOP_MULH) || (req_op == UOP_MULHSU);
  wire sign_b = (req_op == UOP_MUL) || (req_op == UOP_MULH);

  wire signed [32:0] a_ext = sign_a ? {req_op0[31], req_op0} : {1'b0, req_op0};
  wire signed [32:0] b_ext = sign_b ? {req_op1[31], req_op1} : {1'b0, req_op1};

  // Backpressure stall condition: output valid but not accepted by arbiter
  wire stall = rsp_valid && !rsp_ready;
  assign req_ready = !stall;

  // =========================================================================
  // 2. Pipeline Registers
  // =========================================================================

  // Stage 1: Latched operands and metadata
  logic               s1_valid;
  uop_op_e            s1_op;
  logic signed [32:0] s1_a;
  logic signed [32:0] s1_b;
  rob_tag_t           s1_rob_tag;
  phys_reg_t          s1_dest_phys;
  reg_domain_e        s1_dest_domain;
  logic [31:0]        s1_pc;

  // Stage 2: Latched 66-bit signed product and metadata
  logic               s2_valid;
  uop_op_e            s2_op;
  logic signed [65:0] s2_product;
  rob_tag_t           s2_rob_tag;
  phys_reg_t          s2_dest_phys;
  reg_domain_e        s2_dest_domain;
  logic [31:0]        s2_pc;

  // Stage 3: Latched 32-bit final result and response packet
  logic               s3_valid;
  logic [31:0]        s3_result;
  rob_tag_t           s3_rob_tag;
  phys_reg_t          s3_dest_phys;
  reg_domain_e        s3_dest_domain;
  logic [31:0]        s3_pc;

  // Multiplier product computation between Stage 1 and Stage 2
  wire signed [65:0] product_stage1 = s1_a * s1_b;

  // Result selection between Stage 2 and Stage 3
  logic [31:0] result_stage2;
  always_comb begin
    case (s2_op)
      UOP_MUL:    result_stage2 = s2_product[31:0];
      UOP_MULH:   result_stage2 = s2_product[63:32];
      UOP_MULHSU: result_stage2 = s2_product[63:32];
      UOP_MULHU:  result_stage2 = s2_product[63:32];
      default:    result_stage2 = 32'd0;
    endcase
  end

  // Pipeline update logic
  always_ff @(posedge clk) begin
    if (rst || flush_valid) begin
      s1_valid       <= 1'b0;
      s1_op          <= UOP_INVALID;
      s1_a           <= 33'd0;
      s1_b           <= 33'd0;
      s1_rob_tag     <= '0;
      s1_dest_phys   <= '0;
      s1_dest_domain <= REG_NONE;
      s1_pc          <= 32'd0;

      s2_valid       <= 1'b0;
      s2_op          <= UOP_INVALID;
      s2_product     <= 66'd0;
      s2_rob_tag     <= '0;
      s2_dest_phys   <= '0;
      s2_dest_domain <= REG_NONE;
      s2_pc          <= 32'd0;

      s3_valid       <= 1'b0;
      s3_result      <= 32'd0;
      s3_rob_tag     <= '0;
      s3_dest_phys   <= '0;
      s3_dest_domain <= REG_NONE;
      s3_pc          <= 32'd0;
    end else if (!stall) begin
      // Advance Stage 3 (Output Stage)
      s3_valid       <= s2_valid;
      s3_result      <= result_stage2;
      s3_rob_tag     <= s2_rob_tag;
      s3_dest_phys   <= s2_dest_phys;
      s3_dest_domain <= s2_dest_domain;
      s3_pc          <= s2_pc;

      // Advance Stage 2 (Multiply Stage)
      s2_valid       <= s1_valid;
      s2_op          <= s1_op;
      s2_product     <= product_stage1;
      s2_rob_tag     <= s1_rob_tag;
      s2_dest_phys   <= s1_dest_phys;
      s2_dest_domain <= s1_dest_domain;
      s2_pc          <= s1_pc;

      // Advance Stage 1 (Input Stage)
      if (req_valid) begin
        s1_valid       <= 1'b1;
        s1_op          <= req_op;
        s1_a           <= a_ext;
        s1_b           <= b_ext;
        s1_rob_tag     <= req_rob_tag;
        s1_dest_phys   <= req_dest_phys;
        s1_dest_domain <= req_dest_domain;
        s1_pc          <= req_pc;
      end else begin
        s1_valid       <= 1'b0;
        s1_op          <= UOP_INVALID;
        s1_a           <= 33'd0;
        s1_b           <= 33'd0;
        s1_rob_tag     <= '0;
        s1_dest_phys   <= '0;
        s1_dest_domain <= REG_NONE;
        s1_pc          <= 32'd0;
      end
    end
  end

  // =========================================================================
  // 3. Response Generation & Status
  // =========================================================================

  assign rsp_valid       = s3_valid;
  assign rsp_result      = s3_result;
  assign rsp_rob_tag     = s3_rob_tag;
  assign rsp_dest_phys   = s3_dest_phys;
  assign rsp_dest_domain = s3_dest_domain;
  assign rsp_pc          = s3_pc;

  // Busy indicates the pipeline contains active instructions or is stalled
  assign busy            = s1_valid || s2_valid || s3_valid;

endmodule
