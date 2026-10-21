// rv32_ooo_csr.sv — Control and Status Register (CSR) Subsystem
// Machine-mode CSRs, precise trap entry, and performance counters
// Architecture Spec §18, §25 | Uop Spec §12

module rv32_ooo_csr
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input  logic        clk,
  input  logic        rst,          // synchronous active-high

  input  core_state_e core_state,

  // Serialised CSR access from int execute
  input  logic        csr_req_valid,
  input  csr_ctrl_t   csr_ctrl,
  input  logic [31:0] csr_wdata,
  output logic [31:0] csr_rdata,
  output logic        csr_rdata_valid,
  output exception_t  csr_exc,

  // Dynamic rounding mode read
  output fp_rm_e      frm,

  // Trap entry from ROB
  input  logic        trap_entry_valid,
  input  logic [31:0] trap_pc,
  input  logic [31:0] trap_cause,
  input  logic [31:0] trap_tval,
  output logic [31:0] mtvec_out,

  // MRET from ROB
  input  logic        mret_valid,
  output logic [31:0] mepc_out,

  // fflags accumulation at retirement
  input  logic        retire_fp_valid,
  input  fp_flags_t   retire_fflags_delta,

  // Performance counters increment
  input  logic        cycle_inc,
  input  logic        instret_inc
);

  localparam logic [31:0] MISA_VALUE = 32'h4000_1120; // RV32IMF

  // =========================================================================
  // 1. Architectural CSR State
  // =========================================================================

  logic [31:0] csr_mstatus;
  logic [31:0] csr_mtvec;
  logic [31:0] csr_mepc;
  logic [31:0] csr_mcause;
  logic [31:0] csr_mtval;
  logic [31:0] csr_mscratch;

  // 64-bit Performance Counters
  logic [63:0] mcycle_cnt;
  logic [63:0] minstret_cnt;

  // Floating-Point CSRs
  logic [2:0] csr_frm;
  logic [4:0] csr_fflags;

  assign frm       = fp_rm_e'(csr_frm);
  assign mtvec_out = csr_mtvec;
  assign mepc_out  = csr_mepc;

  // =========================================================================
  // 2. CSR Read Multiplexer
  // =========================================================================

  logic [31:0] rdata;
  logic        illegal_csr;

  always_comb begin
    rdata       = 32'd0;
    illegal_csr = 1'b0;

    if (csr_req_valid && csr_ctrl.valid) begin
      case (csr_ctrl.addr)
        12'h300: rdata = csr_mstatus;
        12'h301: rdata = MISA_VALUE;
        12'h305: rdata = csr_mtvec;
        12'h340: rdata = csr_mscratch;
        12'h341: rdata = csr_mepc;
        12'h342: rdata = csr_mcause;
        12'h343: rdata = csr_mtval;

        // FP CSRs
        12'h001: rdata = {27'd0, csr_fflags};
        12'h002: rdata = {29'd0, csr_frm};
        12'h003: rdata = {24'd0, csr_frm, csr_fflags};

        // Counters
        12'hC00, 12'hB00: rdata = mcycle_cnt[31:0];
        12'hC80, 12'hB80: rdata = mcycle_cnt[63:32];
        12'hC02, 12'hB02: rdata = minstret_cnt[31:0];
        12'hC82, 12'hB82: rdata = minstret_cnt[63:32];

        default: begin
          rdata       = 32'd0;
          illegal_csr = 1'b1;
        end
      endcase
    end
  end

  assign csr_rdata       = rdata;
  assign csr_rdata_valid = csr_req_valid && !illegal_csr;
  assign csr_exc.valid   = csr_req_valid && illegal_csr;
  assign csr_exc.cause   = EXC_ILLEGAL_INSTRUCTION;
  assign csr_exc.tval    = {20'd0, csr_ctrl.addr};

  // =========================================================================
  // 3. CSR Write Calculation
  // =========================================================================

  logic [31:0] wdata_calc;
  always_comb begin
    case (csr_ctrl.cmd)
      CSR_WRITE: wdata_calc = csr_wdata;
      CSR_SET:   wdata_calc = rdata | csr_wdata;
      CSR_CLEAR: wdata_calc = rdata & ~csr_wdata;
      default:   wdata_calc = csr_wdata;
    endcase
  end

  // =========================================================================
  // 4. Sequential Updates
  // =========================================================================

  always_ff @(posedge clk) begin
    if (rst) begin
      csr_mstatus   <= 32'h0000_1800; // MPP = 2'b11 (M-mode)
      csr_mtvec     <= 32'h8000_0000;
      csr_mepc      <= 32'd0;
      csr_mcause    <= 32'd0;
      csr_mtval     <= 32'd0;
      csr_mscratch  <= 32'd0;
      mcycle_cnt    <= 64'd0;
      minstret_cnt  <= 64'd0;
      csr_frm       <= 3'd0; // RM_RNE
      csr_fflags    <= 5'd0;
    end else begin
      // --- Performance Counters ---
      if (cycle_inc)   mcycle_cnt   <= mcycle_cnt + 64'd1;
      if (instret_inc) minstret_cnt <= minstret_cnt + 64'd1;

      // --- FP Accrued Flags accumulation ---
      if (retire_fp_valid) begin
        csr_fflags[0] <= csr_fflags[0] | retire_fflags_delta.nx;
        csr_fflags[1] <= csr_fflags[1] | retire_fflags_delta.uf;
        csr_fflags[2] <= csr_fflags[2] | retire_fflags_delta.of;
        csr_fflags[3] <= csr_fflags[3] | retire_fflags_delta.dz;
        csr_fflags[4] <= csr_fflags[4] | retire_fflags_delta.nv;
      end

      // --- Trap Entry ---
      if (trap_entry_valid) begin
        csr_mepc              <= trap_pc;
        csr_mcause            <= trap_cause;
        csr_mtval             <= trap_tval;
        csr_mstatus[7]        <= csr_mstatus[3]; // MPIE <= MIE
        csr_mstatus[3]        <= 1'b0;           // MIE <= 0
        csr_mstatus[12:11]    <= 2'b11;          // MPP <= M-mode
      end
      // --- MRET Execution ---
      else if (mret_valid) begin
        csr_mstatus[3]        <= csr_mstatus[7]; // MIE <= MPIE
        csr_mstatus[7]        <= 1'b1;           // MPIE <= 1
      end
      // --- Explicit CSR Instruction Write ---
      else if (csr_req_valid && csr_ctrl.write_enable && !illegal_csr) begin
        case (csr_ctrl.addr)
          12'h300: csr_mstatus  <= (wdata_calc & 32'h0000_1888) | (csr_mstatus & ~32'h0000_1888);
          12'h305: csr_mtvec    <= {wdata_calc[31:2], 2'b00}; // Direct mode
          12'h340: csr_mscratch <= wdata_calc;
          12'h341: csr_mepc     <= {wdata_calc[31:2], 2'b00};
          12'h342: csr_mcause   <= wdata_calc;
          12'h343: csr_mtval    <= wdata_calc;

          // FP CSRs
          12'h001: csr_fflags   <= wdata_calc[4:0];
          12'h002: csr_frm      <= wdata_calc[2:0];
          12'h003: begin
            csr_frm    <= wdata_calc[7:5];
            csr_fflags <= wdata_calc[4:0];
          end

          // Counter writes
          12'hB00: mcycle_cnt[31:0]    <= wdata_calc;
          12'hB80: mcycle_cnt[63:32]   <= wdata_calc;
          12'hB02: minstret_cnt[31:0]  <= wdata_calc;
          12'hB82: minstret_cnt[63:32] <= wdata_calc;

          default: ;
        endcase
      end
    end
  end

endmodule
