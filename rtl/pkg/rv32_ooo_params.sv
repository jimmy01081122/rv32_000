// rv32_ooo_params.sv
// Current constants; some legacy fields do not configure the instantiated RTL.
// See architecture_spec.md for the implementation inventory and PLAN.md for review.
// Section references below refer to the archived G0 contracts in docs/archive/g0/.
//
// Compatibility: Verilator 4.038, Yosys 0.9+
// * No $clog2 in package scope (Yosys 0.9 rejects it).
// * No 'int unsigned' localparam type (Yosys 0.9 rejects it); use plain integer.
// * Derived widths are pre-computed literal integers with a comment showing the math.

package rv32_ooo_params;

  // Data widths
  localparam integer XLEN         = 32;
  localparam integer FLEN         = 32;

  // Pipeline widths
  localparam integer FETCH_WIDTH    = 1;
  localparam integer DECODE_WIDTH   = 1;
  localparam integer RENAME_WIDTH   = 1;
  localparam integer DISPATCH_WIDTH = 1;
  localparam integer RETIRE_WIDTH   = 1;

  // Reset address (architecture_spec §9.2)
  localparam [31:0] RESET_PC = 32'h8000_0000;

  // ROB (architecture_spec §6)
  localparam integer ROB_ENTRIES   = 16;
  localparam integer ROB_SEQ_WIDTH = 12;
  localparam integer ROB_IDX_W     = 4;   // $clog2(16)

  // Architectural registers
  localparam integer ARCH_REGS  = 32;
  localparam integer ARCH_REG_W = 5;      // $clog2(32)

  // Physical register files (architecture_spec §6 / uop_spec §3)
  localparam integer INT_PRF_ENTRIES = 48;
  localparam integer FP_PRF_ENTRIES  = 48;
  localparam integer INT_PHYS_W      = 6; // $clog2(48) -> 6
  localparam integer FP_PHYS_W       = 6; // $clog2(48) -> 6
  // PHYS_W: max(INT_PHYS_W, FP_PHYS_W) = 6  (uop_spec §4.1)
  localparam integer PHYS_W          = 6;

  // Issue queues
  localparam integer INT_IQ_ENTRIES = 8;
  localparam integer FP_IQ_ENTRIES  = 4;

  // Store queue and reserved LQ schema (G0 architecture_spec §6 / uop_spec §4.3)
  // LQ_ENTRIES does not allocate a load queue in the current LSU.
  localparam integer LQ_ENTRIES = 16;
  localparam integer SQ_ENTRIES = 16;
  localparam integer LQ_IDX_W   = 4;  // $clog2(16)
  localparam integer SQ_IDX_W   = 4;  // $clog2(16)
  localparam integer LSQ_GEN_W  = 4;  // uop_spec §4.3

  // Instruction queue (frontend buffer)
  localparam integer INSTR_QUEUE_ENTRIES = 8;

  // Fetch epoch (uop_spec §4.4)
  localparam integer FETCH_EPOCH_W = 4;

  // Legacy PRF port constants (G0 architecture_spec §6, Appendix C items 4-5).
  // Actual module interfaces: INT 4R/3W, FP 4R/2W; these constants do not size them.
  localparam integer INT_PRF_READ_PORTS  = 3;
  localparam integer INT_PRF_WRITE_PORTS = 1;
  localparam integer FP_PRF_READ_PORTS   = 4;
  localparam integer FP_PRF_WRITE_PORTS  = 1;

  // Memory outstanding requests
  localparam integer MAX_DMEM_OUTSTANDING = 1;

  // Elaboration-time sanity checks live in rv32_ooo_param_check module
  // (initial blocks are illegal in SV packages; $clog2 checks belong in modules)

endpackage
