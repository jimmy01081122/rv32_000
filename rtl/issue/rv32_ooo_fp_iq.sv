// rv32_ooo_fp_iq.sv — Floating-Point Issue Queue
// 4 entries, 3-source wakeup (FMA), multi-completion snooping (Int, Load, and FP)
// architecture_spec.md §17 | uop_spec.md §17

module rv32_ooo_fp_iq
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

  // Issue interface (to FP PRF read / execution cluster)
  output logic         issue_valid,
  output renamed_uop_t issue_uop,
  input  logic         issue_ready,

  // Flush on rollback / recovery
  input  logic         flush_valid,
  input  rob_tag_t     flush_rob_tag
);

  typedef struct packed {
    logic         valid;
    renamed_uop_t uop;
    logic         src0_ready;
    logic         src1_ready;
    logic         src2_ready;
  } fp_iq_entry_t;

  fp_iq_entry_t entries [FP_IQ_ENTRIES-1:0];

  // Count number of valid entries
  logic [2:0] num_valid;
  always_comb begin
    num_valid = '0;
    for (int i = 0; i < FP_IQ_ENTRIES; i++) begin
      if (entries[i].valid) num_valid = num_valid + 3'd1;
    end
  end

  assign dispatch_ready = (num_valid < FP_IQ_ENTRIES[2:0]) && (core_state == CORE_RUN);

  // Ready vector (an entry is ready when valid and all 3 sources are ready)
  logic [FP_IQ_ENTRIES-1:0] ready_mask;
  always_comb begin
    for (int i = 0; i < FP_IQ_ENTRIES; i++) begin
      ready_mask[i] = entries[i].valid &&
                      entries[i].src0_ready &&
                      entries[i].src1_ready &&
                      entries[i].src2_ready &&
                      (core_state == CORE_RUN);
    end
  end

  // Oldest-ready-first priority selection
  logic [1:0] selected_idx;
  logic       can_issue;

  always_comb begin
    selected_idx = 2'd0;
    can_issue    = 1'b0;
    for (int i = 0; i < FP_IQ_ENTRIES; i++) begin
      if (ready_mask[i] && !can_issue) begin
        selected_idx = 2'(i);
        can_issue    = 1'b1;
      end
    end
  end

  assign issue_valid = can_issue;
  assign issue_uop   = entries[selected_idx].uop;

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

  // Compute dispatched entry with same-cycle completion bypassing
  fp_iq_entry_t disp_entry;
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
    disp_entry.src2_ready = src_is_ready(dispatch_uop.src2) ||
                            snoop_wake(dispatch_uop.src2.kind, dispatch_uop.src2.phys, int_cmp) ||
                            snoop_wake(dispatch_uop.src2.kind, dispatch_uop.src2.phys, ld_cmp)  ||
                            snoop_wake(dispatch_uop.src2.kind, dispatch_uop.src2.phys, fp_cmp);
  end

  // Next state generation
  fp_iq_entry_t next_entries [FP_IQ_ENTRIES-1:0];

  always_comb begin
    logic [1:0] insert_pos;
    if (issue_valid && issue_ready) begin
      insert_pos = 2'(num_valid - 3'd1);
    end else begin
      insert_pos = 2'(num_valid);
    end

    for (int i = 0; i < FP_IQ_ENTRIES; i++) begin
      // Step 1: Compaction candidate
      fp_iq_entry_t candidate;
      if (issue_valid && issue_ready && i >= selected_idx) begin
        if (i < FP_IQ_ENTRIES - 1) begin
          candidate = entries[i+1];
        end else begin
          candidate = '0;
        end
      end else begin
        candidate = entries[i];
      end

      // Step 2: Apply wakeup snooping to candidate
      if (candidate.valid) begin
        if (snoop_wake(candidate.uop.src0.kind, candidate.uop.src0.phys, int_cmp) ||
            snoop_wake(candidate.uop.src0.kind, candidate.uop.src0.phys, ld_cmp)  ||
            snoop_wake(candidate.uop.src0.kind, candidate.uop.src0.phys, fp_cmp)) begin
          candidate.src0_ready = 1'b1;
        end
        if (snoop_wake(candidate.uop.src1.kind, candidate.uop.src1.phys, int_cmp) ||
            snoop_wake(candidate.uop.src1.kind, candidate.uop.src1.phys, ld_cmp)  ||
            snoop_wake(candidate.uop.src1.kind, candidate.uop.src1.phys, fp_cmp)) begin
          candidate.src1_ready = 1'b1;
        end
        if (snoop_wake(candidate.uop.src2.kind, candidate.uop.src2.phys, int_cmp) ||
            snoop_wake(candidate.uop.src2.kind, candidate.uop.src2.phys, ld_cmp)  ||
            snoop_wake(candidate.uop.src2.kind, candidate.uop.src2.phys, fp_cmp)) begin
          candidate.src2_ready = 1'b1;
        end
      end

      // Step 3: Dispatch insertion
      if (dispatch_valid && dispatch_ready && 2'(i) == insert_pos) begin
        next_entries[i] = disp_entry;
      end else begin
        next_entries[i] = candidate;
      end
    end
  end

  // Sequential updates
  always_ff @(posedge clk) begin
    if (rst || flush_valid) begin
      for (int i = 0; i < FP_IQ_ENTRIES; i++) begin
        entries[i] <= '0;
      end
    end else begin
      entries <= next_entries;
    end
  end

endmodule
