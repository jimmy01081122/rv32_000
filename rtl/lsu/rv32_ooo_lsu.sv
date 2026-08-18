// rv32_ooo_lsu.sv — Load/Store Unit
// Functional LSU: Address generation, memory request formatting, data extraction, and alignment checks
// Architecture Spec §20–§22 | Uop Spec §21–§22

module rv32_ooo_lsu
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic        clk,
  input  logic        rst,          // synchronous active-high

  input  core_state_e core_state,

  // dmem pending record — drives ROB alias guard (arch_spec §15.2)
  output dmem_pending_t dmem_pending,

  // AGU result from int execute
  input  logic         agu_valid,
  input  exec_req_t    agu_req,
  input  logic [31:0]  agu_addr,

  // SQ data capture: completion buses for writeback snooping
  input  completion_t  int_cmp,
  input  completion_t  fp_cmp,

  // Load completion output
  output completion_t  ld_cmp,

  // Store retirement notification from ROB
  input  logic         sq_retire_valid,
  input  sq_tag_t      sq_retire_tag,

  // Data memory interface (MAX_DMEM_OUTSTANDING=1, ready/valid)
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

  // Flush on rollback / recovery
  input  logic         flush_valid,
  input  rob_tag_t     flush_rob_tag
);

  // =========================================================================
  // 1. Pending Request Tracking
  // =========================================================================

  logic        in_flight_valid;
  exec_req_t   in_flight_req;
  logic [31:0] in_flight_addr;

  assign dmem_pending.valid    = in_flight_valid;
  assign dmem_pending.rob_tag  = in_flight_req.uop.rob_tag;
  assign dmem_pending.lq_valid = in_flight_valid && in_flight_req.uop.lq_valid;
  assign dmem_pending.lq_tag   = in_flight_req.uop.lq_tag;
  assign dmem_pending.sq_valid = in_flight_valid && in_flight_req.uop.sq_valid;
  assign dmem_pending.sq_tag   = in_flight_req.uop.sq_tag;

  // Always ready for memory response
  assign dmem_rsp_ready = 1'b1;

  // =========================================================================
  // 2. Alignment & Byte Enable Generation
  // =========================================================================

  logic        misaligned_load;
  logic        misaligned_store;
  logic [3:0]  byte_en;
  logic [31:0] formatted_wdata;

  always_comb begin
    misaligned_load  = 1'b0;
    misaligned_store = 1'b0;
    byte_en          = 4'b0000;
    formatted_wdata  = 32'd0;

    if (agu_valid) begin
      case (agu_req.uop.mem.size)
        MEM_BYTE: begin
          byte_en = 4'b0001 << agu_addr[1:0];
          case (agu_addr[1:0])
            2'b00: formatted_wdata = {24'd0, agu_req.operand1[7:0]};
            2'b01: formatted_wdata = {16'd0, agu_req.operand1[7:0], 8'd0};
            2'b10: formatted_wdata = {8'd0,  agu_req.operand1[7:0], 16'd0};
            2'b11: formatted_wdata = {agu_req.operand1[7:0], 24'd0};
          endcase
        end

        MEM_HALF: begin
          if (agu_addr[0] != 1'b0) begin
            if (agu_req.uop.mem.is_load)  misaligned_load  = 1'b1;
            if (agu_req.uop.mem.is_store) misaligned_store = 1'b1;
          end
          byte_en = agu_addr[1] ? 4'b1100 : 4'b0011;
          formatted_wdata = agu_addr[1] ? {agu_req.operand1[15:0], 16'd0} : {16'd0, agu_req.operand1[15:0]};
        end

        MEM_WORD: begin
          if (agu_addr[1:0] != 2'b00) begin
            if (agu_req.uop.mem.is_load)  misaligned_load  = 1'b1;
            if (agu_req.uop.mem.is_store) misaligned_store = 1'b1;
          end
          byte_en         = 4'b1111;
          formatted_wdata = agu_req.operand1;
        end

        default: begin
          byte_en         = 4'b1111;
          formatted_wdata = agu_req.operand1;
        end
      endcase
    end
  end

  // =========================================================================
  // 3. Memory Request Channel Driving
  // =========================================================================

  wire can_issue_dmem = agu_valid && !in_flight_valid &&
                        !misaligned_load && !misaligned_store &&
                        (core_state == CORE_RUN);

  assign dmem_req_valid   = can_issue_dmem && !rst;
  assign dmem_req_addr    = {agu_addr[31:2], 2'b00};
  assign dmem_req_wdata   = formatted_wdata;
  assign dmem_req_byte_en = byte_en;
  assign dmem_req_wen     = agu_req.uop.mem.is_store;

  // =========================================================================
  // 4. Load Data Extraction
  // =========================================================================

  logic [31:0] extracted_rdata;
  wire [1:0]   resp_offset = in_flight_addr[1:0];

  always_comb begin
    extracted_rdata = 32'd0;
    case (in_flight_req.uop.mem.size)
      MEM_BYTE: begin
        case (resp_offset)
          2'b00: extracted_rdata = (in_flight_req.uop.mem.load_ext == LOAD_SIGNED) ? {{24{dmem_rsp_rdata[7]}},  dmem_rsp_rdata[7:0]}   : {24'd0, dmem_rsp_rdata[7:0]};
          2'b01: extracted_rdata = (in_flight_req.uop.mem.load_ext == LOAD_SIGNED) ? {{24{dmem_rsp_rdata[15]}}, dmem_rsp_rdata[15:8]}  : {24'd0, dmem_rsp_rdata[15:8]};
          2'b10: extracted_rdata = (in_flight_req.uop.mem.load_ext == LOAD_SIGNED) ? {{24{dmem_rsp_rdata[23]}}, dmem_rsp_rdata[23:16]} : {24'd0, dmem_rsp_rdata[23:16]};
          2'b11: extracted_rdata = (in_flight_req.uop.mem.load_ext == LOAD_SIGNED) ? {{24{dmem_rsp_rdata[31]}}, dmem_rsp_rdata[31:24]} : {24'd0, dmem_rsp_rdata[31:24]};
        endcase
      end

      MEM_HALF: begin
        if (resp_offset[1]) begin
          extracted_rdata = (in_flight_req.uop.mem.load_ext == LOAD_SIGNED) ? {{16{dmem_rsp_rdata[31]}}, dmem_rsp_rdata[31:16]} : {16'd0, dmem_rsp_rdata[31:16]};
        end else begin
          extracted_rdata = (in_flight_req.uop.mem.load_ext == LOAD_SIGNED) ? {{16{dmem_rsp_rdata[15]}}, dmem_rsp_rdata[15:0]}  : {16'd0, dmem_rsp_rdata[15:0]};
        end
      end

      MEM_WORD: begin
        extracted_rdata = dmem_rsp_rdata;
      end

      default: extracted_rdata = dmem_rsp_rdata;
    endcase
  end

  // =========================================================================
  // 5. Completion Packet Formation
  // =========================================================================

  always_comb begin
    ld_cmp = '0;

    if (in_flight_valid && in_flight_req.uop.mem.is_load && dmem_rsp_valid) begin
      ld_cmp.valid         = 1'b1;
      ld_cmp.rob_tag       = in_flight_req.uop.rob_tag;
      ld_cmp.result_valid  = in_flight_req.uop.dst.valid;
      ld_cmp.result_domain = in_flight_req.uop.dst.domain;
      ld_cmp.result_phys   = in_flight_req.uop.dst.new_phys;
      ld_cmp.result_data   = extracted_rdata;
      if (dmem_rsp_error) begin
        ld_cmp.exception.valid = 1'b1;
        ld_cmp.exception.cause = EXC_LOAD_ACCESS_FAULT;
        ld_cmp.exception.tval  = in_flight_addr;
      end
    end
  end

  // =========================================================================
  // 6. Sequential Tracking
  // =========================================================================

  always_ff @(posedge clk) begin
    if (rst) begin
      in_flight_valid <= 1'b0;
      in_flight_req   <= '0;
      in_flight_addr  <= 32'd0;
    end else begin
      if (flush_valid) begin
        in_flight_valid <= 1'b0;
      end else begin
        // Launch new memory access
        if (dmem_req_valid && dmem_req_ready) begin
          in_flight_valid <= 1'b1;
          in_flight_req   <= agu_req;
          in_flight_addr  <= agu_addr;
        end

        // Complete memory response
        if (dmem_rsp_valid && in_flight_valid) begin
          in_flight_valid <= 1'b0;
        end
      end
    end
  end

endmodule
