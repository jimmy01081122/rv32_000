// rv32_ooo_rename.sv — Dual-Domain Register Renaming Subsystem
// Integer and Floating-Point RAT, RRAT, Free Mask, Ready Table, and dynamic rounding mode resolution
// Architecture Spec §14, §23 | Uop Spec §16

module rv32_ooo_rename
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic        clk,
  input  logic        rst,          // synchronous active-high

  input  core_state_e core_state,

  // Input from frontend (decoded uop)
  input  logic         dec_valid,
  input  decoded_uop_t dec_uop,
  output logic         dec_ready,

  // Output to dispatch / ROB / Issue Queues
  output logic         ren_valid,
  output renamed_uop_t ren_uop,
  input  logic         ren_ready,

  // Completion buses for ready-table update (§14.3)
  input  completion_t  int_cmp,
  input  completion_t  ld_cmp,
  input  completion_t  fp_cmp,

  // Retirement interface for RRAT and free-list deallocation (§14.4)
  input  logic         retire_valid,
  input  rob_entry_t   retire_entry,

  // Branch misprediction rollback
  input  logic         rollback_valid,
  input  rob_tag_t     rollback_rob_tag,

  // Trap/MRET recovery
  input  logic         trap_recovery_valid,
  input  logic         mret_recovery_valid,

  // Dynamic FP rounding mode from CSR
  input  fp_rm_e       frm
);

  localparam int FREE_LIST_SIZE = INT_PRF_ENTRIES - ARCH_REGS; // 16

  // =========================================================================
  // 1. Integer Domain Tables
  // =========================================================================

  phys_reg_t int_rat  [ARCH_REGS-1:0];
  phys_reg_t int_rrat [ARCH_REGS-1:0];
  logic [INT_PRF_ENTRIES-1:0] int_ready_table;
  logic [INT_PRF_ENTRIES-1:0] int_free_mask;

  // =========================================================================
  // 2. Floating-Point Domain Tables
  // =========================================================================

  phys_reg_t fp_rat  [ARCH_REGS-1:0];
  phys_reg_t fp_rrat [ARCH_REGS-1:0];
  logic [FP_PRF_ENTRIES-1:0] fp_ready_table;
  logic [FP_PRF_ENTRIES-1:0] fp_free_mask;

  // Priority encoder functions to find first free physical register
  function automatic phys_reg_t find_first_free_int(input logic [INT_PRF_ENTRIES-1:0] mask);
    phys_reg_t result;
    result = 6'd0;
    // Scan high-to-low: lowest free register (min p >= 1) wins by overriding
    for (int p = INT_PRF_ENTRIES-1; p >= 1; p--) begin
      if (mask[p]) result = phys_reg_t'(p);
    end
    return result;
  endfunction

  function automatic phys_reg_t find_first_free_fp(input logic [FP_PRF_ENTRIES-1:0] mask);
    phys_reg_t result;
    result = 6'd0;
    // Scan high-to-low: lowest free register wins by overriding
    for (int p = FP_PRF_ENTRIES-1; p >= 0; p--) begin
      if (mask[p]) result = phys_reg_t'(p);
    end
    return result;
  endfunction

  wire free_int_available = (int_free_mask != '0);
  wire free_fp_available  = (fp_free_mask != '0);

  wire phys_reg_t allocated_int_phys = find_first_free_int(int_free_mask);
  wire phys_reg_t allocated_fp_phys  = find_first_free_fp(fp_free_mask);

  wire needs_int_phys = dec_uop.dst.valid && (dec_uop.dst.domain == REG_INT) && (dec_uop.dst.arch != 5'd0);
  wire needs_fp_phys  = dec_uop.dst.valid && (dec_uop.dst.domain == REG_FP);

  wire free_dest_available = (!needs_int_phys || free_int_available) && (!needs_fp_phys || free_fp_available);

  // Decode ready if downstream ready and required free list not exhausted
  assign dec_ready = ren_ready && free_dest_available && (core_state == CORE_RUN);

  // =========================================================================
  // 3. Renaming Logic (Comb)
  // =========================================================================

  renamed_uop_t ren_d;

  always_comb begin
    // ── Hoist all branch-local temps to block scope (avoids latch loops) ─────
    phys_reg_t s0_int_p, s0_fp_p, s1_int_p, s1_fp_p, s2_fp_p;
    s0_int_p = '0; s0_fp_p = '0; s1_int_p = '0; s1_fp_p = '0; s2_fp_p = '0;

    ren_d.pc                = dec_uop.pc;
    ren_d.insn              = dec_uop.insn;
    ren_d.fetch             = dec_uop.fetch;
    ren_d.rob_tag           = '0;
    ren_d.op                = dec_uop.op;
    ren_d.fu_class          = dec_uop.fu_class;
    ren_d.imm               = dec_uop.imm;
    ren_d.mem               = dec_uop.mem;
    ren_d.branch            = dec_uop.branch;
    ren_d.csr               = dec_uop.csr;
    ren_d.fp                = dec_uop.fp;
    ren_d.lq_valid          = dec_uop.alloc_lq;
    ren_d.lq_tag            = '0;
    ren_d.sq_valid          = dec_uop.alloc_sq;
    ren_d.sq_tag            = '0;
    ren_d.serializing       = dec_uop.serializing;
    ren_d.requires_rob_head = dec_uop.requires_rob_head;
    ren_d.exception         = dec_uop.exception;

    // --- Dynamic FP Rounding Mode Resolution (§23.3) ---
    if (dec_uop.fp.valid) begin
      if (dec_uop.fp.rm == fp_rm_e'(3'b111)) begin
        ren_d.fp.rm = frm;
        if (frm == 3'b101 || frm == 3'b110 || frm == 3'b111) begin
          ren_d.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: dec_uop.insn};
        end
      end else if (dec_uop.fp.rm == 3'b101 || dec_uop.fp.rm == 3'b110) begin
        ren_d.exception = '{valid: 1'b1, cause: EXC_ILLEGAL_INSTRUCTION, tval: dec_uop.insn};
      end
    end

    // --- Source 0 Rename ---
    ren_d.src0.kind = dec_uop.src0.kind;
    if (dec_uop.src0.kind == SRC_INT_REG) begin
      if (dec_uop.src0.arch == 5'd0) begin
        ren_d.src0.phys  = 6'd0; // p0
        ren_d.src0.ready = 1'b1;
      end else begin
        s0_int_p         = int_rat[dec_uop.src0.arch];
        ren_d.src0.phys  = s0_int_p;
        ren_d.src0.ready = int_ready_table[s0_int_p];
      end
    end else if (dec_uop.src0.kind == SRC_FP_REG) begin
      s0_fp_p          = fp_rat[dec_uop.src0.arch];
      ren_d.src0.phys  = s0_fp_p;
      ren_d.src0.ready = fp_ready_table[s0_fp_p];
    end else begin
      ren_d.src0.phys  = 6'd0;
      ren_d.src0.ready = 1'b1;
    end

    // --- Source 1 Rename ---
    ren_d.src1.kind = dec_uop.src1.kind;
    if (dec_uop.src1.kind == SRC_INT_REG) begin
      if (dec_uop.src1.arch == 5'd0) begin
        ren_d.src1.phys  = 6'd0; // p0
        ren_d.src1.ready = 1'b1;
      end else begin
        s1_int_p         = int_rat[dec_uop.src1.arch];
        ren_d.src1.phys  = s1_int_p;
        ren_d.src1.ready = int_ready_table[s1_int_p];
      end
    end else if (dec_uop.src1.kind == SRC_FP_REG) begin
      s1_fp_p          = fp_rat[dec_uop.src1.arch];
      ren_d.src1.phys  = s1_fp_p;
      ren_d.src1.ready = fp_ready_table[s1_fp_p];
    end else begin
      ren_d.src1.phys  = 6'd0;
      ren_d.src1.ready = 1'b1;
    end

    // --- Source 2 Rename (FMA third source) ---
    ren_d.src2.kind = dec_uop.src2.kind;
    if (dec_uop.src2.kind == SRC_FP_REG) begin
      s2_fp_p          = fp_rat[dec_uop.src2.arch];
      ren_d.src2.phys  = s2_fp_p;
      ren_d.src2.ready = fp_ready_table[s2_fp_p];
    end else begin
      ren_d.src2.phys  = 6'd0;
      ren_d.src2.ready = 1'b1;
    end

    // --- Destination Rename ---
    ren_d.dst.valid  = dec_uop.dst.valid;
    ren_d.dst.domain = dec_uop.dst.domain;
    ren_d.dst.arch   = dec_uop.dst.arch;

    if (needs_int_phys) begin
      ren_d.dst.new_phys = allocated_int_phys;
      ren_d.dst.old_phys = int_rat[dec_uop.dst.arch];
    end else if (needs_fp_phys) begin
      ren_d.dst.new_phys = allocated_fp_phys;
      ren_d.dst.old_phys = fp_rat[dec_uop.dst.arch];
    end else if (dec_uop.dst.valid && (dec_uop.dst.domain == REG_INT) && (dec_uop.dst.arch == 5'd0)) begin
      ren_d.dst.new_phys = 6'd0;
      ren_d.dst.old_phys = 6'd0;
      ren_d.dst.valid    = 1'b0; // Suppress write for x0
    end else begin
      ren_d.dst.new_phys = 6'd0;
      ren_d.dst.old_phys = 6'd0;
    end
  end

  // Retirement flags
  wire retiring_int_dest = retire_valid && retire_entry.dst.valid &&
                           (retire_entry.dst.domain == REG_INT) &&
                           (retire_entry.dst.arch != 5'd0);

  wire retiring_fp_dest  = retire_valid && retire_entry.dst.valid &&
                           (retire_entry.dst.domain == REG_FP);

  wire allocating_int_dest = dec_valid && dec_ready && needs_int_phys;
  wire allocating_fp_dest  = dec_valid && dec_ready && needs_fp_phys;

  // Next RRAT masks for rollback recovery (discrete per-phys parallel checks)
  logic [INT_PRF_ENTRIES-1:0] next_int_rrat_mask;
  for (genvar p = 0; p < INT_PRF_ENTRIES; p++) begin : gen_next_int_rrat_mask
    logic [ARCH_REGS-1:0] int_rrat_has_p;
    for (genvar a = 0; a < ARCH_REGS; a++) begin : gen_check_a
      assign int_rrat_has_p[a] = (retiring_int_dest && (retire_entry.dst.arch == arch_reg_t'(a))) ?
                                   (retire_entry.dst.new_phys == phys_reg_t'(p)) :
                                   (int_rrat[a] == phys_reg_t'(p));
    end
    assign next_int_rrat_mask[p] = (p == 0) ? 1'b1 : (|int_rrat_has_p);
  end

  logic [FP_PRF_ENTRIES-1:0] next_fp_rrat_mask;
  for (genvar p = 0; p < FP_PRF_ENTRIES; p++) begin : gen_next_fp_rrat_mask
    logic [ARCH_REGS-1:0] fp_rrat_has_p;
    for (genvar a = 0; a < ARCH_REGS; a++) begin : gen_check_a
      assign fp_rrat_has_p[a] = (retiring_fp_dest && (retire_entry.dst.arch == arch_reg_t'(a))) ?
                                  (retire_entry.dst.new_phys == phys_reg_t'(p)) :
                                  (fp_rrat[a] == phys_reg_t'(p));
    end
    assign next_fp_rrat_mask[p] = |fp_rrat_has_p;
  end

  // =========================================================================
  // 4. State Updates (Discrete Per-Register Sequential Logic)
  // =========================================================================

  for (genvar a = 0; a < ARCH_REGS; a++) begin : gen_arch_rat
    always_ff @(posedge clk) begin
      if (rst) begin
        int_rat[a]  <= phys_reg_t'(a);
        int_rrat[a] <= phys_reg_t'(a);
        fp_rat[a]   <= phys_reg_t'(a);
        fp_rrat[a]  <= phys_reg_t'(a);
      end else if (rollback_valid || trap_recovery_valid || mret_recovery_valid) begin
        if (retiring_int_dest && (retire_entry.dst.arch == arch_reg_t'(a))) begin
          int_rat[a]  <= retire_entry.dst.new_phys;
          int_rrat[a] <= retire_entry.dst.new_phys;
        end else begin
          int_rat[a]  <= int_rrat[a];
        end

        if (retiring_fp_dest && (retire_entry.dst.arch == arch_reg_t'(a))) begin
          fp_rat[a]  <= retire_entry.dst.new_phys;
          fp_rrat[a] <= retire_entry.dst.new_phys;
        end else begin
          fp_rat[a]  <= fp_rrat[a];
        end
      end else begin
        // Normal Execution
        if (retiring_int_dest && (retire_entry.dst.arch == arch_reg_t'(a))) begin
          int_rrat[a] <= retire_entry.dst.new_phys;
        end
        if (allocating_int_dest && (dec_uop.dst.arch == arch_reg_t'(a))) begin
          int_rat[a] <= allocated_int_phys;
        end

        if (retiring_fp_dest && (retire_entry.dst.arch == arch_reg_t'(a))) begin
          fp_rrat[a] <= retire_entry.dst.new_phys;
        end
        if (allocating_fp_dest && (dec_uop.dst.arch == arch_reg_t'(a))) begin
          fp_rat[a] <= allocated_fp_phys;
        end
      end
    end
  end

  for (genvar p = 0; p < INT_PRF_ENTRIES; p++) begin : gen_int_phys_status
    always_ff @(posedge clk) begin
      if (rst) begin
        int_ready_table[p] <= 1'b1;
        int_free_mask[p]   <= (p >= ARCH_REGS);
      end else if (rollback_valid || trap_recovery_valid || mret_recovery_valid) begin
        int_ready_table[p] <= 1'b1;
        int_free_mask[p]   <= (p == 0) ? 1'b0 : ~next_int_rrat_mask[p];
      end else begin
        // Ready table updates
        if (int_cmp.valid && int_cmp.result_valid && (int_cmp.result_domain == REG_INT) && (int_cmp.result_phys == phys_reg_t'(p))) begin
          int_ready_table[p] <= 1'b1;
        end else if (ld_cmp.valid && ld_cmp.result_valid && (ld_cmp.result_domain == REG_INT) && (ld_cmp.result_phys == phys_reg_t'(p))) begin
          int_ready_table[p] <= 1'b1;
        end else if (fp_cmp.valid && fp_cmp.result_valid && (fp_cmp.result_domain == REG_INT) && (fp_cmp.result_phys == phys_reg_t'(p))) begin
          int_ready_table[p] <= 1'b1;
        end else if (allocating_int_dest && (allocated_int_phys == phys_reg_t'(p))) begin
          int_ready_table[p] <= 1'b0;
        end

        // Free mask updates
        if (allocating_int_dest && (allocated_int_phys == phys_reg_t'(p))) begin
          int_free_mask[p] <= 1'b0;
        end else if (retiring_int_dest && (retire_entry.dst.old_phys == phys_reg_t'(p))) begin
          int_free_mask[p] <= 1'b1;
        end
      end
    end
  end

  for (genvar p = 0; p < FP_PRF_ENTRIES; p++) begin : gen_fp_phys_status
    always_ff @(posedge clk) begin
      if (rst) begin
        fp_ready_table[p] <= 1'b1;
        fp_free_mask[p]   <= (p >= ARCH_REGS);
      end else if (rollback_valid || trap_recovery_valid || mret_recovery_valid) begin
        fp_ready_table[p] <= 1'b1;
        fp_free_mask[p]   <= ~next_fp_rrat_mask[p];
      end else begin
        // Ready table updates
        if (int_cmp.valid && int_cmp.result_valid && (int_cmp.result_domain == REG_FP) && (int_cmp.result_phys == phys_reg_t'(p))) begin
          fp_ready_table[p] <= 1'b1;
        end else if (ld_cmp.valid && ld_cmp.result_valid && (ld_cmp.result_domain == REG_FP) && (ld_cmp.result_phys == phys_reg_t'(p))) begin
          fp_ready_table[p] <= 1'b1;
        end else if (fp_cmp.valid && fp_cmp.result_valid && (fp_cmp.result_domain == REG_FP) && (fp_cmp.result_phys == phys_reg_t'(p))) begin
          fp_ready_table[p] <= 1'b1;
        end else if (allocating_fp_dest && (allocated_fp_phys == phys_reg_t'(p))) begin
          fp_ready_table[p] <= 1'b0;
        end

        // Free mask updates
        if (allocating_fp_dest && (allocated_fp_phys == phys_reg_t'(p))) begin
          fp_free_mask[p] <= 1'b0;
        end else if (retiring_fp_dest && (retire_entry.dst.old_phys == phys_reg_t'(p))) begin
          fp_free_mask[p] <= 1'b1;
        end
      end
    end
  end

  // Output to Dispatch / Queues
  assign ren_valid = dec_valid && free_dest_available && (core_state == CORE_RUN);
  assign ren_uop   = ren_d;

endmodule
