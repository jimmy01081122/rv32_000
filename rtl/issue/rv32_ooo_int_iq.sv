// rv32_ooo_int_iq.sv — Integer Issue Queue (AP3B Static-Slot Non-Compacting Architecture)
// 8 static slots, 2-source wakeup, multi-completion snooping (Int, Load, and FP)
// Tournament-based oldest-ready-first selection tree using modular ROB sequence tags
// architecture_spec.md §17 | uop_spec.md §17

module rv32_ooo_int_iq
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic        clk,
  input  logic        rst,          // synchronous active-high

  input  core_state_e core_state,

  // Dispatch interface (from Rename)
  input  logic         dispatch_valid,
  input  renamed_uop_t dispatch_uop,
  output logic         dispatch_ready,

  // Wakeup snooping: all completion buses (§17.2)
  input  completion_t  int_cmp,
  input  completion_t  ld_cmp,
  input  completion_t  fp_cmp,

  // Issue interface (to PRF read / execution cluster)
  output logic         issue_valid,
  output renamed_uop_t issue_uop,
  input  logic         issue_ready,

  // Flush on rollback / recovery
  input  logic         flush_valid,
  input  rob_tag_t     flush_rob_tag,

  // Functional unit status
  input  logic         divider_busy
);

  typedef struct packed {
    logic         valid;
    renamed_uop_t uop;
    logic         src0_ready;
    logic         src1_ready;
  } iq_entry_t;

  iq_entry_t entries [INT_IQ_ENTRIES-1:0];

  // Helper to determine if ROB tag a is strictly older than ROB tag b using modular distance
  function automatic logic is_older_rob(input rob_tag_t a, input rob_tag_t b);
    logic [ROB_SEQ_WIDTH-1:0] diff;
    diff = b.seq - a.seq;
    return (a.seq != b.seq) && (diff < (1 << (ROB_SEQ_WIDTH-1)));
  endfunction

  // Helper function to check if a completion bus wakes up a source
  function automatic logic snoop_wake(
    input src_kind_e   kind,
    input phys_reg_t   phys,
    input completion_t cmp
  );
    snoop_wake = 1'b0;
    if (cmp.valid && cmp.result_valid) begin
      if (cmp.result_domain == REG_INT && kind == SRC_INT_REG && phys == cmp.result_phys) snoop_wake = 1'b1;
      if (cmp.result_domain == REG_FP  && kind == SRC_FP_REG  && phys == cmp.result_phys) snoop_wake = 1'b1;
    end
  endfunction

  // =========================================================================
  // 1. Allocation & Dispatch Readiness (Static Free Mask)
  // =========================================================================

  logic [INT_IQ_ENTRIES-1:0] free_mask;
  logic [2:0]                alloc_idx;
  logic                      has_free_slot;

  always_comb begin
    for (int i = 0; i < INT_IQ_ENTRIES; i++) begin
      free_mask[i] = !entries[i].valid;
    end
    has_free_slot = |free_mask;

    // Lowest-index free slot priority encoder
    alloc_idx = 3'd0;
    for (int i = INT_IQ_ENTRIES-1; i >= 0; i--) begin
      if (free_mask[i]) begin
        alloc_idx = 3'(i);
      end
    end
  end

  // Dispatch ready is purely a function of registered entry validity (zero issue-to-dispatch loop)
  assign dispatch_ready = has_free_slot && (core_state == CORE_RUN);

  // Form newly dispatched entry with same-cycle completion bypassing
  iq_entry_t disp_entry;
  always_comb begin
    disp_entry.valid = 1'b1;
    disp_entry.uop   = dispatch_uop;
    disp_entry.src0_ready = src_is_ready(dispatch_uop.src0) ||
                            snoop_wake(dispatch_uop.src0.kind, dispatch_uop.src0.phys, int_cmp) ||
                            snoop_wake(dispatch_uop.src0.kind, dispatch_uop.src0.phys, ld_cmp)  ||
                            snoop_wake(dispatch_uop.src0.kind, dispatch_uop.src0.phys, fp_cmp);
    disp_entry.src1_ready = src_is_ready(dispatch_uop.src1) ||
                            snoop_wake(dispatch_uop.src1.kind, dispatch_uop.src1.phys, int_cmp) ||
                            snoop_wake(dispatch_uop.src1.kind, dispatch_uop.src1.phys, ld_cmp)  ||
                            snoop_wake(dispatch_uop.src1.kind, dispatch_uop.src1.phys, fp_cmp);
  end

  // =========================================================================
  // 2. Issue Readiness Evaluation
  // =========================================================================

  logic [INT_IQ_ENTRIES-1:0] ready_mask;

  always_comb begin
    for (int i = 0; i < INT_IQ_ENTRIES; i++) begin
      logic older_store_in_iq;
      logic fu_available;

      older_store_in_iq = 1'b0;
      if (entries[i].uop.mem.is_load) begin
        for (int j = 0; j < INT_IQ_ENTRIES; j++) begin
          if (entries[j].valid && entries[j].uop.mem.is_store &&
              is_older_rob(entries[j].uop.rob_tag, entries[i].uop.rob_tag)) begin
            older_store_in_iq = 1'b1;
          end
        end
      end

      fu_available = (entries[i].uop.fu_class == FU_INT_DIV) ? !divider_busy : 1'b1;

      ready_mask[i] = entries[i].valid &&
                      entries[i].src0_ready &&
                      entries[i].src1_ready &&
                      !older_store_in_iq &&
                      fu_available &&
                      (core_state == CORE_RUN);
    end
  end

  // =========================================================================
  // 3. Oldest-Ready Tournament Selection Tree
  // =========================================================================

  typedef struct packed {
    logic       valid;
    logic [2:0] idx;
    rob_tag_t   tag;
  } cand_t;

  function automatic cand_t pick_older(input cand_t a, input cand_t b);
    if (!a.valid) begin
      return b;
    end else if (!b.valid) begin
      return a;
    end else begin
      if (is_older_rob(a.tag, b.tag)) begin
        return a;
      end else begin
        return b;
      end
    end
  endfunction

  cand_t l0 [7:0];
  cand_t l1 [3:0];
  cand_t l2 [1:0];
  cand_t winner;

  always_comb begin
    // Level 0: Leaf candidates
    for (int i = 0; i < INT_IQ_ENTRIES; i++) begin
      l0[i].valid = ready_mask[i];
      l0[i].idx   = 3'(i);
      l0[i].tag   = entries[i].uop.rob_tag;
    end

    // Level 1: Pairwise comparisons (4 comparators)
    l1[0] = pick_older(l0[0], l0[1]);
    l1[1] = pick_older(l0[2], l0[3]);
    l1[2] = pick_older(l0[4], l0[5]);
    l1[3] = pick_older(l0[6], l0[7]);

    // Level 2: Semi-final comparisons (2 comparators)
    l2[0] = pick_older(l1[0], l1[1]);
    l2[1] = pick_older(l1[2], l1[3]);

    // Level 3: Tournament Winner (1 comparator)
    winner = pick_older(l2[0], l2[1]);
  end

  assign issue_valid = winner.valid;
  assign issue_uop   = entries[winner.idx].uop;

  // =========================================================================
  // 4. Static Slot Sequential State Update
  // =========================================================================

  always_ff @(posedge clk) begin
    if (rst || flush_valid) begin
      for (int i = 0; i < INT_IQ_ENTRIES; i++) begin
        entries[i] <= '0;
      end
    end else begin
      for (int i = 0; i < INT_IQ_ENTRIES; i++) begin
        // Slot allocated by dispatch
        if (dispatch_valid && dispatch_ready && (3'(i) == alloc_idx)) begin
          entries[i] <= disp_entry;
        end
        // Slot invalidated by issue
        else if (issue_valid && issue_ready && (3'(i) == winner.idx)) begin
          entries[i] <= '0;
        end
        // Resident slot: retain uop and update source readiness via completion snooping
        else if (entries[i].valid) begin
          logic next_src0_ready, next_src1_ready;
          next_src0_ready = entries[i].src0_ready ||
                            snoop_wake(entries[i].uop.src0.kind, entries[i].uop.src0.phys, int_cmp) ||
                            snoop_wake(entries[i].uop.src0.kind, entries[i].uop.src0.phys, ld_cmp)  ||
                            snoop_wake(entries[i].uop.src0.kind, entries[i].uop.src0.phys, fp_cmp);
          next_src1_ready = entries[i].src1_ready ||
                            snoop_wake(entries[i].uop.src1.kind, entries[i].uop.src1.phys, int_cmp) ||
                            snoop_wake(entries[i].uop.src1.kind, entries[i].uop.src1.phys, ld_cmp)  ||
                            snoop_wake(entries[i].uop.src1.kind, entries[i].uop.src1.phys, fp_cmp);
          entries[i].src0_ready <= next_src0_ready;
          entries[i].src1_ready <= next_src1_ready;
        end
      end
    end
  end

  // =========================================================================
  // 5. AP3B Architectural Integrity Assertions
  // =========================================================================
`ifndef SYNTHESIS
  always_ff @(posedge clk) begin
    if (!rst) begin
      // Assert: Invalid entry never issues
      if (issue_valid) begin
        assert (entries[winner.idx].valid)
          else $error("[AP3B Assertion Failed] Issue valid from invalid slot %0d.", winner.idx);
      end

      // Assert: Flushed entry never issues on cycle after flush
      if ($past(!rst && flush_valid)) begin
        assert (!issue_valid)
          else $error("[AP3B Assertion Failed] Issue valid asserted immediately after pipeline flush.");
      end

      // Assert: One slot cannot be allocated twice
      if (dispatch_valid && dispatch_ready) begin
        assert (!entries[alloc_idx].valid)
          else $error("[AP3B Assertion Failed] Allocated slot %0d was already valid.", alloc_idx);
      end
    end
  end
`endif

endmodule
