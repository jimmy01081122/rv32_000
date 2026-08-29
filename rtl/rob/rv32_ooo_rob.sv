// rv32_ooo_rob.sv — Reorder Buffer (ROB)
// Circular buffer (16 entries), in-order retirement, safe store retirement protocol, commit trace
// Architecture Spec §15, §23, §24, §25, §29 | Uop Spec §20

module rv32_ooo_rob
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic        clk,
  input  logic        rst,          // synchronous active-high

  output core_state_e core_state,

  // dmem pending record (§15.2) — alias guard
  input  dmem_pending_t dmem_pending,

  // Allocation from rename
  input  logic          alloc_valid,
  input  renamed_uop_t  alloc_uop,
  output logic          alloc_ready,
  output rob_tag_t      alloc_rob_tag,

  // Completion buses (§24.3)
  input  completion_t   int_cmp,
  input  completion_t   ld_cmp,
  input  completion_t   fp_cmp,

  // Store retirement handshake with LSU
  output logic          sq_retire_valid,
  output rob_tag_t      sq_retire_rob_tag,
  input  logic          sq_retire_ack,
  input  logic [31:0]   retire_store_addr,
  input  logic [3:0]    retire_store_mask,
  input  logic [31:0]   retire_store_data,

  // Retirement outputs
  output logic          retire_valid,
  output rob_entry_t    retire_entry,
  output commit_trace_t commit_trace,

  // FP accrued exception flags to CSR
  output logic          retire_fp_valid,
  output fp_flags_t     retire_fflags_delta,

  // Branch misprediction rollback
  output logic          rollback_valid,
  output rob_tag_t      rollback_rob_tag,

  // Precise trap
  output logic          trap_valid,
  output logic          mret_valid,
  output logic [31:0]   trap_pc,
  output logic [31:0]   trap_cause,
  output logic [31:0]   trap_tval
);

  // =========================================================================
  // 1. Storage & Pointers
  // =========================================================================

  typedef logic [ROB_IDX_W-1:0] rob_idx_t;

  rob_entry_t entries [ROB_ENTRIES-1:0];
  rob_idx_t                 head, tail;
  logic [ROB_SEQ_WIDTH-1:0] next_seq;
  logic [4:0]               rob_count;

  core_state_e current_state;
  assign core_state = current_state;

  // In-flight serializing instruction check
  logic in_flight_serializing;
  always_comb begin
    in_flight_serializing = 1'b0;
    for (int i = 0; i < ROB_ENTRIES; i++) begin
      if (entries[i].valid && entries[i].serializing && !entries[i].completed) begin
        in_flight_serializing = 1'b1;
      end
    end
  end

  wire rob_full  = (rob_count == ROB_ENTRIES[4:0]);
  wire rob_empty = (rob_count == 5'd0);

  assign alloc_ready   = (alloc_uop.serializing ? rob_empty : (!rob_full && !in_flight_serializing)) && (current_state == CORE_RUN);
  assign alloc_rob_tag = '{seq: next_seq, idx: tail};

  // Monotonic commit trace event order
  logic [63:0] event_counter;

  // =========================================================================
  // 2. Head Entry Inspection & Retirement Protocol
  // =========================================================================

  rob_entry_t head_entry;
  assign head_entry = entries[head];

  wire rob_head_valid     = !rob_empty && head_entry.valid;
  wire rob_head_completed = rob_head_valid && head_entry.completed;
  wire rob_head_exception = rob_head_completed && head_entry.exception.valid;

  // Store retirement handshake
  assign sq_retire_valid   = rob_head_completed && !rob_head_exception && head_entry.is_store && (current_state == CORE_RUN);
  assign sq_retire_rob_tag = head_entry.tag;

  wire store_ready_to_retire = !head_entry.is_store || sq_retire_ack;

  // Retirement signals
  wire can_retire = rob_head_completed && !rob_head_exception && store_ready_to_retire && (current_state == CORE_RUN);

  assign retire_valid        = can_retire;
  assign retire_entry        = head_entry;
  assign retire_fp_valid     = can_retire && head_entry.fp_flags_valid;
  assign retire_fflags_delta = head_entry.fp_flags;

  // Trap / MRET signals
  wire is_trap    = rob_head_completed && rob_head_exception && (current_state == CORE_RUN);
  wire is_mret    = can_retire && (head_entry.op == UOP_MRET);
  wire is_fence_i = can_retire && (head_entry.op == UOP_FENCE_I);

  assign trap_valid = is_trap;
  assign mret_valid = is_mret || is_fence_i;
  assign trap_pc    = head_entry.pc;
  assign trap_cause = {27'd0, head_entry.exception.cause};
  assign trap_tval  = head_entry.exception.tval;

  // Rollback on branch misprediction at retirement
  assign rollback_valid   = can_retire && head_entry.branch_mispredict;
  assign rollback_rob_tag = head_entry.tag;

  // =========================================================================
  // 3. Per-Entry Storage & Next-State Logic
  // =========================================================================

  for (genvar i = 0; i < ROB_ENTRIES; i++) begin : gen_rob_entries
    rob_entry_t entry_next;

    always_comb begin
      entry_next = entries[i];

      // --- Completion Snooping (Integer execution completion bus) ---
      if (int_cmp.valid && (rob_idx_t'(i) == int_cmp.rob_tag.idx) && entries[i].valid && (entries[i].tag.seq == int_cmp.rob_tag.seq)) begin
        entry_next.completed         = 1'b1;
        entry_next.result_data       = int_cmp.result_data;
        entry_next.branch_resolved   = int_cmp.branch_valid;
        entry_next.branch_mispredict = int_cmp.branch_mispredict;
        entry_next.branch_target     = int_cmp.branch_target;
        if (int_cmp.exception.valid) begin
          entry_next.exception = int_cmp.exception;
        end
      end

      // --- Completion Snooping (Load response completion bus) ---
      if (ld_cmp.valid && (rob_idx_t'(i) == ld_cmp.rob_tag.idx) && entries[i].valid && (entries[i].tag.seq == ld_cmp.rob_tag.seq)) begin
        entry_next.completed   = 1'b1;
        entry_next.result_data = ld_cmp.result_data;
        if (ld_cmp.exception.valid) begin
          entry_next.exception = ld_cmp.exception;
        end
      end

      // --- Completion Snooping (FP execution completion bus) ---
      if (fp_cmp.valid && (rob_idx_t'(i) == fp_cmp.rob_tag.idx) && entries[i].valid && (entries[i].tag.seq == fp_cmp.rob_tag.seq)) begin
        entry_next.completed      = 1'b1;
        entry_next.result_data    = fp_cmp.result_data;
        entry_next.fp_flags_valid = 1'b1;
        entry_next.fp_flags       = fp_cmp.fp_flags;
        if (fp_cmp.exception.valid) begin
          entry_next.exception    = fp_cmp.exception;
        end
      end

      // --- Retirement Execution (In-order at head) ---
      if (can_retire && !head_entry.branch_mispredict && (rob_idx_t'(i) == head)) begin
        entry_next.valid = 1'b0;
      end

      // --- Allocation Execution (Dispatch insertion at tail) ---
      if (alloc_valid && alloc_ready && !(can_retire && head_entry.branch_mispredict) && !is_trap && (rob_idx_t'(i) == tail)) begin
        entry_next                   = '0;
        entry_next.valid             = 1'b1;
        entry_next.completed         = alloc_uop.exception.valid;
        entry_next.tag               = '{seq: next_seq, idx: rob_idx_t'(i)};
        entry_next.pc                = alloc_uop.pc;
        entry_next.insn              = alloc_uop.insn;
        entry_next.op                = alloc_uop.op;
        entry_next.dst               = alloc_uop.dst;
        entry_next.is_branch         = (alloc_uop.fu_class == FU_BRANCH);
        entry_next.is_load           = alloc_uop.lq_valid;
        entry_next.is_store          = alloc_uop.sq_valid;
        entry_next.is_csr            = (alloc_uop.fu_class == FU_CSR_SERIAL);
        entry_next.serializing       = alloc_uop.serializing;
        entry_next.exception         = alloc_uop.exception;
        entry_next.lq_valid          = alloc_uop.lq_valid;
        entry_next.lq_tag            = alloc_uop.lq_tag;
        entry_next.sq_valid          = alloc_uop.sq_valid;
        entry_next.sq_tag            = alloc_uop.sq_tag;
      end
    end

    always_ff @(posedge clk) begin
      if (rst || is_trap || is_mret || is_fence_i || (can_retire && head_entry.branch_mispredict)) begin
        entries[i] <= '0;
      end else begin
        entries[i] <= entry_next;
      end
    end
  end

  // =========================================================================
  // 4. Control State & Pointer Tracking
  // =========================================================================

  always_ff @(posedge clk) begin
    if (rst) begin
      head          <= '0;
      tail          <= '0;
      next_seq      <= '0;
      rob_count     <= '0;
      current_state <= CORE_RUN;
      event_counter <= '0;
      commit_trace  <= '0;
    end else if (is_trap || is_mret || is_fence_i || (can_retire && head_entry.branch_mispredict)) begin
      head          <= '0;
      tail          <= '0;
      rob_count     <= '0;

      // Trace on trap
      commit_trace <= '0;
      if (is_trap) begin
        commit_trace.trap_valid  <= 1'b1;
        commit_trace.event_order <= event_counter;
        commit_trace.pc          <= head_entry.pc;
        commit_trace.insn        <= head_entry.insn;
        commit_trace.trap_cause  <= {27'd0, head_entry.exception.cause};
        commit_trace.trap_tval   <= head_entry.exception.tval;
        event_counter            <= event_counter + 64'd1;
      end else if (can_retire) begin
        // Mispredicted branch, MRET, or FENCE.I commit trace
        commit_trace.retire_valid  <= 1'b1;
        commit_trace.event_order   <= event_counter;
        commit_trace.pc            <= head_entry.pc;
        commit_trace.insn          <= head_entry.insn;
        commit_trace.int_dst_valid <= head_entry.dst.valid && (head_entry.dst.domain == REG_INT);
        commit_trace.int_dst_arch  <= head_entry.dst.arch;
        commit_trace.int_dst_data  <= head_entry.result_data;
        commit_trace.fp_dst_valid  <= head_entry.dst.valid && (head_entry.dst.domain == REG_FP);
        commit_trace.fp_dst_arch   <= head_entry.dst.arch;
        commit_trace.fp_dst_data   <= head_entry.result_data;
        commit_trace.fflags        <= head_entry.fp_flags;
        event_counter              <= event_counter + 64'd1;
      end

      if (is_trap) begin
        current_state <= TRAP_RECOVERY;
      end else if (is_mret || is_fence_i) begin
        current_state <= MRET_RECOVERY;
      end else begin
        current_state <= BRANCH_ROLLBACK;
      end
    end else begin
      // --- Commit Trace Logging ---
      commit_trace <= '0;
      if (can_retire) begin
        commit_trace.retire_valid  <= 1'b1;
        commit_trace.event_order   <= event_counter;
        commit_trace.pc            <= head_entry.pc;
        commit_trace.insn          <= head_entry.insn;
        commit_trace.int_dst_valid <= head_entry.dst.valid && (head_entry.dst.domain == REG_INT);
        commit_trace.int_dst_arch  <= head_entry.dst.arch;
        commit_trace.int_dst_data  <= head_entry.result_data;
        commit_trace.fp_dst_valid  <= head_entry.dst.valid && (head_entry.dst.domain == REG_FP);
        commit_trace.fp_dst_arch   <= head_entry.dst.arch;
        commit_trace.fp_dst_data   <= head_entry.result_data;
        commit_trace.fflags        <= head_entry.fp_flags;

        // Memory store commit trace
        if (head_entry.is_store) begin
          commit_trace.mem_valid     <= 1'b1;
          commit_trace.mem_addr      <= retire_store_addr;
          commit_trace.mem_byte_mask <= retire_store_mask;
          commit_trace.mem_wdata     <= retire_store_data;
        end

        event_counter <= event_counter + 64'd1;
      end

      // --- State Transitions ---
      case (current_state)
        CORE_RUN: begin
          if (is_mret) begin
            current_state <= MRET_RECOVERY;
          end
        end
        BRANCH_ROLLBACK, TRAP_RECOVERY, MRET_RECOVERY: begin
          current_state <= CORE_RUN;
        end
        default: current_state <= CORE_RUN;
      endcase

      // --- Pointer Tracking ---
      if (can_retire) begin
        head <= head + 1'b1;
      end

      if (alloc_valid && alloc_ready) begin
        tail     <= tail + 1'b1;
        next_seq <= next_seq + 12'd1;
      end

      if ((alloc_valid && alloc_ready) && !can_retire) begin
        rob_count <= rob_count + 5'd1;
      end else if (!(alloc_valid && alloc_ready) && can_retire) begin
        rob_count <= rob_count - 5'd1;
      end
    end
  end

endmodule
