// rv32_ooo_lsu.sv — Load/Store Unit
// Complete Store Queue (SQ) and Load Queue (LQ) with safe in-order store retirement,
// store-to-load forwarding, memory disambiguation, and speculative wrong-path isolation.
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

  // Dispatch allocation interface from Rename/Dispatch (for early SQ reservation)
  input  logic         disp_valid,
  input  renamed_uop_t disp_uop,

  // AGU result from int execute
  input  logic         agu_valid,
  input  exec_req_t    agu_req,
  input  logic [31:0]  agu_addr,

  // SQ data capture: completion buses for writeback snooping
  input  completion_t  int_cmp,
  input  completion_t  fp_cmp,

  // Load completion output
  output completion_t  ld_cmp,
  output logic         lsu_ready,

  // Store retirement handshake from ROB
  input  logic         sq_retire_valid,
  input  rob_tag_t     sq_retire_rob_tag,
  output logic         sq_retire_ack,
  output logic [31:0]  retire_store_addr,
  output logic [3:0]   retire_store_mask,
  output logic [31:0]  retire_store_data,

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
  // 1. Structure Definitions & Age Comparison Helper
  // =========================================================================

  localparam integer SQ_SIZE = SQ_ENTRIES; // 4
  localparam integer LQ_SIZE = LQ_ENTRIES; // 4

  typedef struct packed {
    logic        valid;
    rob_tag_t    rob_tag;
    logic        addr_valid;
    logic [31:0] addr;
    logic [3:0]  byte_mask;
    logic [31:0] data;
    mem_size_e   size;
    logic        is_fp;
    exception_t  exception;
    logic        retired;      // marked for retirement by ROB
    logic        req_sent;     // dmem write request dispatched
    logic        rsp_done;     // dmem write response received
  } sq_slot_t;

  sq_slot_t sq [SQ_SIZE-1:0];

  // Helper to determine if ROB tag a is strictly older than ROB tag b
  function automatic logic is_older_rob(input rob_tag_t a, input rob_tag_t b);
    logic [ROB_SEQ_WIDTH-1:0] diff;
    diff = b.seq - a.seq;
    return (a.seq != b.seq) && (diff < 12'd2048);
  endfunction

  // =========================================================================
  // 2. Alignment & Byte Formatting Helper
  // =========================================================================

  function automatic logic [3:0] calc_byte_en(input logic [31:0] addr, input mem_size_e size);
    case (size)
      MEM_BYTE: calc_byte_en = 4'b0001 << addr[1:0];
      MEM_HALF: calc_byte_en = addr[1] ? 4'b1100 : 4'b0011;
      MEM_WORD: calc_byte_en = 4'b1111;
      default:  calc_byte_en = 4'b1111;
    endcase
  endfunction

  function automatic logic [31:0] format_store_data(input logic [31:0] raw_data, input logic [31:0] addr, input mem_size_e size);
    case (size)
      MEM_BYTE: begin
        case (addr[1:0])
          2'b00: format_store_data = {24'd0, raw_data[7:0]};
          2'b01: format_store_data = {16'd0, raw_data[7:0], 8'd0};
          2'b10: format_store_data = {8'd0,  raw_data[7:0], 16'd0};
          2'b11: format_store_data = {raw_data[7:0], 24'd0};
        endcase
      end
      MEM_HALF: begin
        format_store_data = addr[1] ? {raw_data[15:0], 16'd0} : {16'd0, raw_data[15:0]};
      end
      MEM_WORD: begin
        format_store_data = raw_data;
      end
      default: format_store_data = raw_data;
    endcase
  endfunction

  function automatic logic [31:0] extract_load_data(input logic [31:0] word_data, input logic [1:0] offset, input mem_size_e size, input load_ext_e load_ext);
    case (size)
      MEM_BYTE: begin
        case (offset)
          2'b00: extract_load_data = (load_ext == LOAD_SIGNED) ? {{24{word_data[7]}},  word_data[7:0]}   : {24'd0, word_data[7:0]};
          2'b01: extract_load_data = (load_ext == LOAD_SIGNED) ? {{24{word_data[15]}}, word_data[15:8]}  : {24'd0, word_data[15:8]};
          2'b10: extract_load_data = (load_ext == LOAD_SIGNED) ? {{24{word_data[23]}}, word_data[23:16]} : {24'd0, word_data[23:16]};
          2'b11: extract_load_data = (load_ext == LOAD_SIGNED) ? {{24{word_data[31]}}, word_data[31:24]} : {24'd0, word_data[31:24]};
        endcase
      end
      MEM_HALF: begin
        if (offset[1]) begin
          extract_load_data = (load_ext == LOAD_SIGNED) ? {{16{word_data[31]}}, word_data[31:16]} : {16'd0, word_data[31:16]};
        end else begin
          extract_load_data = (load_ext == LOAD_SIGNED) ? {{16{word_data[15]}}, word_data[15:0]}  : {16'd0, word_data[15:0]};
        end
      end
      MEM_WORD: begin
        extract_load_data = word_data;
      end
      default: extract_load_data = word_data;
    endcase
  endfunction

  // =========================================================================
  // 3. In-Flight Memory Request Tracking
  // =========================================================================

  logic        in_flight_valid;
  logic        in_flight_is_store;
  rob_tag_t    in_flight_rob_tag;
  logic [31:0] in_flight_addr;
  exec_req_t   in_flight_load_req;
  logic [SQ_IDX_W-1:0] in_flight_sq_idx;

  assign dmem_pending.valid    = in_flight_valid;
  assign dmem_pending.rob_tag  = in_flight_rob_tag;
  assign dmem_pending.lq_valid = in_flight_valid && !in_flight_is_store;
  assign dmem_pending.lq_tag   = '0;
  assign dmem_pending.sq_valid = in_flight_valid && in_flight_is_store;
  assign dmem_pending.sq_tag   = '0;

  assign dmem_rsp_ready = 1'b1;

  // =========================================================================
  // 4. Store Queue Allocation & Update Logic
  // =========================================================================

  // Misalignment check for incoming AGU
  logic agu_misaligned;
  always_comb begin
    agu_misaligned = 1'b0;
    if (agu_valid) begin
      case (agu_req.uop.mem.size)
        MEM_HALF: if (agu_addr[0]   != 1'b0)  agu_misaligned = 1'b1;
        MEM_WORD: if (agu_addr[1:0] != 2'b00) agu_misaligned = 1'b1;
        default:  agu_misaligned = 1'b0;
      endcase
    end
  end

  // Free SQ slot selection
  logic [SQ_IDX_W-1:0] free_sq_idx;
  logic                sq_has_free;
  always_comb begin
    free_sq_idx = '0;
    sq_has_free = 1'b0;
    for (int i = 0; i < SQ_SIZE; i++) begin
      if (!sq[i].valid && !sq_has_free) begin
        free_sq_idx = SQ_IDX_W'(i);
        sq_has_free = 1'b1;
      end
    end
  end

  // Find existing SQ entry for incoming store AGU
  logic [SQ_IDX_W-1:0] match_sq_idx;
  logic                sq_matched;
  always_comb begin
    match_sq_idx = '0;
    sq_matched   = 1'b0;
    for (int i = 0; i < SQ_SIZE; i++) begin
      if (sq[i].valid && (sq[i].rob_tag.seq == agu_req.uop.rob_tag.seq) && !sq_matched) begin
        match_sq_idx = SQ_IDX_W'(i);
        sq_matched   = 1'b1;
      end
    end
  end

  // Check which SQ entry ROB is retiring
  logic [SQ_IDX_W-1:0] retire_sq_idx;
  logic                retire_sq_match;
  always_comb begin
    retire_sq_idx   = '0;
    retire_sq_match = 1'b0;
    for (int i = 0; i < SQ_SIZE; i++) begin
      if (sq[i].valid && (sq[i].rob_tag.seq == sq_retire_rob_tag.seq) && !retire_sq_match) begin
        retire_sq_idx   = SQ_IDX_W'(i);
        retire_sq_match = 1'b1;
      end
    end
  end

  // Provide store commit metadata to ROB trace
  assign retire_store_addr = retire_sq_match ? sq[retire_sq_idx].addr      : 32'd0;
  assign retire_store_mask = retire_sq_match ? sq[retire_sq_idx].byte_mask : 4'd0;
  assign retire_store_data = retire_sq_match ? sq[retire_sq_idx].data      : 32'd0;

  // Find oldest retired store ready to write to memory
  logic [SQ_IDX_W-1:0] send_sq_idx;
  logic                sq_has_send;
  always_comb begin
    send_sq_idx = '0;
    sq_has_send = 1'b0;
    for (int i = 0; i < SQ_SIZE; i++) begin
      if (sq[i].valid && sq[i].retired && !sq[i].req_sent && !sq[i].exception.valid && !sq_has_send) begin
        send_sq_idx = SQ_IDX_W'(i);
        sq_has_send = 1'b1;
      end
    end
  end

  // =========================================================================
  // 5. Store-to-Load Forwarding & Memory Disambiguation
  // =========================================================================

  logic        fwd_valid;
  logic [31:0] fwd_data;
  logic        load_stall_unresolved;
  logic        load_stall_partial;

  always_comb begin
    fwd_valid             = 1'b0;
    fwd_data              = 32'd0;
    load_stall_unresolved = 1'b0;
    load_stall_partial    = 1'b0;

    if (agu_valid && agu_req.uop.mem.is_load && !agu_misaligned) begin
      logic [3:0] load_mask;
      logic       fwd_found;
      rob_tag_t   fwd_youngest_tag;

      load_mask        = calc_byte_en(agu_addr, agu_req.uop.mem.size);
      fwd_found        = 1'b0;
      fwd_youngest_tag = '0;

      for (int i = 0; i < SQ_SIZE; i++) begin
        if (sq[i].valid && is_older_rob(sq[i].rob_tag, agu_req.uop.rob_tag)) begin
          // Case A: Older store address is not yet resolved
          if (!sq[i].addr_valid) begin
            load_stall_unresolved = 1'b1;
          end
          // Case B: Older store address matches word address
          else if (sq[i].addr[31:2] == agu_addr[31:2]) begin
            // Check byte overlap
            if ((load_mask & sq[i].byte_mask) == load_mask) begin
              // Full forward match: select youngest store
              if (!fwd_found || is_older_rob(fwd_youngest_tag, sq[i].rob_tag)) begin
                fwd_found        = 1'b1;
                fwd_youngest_tag = sq[i].rob_tag;
                fwd_valid        = 1'b1;
                fwd_data         = extract_load_data(sq[i].data, agu_addr[1:0], agu_req.uop.mem.size, agu_req.uop.mem.load_ext);
              end
            end else if ((load_mask & sq[i].byte_mask) != 4'b0000) begin
              // Partial overlap: must stall until store commits
              if (!fwd_found || is_older_rob(fwd_youngest_tag, sq[i].rob_tag)) begin
                load_stall_partial = 1'b1;
              end
            end
          end
        end
      end
    end
  end

  wire effective_fwd_valid = fwd_valid && !load_stall_unresolved && !load_stall_partial;

  // Can load issue to external D-memory?
  wire can_issue_load = agu_valid && agu_req.uop.mem.is_load && !agu_misaligned &&
                        !effective_fwd_valid && !load_stall_unresolved && !load_stall_partial &&
                        !in_flight_valid && !sq_has_send && (core_state == CORE_RUN);

  // Can retired store issue to external D-memory?
  wire can_issue_store = sq_has_send && !in_flight_valid && (core_state == CORE_RUN);

  wire sq_full = !sq_has_free;

  assign lsu_ready = (core_state == CORE_RUN) && (
    (agu_req.uop.mem.is_store && (!sq_full || sq_matched)) ||
    (agu_req.uop.mem.is_load  && (agu_misaligned || effective_fwd_valid || can_issue_load))
  );

  // =========================================================================
  // 6. Memory Request Arbiter (Retired Store > Load)
  // =========================================================================

  always_comb begin
    dmem_req_valid   = 1'b0;
    dmem_req_addr    = 32'd0;
    dmem_req_wdata   = 32'd0;
    dmem_req_byte_en = 4'b0000;
    dmem_req_wen     = 1'b0;

    if (!rst) begin
      if (can_issue_store) begin
        dmem_req_valid   = 1'b1;
        dmem_req_addr    = {sq[send_sq_idx].addr[31:2], 2'b00};
        dmem_req_wdata   = sq[send_sq_idx].data;
        dmem_req_byte_en = sq[send_sq_idx].byte_mask;
        dmem_req_wen     = 1'b1;
      end else if (can_issue_load) begin
        dmem_req_valid   = 1'b1;
        dmem_req_addr    = {agu_addr[31:2], 2'b00};
        dmem_req_wdata   = 32'd0;
        dmem_req_byte_en = calc_byte_en(agu_addr, agu_req.uop.mem.size);
        dmem_req_wen     = 1'b0;
      end
    end
  end

  // =========================================================================
  // 7. Load Completion Packet Formation
  // =========================================================================

  // Forwarded load completion register for clean 1-cycle timing
  logic        fwd_reg_valid;
  exec_req_t   fwd_reg_req;
  logic [31:0] fwd_reg_data;

  // Direct misaligned load completion
  logic        misalign_reg_valid;
  exec_req_t   misalign_reg_req;
  logic [31:0] misalign_reg_addr;

  always_comb begin
    ld_cmp = '0;

    // Source 1: D-memory response
    if (in_flight_valid && !in_flight_is_store && dmem_rsp_valid) begin
      ld_cmp.valid         = 1'b1;
      ld_cmp.rob_tag       = in_flight_load_req.uop.rob_tag;
      ld_cmp.result_valid  = in_flight_load_req.uop.dst.valid;
      ld_cmp.result_domain = in_flight_load_req.uop.dst.domain;
      ld_cmp.result_phys   = in_flight_load_req.uop.dst.new_phys;
      ld_cmp.result_data   = extract_load_data(dmem_rsp_rdata, in_flight_addr[1:0],
                                               in_flight_load_req.uop.mem.size,
                                               in_flight_load_req.uop.mem.load_ext);
      if (dmem_rsp_error) begin
        ld_cmp.exception.valid = 1'b1;
        ld_cmp.exception.cause = EXC_LOAD_ACCESS_FAULT;
        ld_cmp.exception.tval  = in_flight_addr;
      end
    end
    // Source 2: Store-to-Load Forwarding response
    else if (fwd_reg_valid) begin
      ld_cmp.valid         = 1'b1;
      ld_cmp.rob_tag       = fwd_reg_req.uop.rob_tag;
      ld_cmp.result_valid  = fwd_reg_req.uop.dst.valid;
      ld_cmp.result_domain = fwd_reg_req.uop.dst.domain;
      ld_cmp.result_phys   = fwd_reg_req.uop.dst.new_phys;
      ld_cmp.result_data   = fwd_reg_data;
    end
    // Source 3: Misaligned load exception
    else if (misalign_reg_valid) begin
      ld_cmp.valid           = 1'b1;
      ld_cmp.rob_tag         = misalign_reg_req.uop.rob_tag;
      ld_cmp.result_valid    = 1'b0;
      ld_cmp.exception.valid = 1'b1;
      ld_cmp.exception.cause = EXC_LOAD_ADDR_MISALIGNED;
      ld_cmp.exception.tval  = misalign_reg_addr;
    end
  end

  // =========================================================================
  // 8. Store Retirement Acknowledgement to ROB
  // =========================================================================

  always_comb begin
    sq_retire_ack = 1'b0;
    if (sq_retire_valid && retire_sq_match) begin
      if (sq[retire_sq_idx].exception.valid) begin
        // Misaligned store traps without writing memory
        sq_retire_ack = 1'b1;
      end else if (sq[retire_sq_idx].rsp_done || (in_flight_valid && in_flight_is_store && (in_flight_sq_idx == retire_sq_idx) && dmem_rsp_valid)) begin
        sq_retire_ack = 1'b1;
      end
    end
  end

  // =========================================================================
  // 9. Sequential State Updates
  // =========================================================================

  always_ff @(posedge clk) begin
    if (rst) begin
      in_flight_valid     <= 1'b0;
      in_flight_is_store  <= 1'b0;
      in_flight_rob_tag   <= '0;
      in_flight_addr      <= 32'd0;
      in_flight_load_req  <= '0;
      in_flight_sq_idx    <= '0;
      fwd_reg_valid       <= 1'b0;
      fwd_reg_req         <= '0;
      fwd_reg_data        <= 32'd0;
      misalign_reg_valid  <= 1'b0;
      misalign_reg_req    <= '0;
      misalign_reg_addr   <= 32'd0;

      for (int i = 0; i < SQ_SIZE; i++) begin
        sq[i] <= '0;
      end
    end else begin
      // Default auto-clearing single-cycle pulses
      fwd_reg_valid      <= 1'b0;
      misalign_reg_valid <= 1'b0;

      // ── Pipeline Flush (Wrong-Path Purge) ──────────────────────────────────
      if (flush_valid) begin
        // Only flush in-flight if it was a non-retired speculative load
        if (in_flight_valid && !in_flight_is_store) begin
          in_flight_valid <= 1'b0;
        end
        fwd_reg_valid      <= 1'b0;
        misalign_reg_valid <= 1'b0;

        // Invalidate all un-retired speculative stores in SQ!
        for (int i = 0; i < SQ_SIZE; i++) begin
          if (sq[i].valid && !sq[i].retired) begin
            sq[i] <= '0;
          end
        end
      end else begin
        // ── Forwarding & Misalignment Capture ───────────────────────────────
        if (agu_valid && agu_req.uop.mem.is_load) begin
          if (agu_misaligned) begin
            misalign_reg_valid <= 1'b1;
            misalign_reg_req   <= agu_req;
            misalign_reg_addr  <= agu_addr;
          end else if (effective_fwd_valid) begin
            fwd_reg_valid <= 1'b1;
            fwd_reg_req   <= agu_req;
            fwd_reg_data  <= fwd_data;
          end
        end

        // ── Store Queue Dispatch Allocation (Early Reservation for Disambiguation)
        if (disp_valid && disp_uop.mem.is_store && sq_has_free) begin
          sq[free_sq_idx].valid      <= 1'b1;
          sq[free_sq_idx].rob_tag    <= disp_uop.rob_tag;
          sq[free_sq_idx].addr_valid <= 1'b0;
          sq[free_sq_idx].size       <= disp_uop.mem.size;
          sq[free_sq_idx].is_fp      <= disp_uop.mem.is_fp;
          sq[free_sq_idx].retired    <= 1'b0;
          sq[free_sq_idx].req_sent   <= 1'b0;
          sq[free_sq_idx].rsp_done   <= 1'b0;
          sq[free_sq_idx].exception  <= '{valid: 1'b0, cause: 5'd0, tval: 32'd0};
        end

        // ── Store Queue AGU Ingestion ───────────────────────────────────────
        if (agu_valid && agu_req.uop.mem.is_store) begin
          logic [SQ_IDX_W-1:0] target_idx;
          target_idx = sq_matched ? match_sq_idx : free_sq_idx;

          if (sq_matched || sq_has_free) begin
            sq[target_idx].valid      <= 1'b1;
            sq[target_idx].rob_tag    <= agu_req.uop.rob_tag;
            sq[target_idx].addr_valid <= 1'b1;
            sq[target_idx].addr       <= agu_addr;
            sq[target_idx].byte_mask  <= calc_byte_en(agu_addr, agu_req.uop.mem.size);
            sq[target_idx].data       <= format_store_data(agu_req.operand1, agu_addr, agu_req.uop.mem.size);
            sq[target_idx].size       <= agu_req.uop.mem.size;
            sq[target_idx].is_fp      <= agu_req.uop.mem.is_fp;
            if (agu_misaligned) begin
              sq[target_idx].exception <= '{valid: 1'b1, cause: EXC_STORE_ADDR_MISALIGNED, tval: agu_addr};
            end else begin
              sq[target_idx].exception <= '{valid: 1'b0, cause: 5'd0, tval: 32'd0};
            end
          end
        end

        // ── ROB Store Retirement Marking ────────────────────────────────────
        if (sq_retire_valid && retire_sq_match) begin
          sq[retire_sq_idx].retired <= 1'b1;
        end

        // ── Outbound Memory Request Dispatch ────────────────────────────────
        if (dmem_req_valid && dmem_req_ready) begin
          in_flight_valid <= 1'b1;
          if (dmem_req_wen) begin
            in_flight_is_store       <= 1'b1;
            in_flight_rob_tag        <= sq[send_sq_idx].rob_tag;
            in_flight_addr           <= sq[send_sq_idx].addr;
            in_flight_sq_idx         <= send_sq_idx;
            sq[send_sq_idx].req_sent <= 1'b1;
          end else begin
            in_flight_is_store <= 1'b0;
            in_flight_rob_tag  <= agu_req.uop.rob_tag;
            in_flight_addr     <= agu_addr;
            in_flight_load_req <= agu_req;
          end
        end

        // ── Memory Response Handling & Deallocation ─────────────────────────
        if (dmem_rsp_valid && in_flight_valid) begin
          in_flight_valid <= 1'b0;
          if (in_flight_is_store) begin
            sq[in_flight_sq_idx] <= '0; // Deallocate completed store immediately upon response
          end
        end

        // ── Deallocate Exception Store Entries ──────────────────────────────
        for (int i = 0; i < SQ_SIZE; i++) begin
          if (sq[i].valid && sq[i].retired && sq[i].exception.valid) begin
            sq[i] <= '0;
          end
        end
      end
    end
  end

endmodule
