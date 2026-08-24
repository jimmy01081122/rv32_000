// All width constants are replicated here for Yosys 0.9 compatibility.
// Values MUST match rv32_ooo_params.sv — verified by G1.1 cross-check.
// Yosys 0.9 does not support 'import pkg::*' inside another package.

package rv32_ooo_types;
  import rv32_ooo_params::*;

  // =========================================================================
  // §4.1  Register identifiers
  // =========================================================================

  typedef logic [ARCH_REG_W-1:0] arch_reg_t;
  typedef logic [PHYS_W-1:0]     phys_reg_t;

  typedef enum logic [1:0] {
    REG_NONE = 2'b00,
    REG_INT  = 2'b01,
    REG_FP   = 2'b10
  } reg_domain_e;

  // =========================================================================
  // §4.2  ROB tag
  // =========================================================================

  typedef struct packed {
    logic [ROB_SEQ_WIDTH-1:0] seq;
    logic [ROB_IDX_W-1:0]     idx;
  } rob_tag_t;

  // =========================================================================
  // §4.3  LSQ tags  (generation-protected)
  // =========================================================================

  typedef struct packed {
    logic [LSQ_GEN_W-1:0] gen;
    logic [LQ_IDX_W-1:0]  idx;
  } lq_tag_t;

  typedef struct packed {
    logic [LSQ_GEN_W-1:0] gen;
    logic [SQ_IDX_W-1:0]  idx;
  } sq_tag_t;

  // =========================================================================
  // §4.4  Fetch metadata
  // =========================================================================

  typedef struct packed {
    logic [FETCH_EPOCH_W-1:0] epoch;
    logic                     predicted_taken;
    logic [31:0]              predicted_target;
  } fetch_meta_t;

  // =========================================================================
  // §5  Operation enumeration
  // =========================================================================

  typedef enum logic [7:0] {
    UOP_INVALID   = 8'h00,

    // RV32I upper immediate / control flow
    UOP_LUI,
    UOP_AUIPC,
    UOP_JAL,
    UOP_JALR,
    UOP_BEQ,
    UOP_BNE,
    UOP_BLT,
    UOP_BGE,
    UOP_BLTU,
    UOP_BGEU,

    // RV32I loads and stores
    UOP_LB,
    UOP_LH,
    UOP_LW,
    UOP_LBU,
    UOP_LHU,
    UOP_SB,
    UOP_SH,
    UOP_SW,

    // RV32I immediate ALU
    UOP_ADDI,
    UOP_SLTI,
    UOP_SLTIU,
    UOP_XORI,
    UOP_ORI,
    UOP_ANDI,
    UOP_SLLI,
    UOP_SRLI,
    UOP_SRAI,

    // RV32I register ALU
    UOP_ADD,
    UOP_SUB,
    UOP_SLL,
    UOP_SLT,
    UOP_SLTU,
    UOP_XOR,
    UOP_SRL,
    UOP_SRA,
    UOP_OR,
    UOP_AND,

    // Ordering / system
    UOP_FENCE,
    UOP_FENCE_I,
    UOP_ECALL,
    UOP_EBREAK,
    UOP_MRET,

    // Zicsr
    UOP_CSRRW,
    UOP_CSRRS,
    UOP_CSRRC,
    UOP_CSRRWI,
    UOP_CSRRSI,
    UOP_CSRRCI,

    // RV32M
    UOP_MUL,
    UOP_MULH,
    UOP_MULHSU,
    UOP_MULHU,
    UOP_DIV,
    UOP_DIVU,
    UOP_REM,
    UOP_REMU,

    // RV32F load/store
    UOP_FLW,
    UOP_FSW,

    // RV32F fused operations
    UOP_FMADD_S,
    UOP_FMSUB_S,
    UOP_FNMSUB_S,
    UOP_FNMADD_S,

    // RV32F arithmetic
    UOP_FADD_S,
    UOP_FSUB_S,
    UOP_FMUL_S,
    UOP_FDIV_S,
    UOP_FSQRT_S,

    // RV32F sign/min/max
    UOP_FSGNJ_S,
    UOP_FSGNJN_S,
    UOP_FSGNJX_S,
    UOP_FMIN_S,
    UOP_FMAX_S,

    // RV32F FP-to-integer / compare / classify
    UOP_FCVT_W_S,
    UOP_FCVT_WU_S,
    UOP_FMV_X_W,
    UOP_FEQ_S,
    UOP_FLT_S,
    UOP_FLE_S,
    UOP_FCLASS_S,

    // RV32F integer-to-FP / move
    UOP_FCVT_S_W,
    UOP_FCVT_S_WU,
    UOP_FMV_W_X,

    // Internal exception-only uop
    UOP_EXCEPTION
  } uop_op_e;

  // =========================================================================
  // §6  Functional-unit classification
  // =========================================================================

  typedef enum logic [3:0] {
    FU_NONE,
    FU_INT_ALU,
    FU_BRANCH,
    FU_INT_MUL,
    FU_INT_DIV,
    FU_LSU_AGU,
    FU_FP_ADD,
    FU_FP_MUL,
    FU_FP_FMA,
    FU_FP_DIVSQRT,
    FU_FP_MISC,
    FU_FP_CONV,
    FU_CSR_SERIAL,
    FU_EXCEPTION
  } fu_class_e;

  // =========================================================================
  // §7  Source representation
  // =========================================================================

  typedef enum logic [2:0] {
    SRC_NONE,
    SRC_INT_REG,
    SRC_FP_REG,
    SRC_PC,
    SRC_IMM,
    SRC_ZERO,
    SRC_CSR_ZIMM
  } src_kind_e;

  typedef struct packed {
    src_kind_e kind;
    arch_reg_t arch;
  } decoded_src_t;

  typedef struct packed {
    src_kind_e kind;
    phys_reg_t phys;
    logic      ready;
  } renamed_src_t;

  // =========================================================================
  // §8  Destination representation
  // =========================================================================

  typedef struct packed {
    logic        valid;
    reg_domain_e domain;
    arch_reg_t   arch;
  } decoded_dst_t;

  typedef struct packed {
    logic        valid;
    reg_domain_e domain;
    arch_reg_t   arch;
    phys_reg_t   new_phys;
    phys_reg_t   old_phys;
  } renamed_dst_t;

  // =========================================================================
  // §9  Immediate type
  // =========================================================================

  typedef enum logic [3:0] {
    IMM_NONE,
    IMM_I,
    IMM_S,
    IMM_B,
    IMM_U,
    IMM_J,
    IMM_SHAMT,
    IMM_CSR_ZIMM
  } imm_kind_e;

  // =========================================================================
  // §10  Memory control
  // =========================================================================

  typedef enum logic [1:0] {
    MEM_BYTE = 2'b00,
    MEM_HALF = 2'b01,
    MEM_WORD = 2'b10
  } mem_size_e;

  typedef enum logic {
    LOAD_SIGNED   = 1'b0,
    LOAD_UNSIGNED = 1'b1
  } load_ext_e;

  typedef struct packed {
    logic      is_load;
    logic      is_store;
    logic      is_fp;
    mem_size_e size;
    load_ext_e load_ext;
  } mem_ctrl_t;

  // =========================================================================
  // §11  Branch control
  // =========================================================================

  typedef enum logic [3:0] {
    BR_NONE,
    BR_JAL,
    BR_JALR,
    BR_EQ,
    BR_NE,
    BR_LT,
    BR_GE,
    BR_LTU,
    BR_GEU
  } branch_kind_e;

  typedef struct packed {
    branch_kind_e kind;
    logic         writes_link;
  } branch_ctrl_t;

  // =========================================================================
  // §12  CSR control
  // =========================================================================

  typedef enum logic [2:0] {
    CSR_NONE,
    CSR_WRITE,
    CSR_SET,
    CSR_CLEAR
  } csr_cmd_e;

  typedef struct packed {
    logic        valid;
    csr_cmd_e    cmd;
    logic [11:0] addr;
    logic        use_zimm;
    logic        read_enable;
    logic        write_enable;
  } csr_ctrl_t;

  // =========================================================================
  // §13  FP control
  // =========================================================================

  typedef enum logic [2:0] {
    RM_RNE = 3'b000,
    RM_RTZ = 3'b001,
    RM_RDN = 3'b010,
    RM_RUP = 3'b011,
    RM_RMM = 3'b100
  } fp_rm_e;

  typedef struct packed {
    logic   valid;
    logic   uses_rm;
    fp_rm_e rm;
    logic   may_set_flags;
  } fp_ctrl_t;

  typedef struct packed {
    logic nv;
    logic dz;
    logic of;
    logic uf;
    logic nx;
  } fp_flags_t;

  // =========================================================================
  // §14  Exception metadata
  // =========================================================================

  typedef enum logic [4:0] {
    EXC_INST_ADDR_MISALIGNED  = 5'd0,
    EXC_INST_ACCESS_FAULT     = 5'd1,
    EXC_ILLEGAL_INSTRUCTION   = 5'd2,
    EXC_BREAKPOINT            = 5'd3,
    EXC_LOAD_ADDR_MISALIGNED  = 5'd4,
    EXC_LOAD_ACCESS_FAULT     = 5'd5,
    EXC_STORE_ADDR_MISALIGNED = 5'd6,
    EXC_STORE_ACCESS_FAULT    = 5'd7,
    EXC_ECALL_M               = 5'd11
  } exception_cause_e;

  typedef struct packed {
    logic             valid;
    exception_cause_e cause;
    logic [31:0]      tval;
  } exception_t;

  // =========================================================================
  // §15  Decoded uop
  // =========================================================================

  typedef struct packed {
    // Identity
    logic [31:0] pc;
    logic [31:0] insn;
    fetch_meta_t fetch;

    // Operation
    uop_op_e   op;
    fu_class_e fu_class;

    // Sources and destination
    decoded_src_t src0;
    decoded_src_t src1;
    decoded_src_t src2;
    decoded_dst_t dst;

    // Immediate and specialized control
    imm_kind_e    imm_kind;
    logic [31:0]  imm;
    mem_ctrl_t    mem;
    branch_ctrl_t branch;
    csr_ctrl_t    csr;
    fp_ctrl_t     fp;

    // Scheduling and ordering
    logic serializing;
    logic requires_rob_head;
    logic alloc_lq;
    logic alloc_sq;

    // Pre-execution exception
    exception_t exception;
  } decoded_uop_t;

  // =========================================================================
  // §16  Renamed uop
  // =========================================================================

  typedef struct packed {
    // Identity
    logic [31:0] pc;
    logic [31:0] insn;
    fetch_meta_t fetch;
    rob_tag_t    rob_tag;

    // Operation
    uop_op_e   op;
    fu_class_e fu_class;

    // Renamed operands
    renamed_src_t src0;
    renamed_src_t src1;
    renamed_src_t src2;
    renamed_dst_t dst;

    // Immediate and specialized control
    logic [31:0]  imm;
    mem_ctrl_t    mem;
    branch_ctrl_t branch;
    csr_ctrl_t    csr;
    fp_ctrl_t     fp;

    // Allocated queue identities
    logic    lq_valid;
    lq_tag_t lq_tag;
    logic    sq_valid;
    sq_tag_t sq_tag;

    // Scheduling and ordering
    logic serializing;
    logic requires_rob_head;

    // Pre-execution exception
    exception_t exception;
  } renamed_uop_t;

  // =========================================================================
  // §17  Issue-queue entry
  // =========================================================================

  typedef struct packed {
    logic         valid;
    renamed_uop_t uop;
  } issue_entry_t;

  // =========================================================================
  // §17.1  Readiness helper  (explicit == only; no 'inside' operator)
  // =========================================================================

  function automatic logic src_is_ready(input renamed_src_t src);
    return (src.kind == SRC_NONE || src.kind == SRC_PC || src.kind == SRC_IMM || src.kind == SRC_ZERO || src.kind == SRC_CSR_ZIMM) ? 1'b1 : src.ready;
  endfunction

  // =========================================================================
  // §18  Operand read packet (execution request)
  // =========================================================================

  typedef struct packed {
    renamed_uop_t uop;
    logic [31:0]  operand0;
    logic [31:0]  operand1;
    logic [31:0]  operand2;
  } exec_req_t;

  // =========================================================================
  // §19  Completion packet
  // =========================================================================

  typedef struct packed {
    logic        valid;
    rob_tag_t    rob_tag;

    // Register writeback
    logic        result_valid;
    reg_domain_e result_domain;
    phys_reg_t   result_phys;
    logic [31:0] result_data;

    // Exception and FP state
    exception_t  exception;
    logic        fp_flags_valid;
    fp_flags_t   fp_flags;

    // Branch resolution
    logic        branch_valid;
    logic        branch_taken;
    logic [31:0] branch_target;
    logic        branch_mispredict;

    // Memory association
    logic    lq_valid;
    lq_tag_t lq_tag;
    logic    sq_valid;
    sq_tag_t sq_tag;
  } completion_t;

  // =========================================================================
  // §20  ROB entry
  // =========================================================================

  typedef struct packed {
    logic     valid;
    logic     completed;
    rob_tag_t tag;

    logic [31:0] pc;
    logic [31:0] insn;
    uop_op_e     op;

    // Destination ownership
    renamed_dst_t dst;
    logic [31:0]  result_data;

    // Classification
    logic is_branch;
    logic is_load;
    logic is_store;
    logic is_csr;
    logic serializing;

    // Exception state
    exception_t exception;

    // FP accrued flags
    logic      fp_flags_valid;
    fp_flags_t fp_flags;

    // Branch resolution
    logic        branch_resolved;
    logic        branch_mispredict;
    logic [31:0] branch_target;

    // Memory association
    logic    lq_valid;
    lq_tag_t lq_tag;
    logic    sq_valid;
    sq_tag_t sq_tag;

    // Store retirement state
    logic store_req_sent;
    logic store_rsp_done;
  } rob_entry_t;

  // =========================================================================
  // §21  Load Queue entry
  // =========================================================================

  typedef struct packed {
    logic     valid;
    lq_tag_t  tag;
    rob_tag_t rob_tag;

    logic        addr_valid;
    logic [31:0] addr;
    mem_size_e   size;
    load_ext_e   load_ext;
    logic        is_fp;

    reg_domain_e dst_domain;
    phys_reg_t   dst_phys;

    logic       request_sent;
    logic       response_done;
    exception_t exception;
  } lq_entry_t;

  // =========================================================================
  // §22  Store Queue entry
  //   data_valid == 1 iff store-data bits are physically captured in `data`
  //   (not merely src1.ready). Dedicated SQ PRF port; never contested
  //   because rename_width = 1.
  // =========================================================================

  typedef struct packed {
    logic     valid;
    sq_tag_t  tag;
    rob_tag_t rob_tag;

    logic        addr_valid;
    logic [31:0] addr;

    reg_domain_e data_domain;
    phys_reg_t   data_phys;
    logic        data_valid;
    logic [31:0] data;

    logic [3:0] byte_mask;
    mem_size_e  size;
    logic       is_fp;

    logic       request_sent;
    logic       response_done;
    exception_t exception;
  } sq_entry_t;

  // =========================================================================
  // architecture_spec §15.2  Pending memory transaction record
  //   Set on (dmem_req_valid && dmem_req_ready).
  //   Cleared on (dmem_rsp_valid && dmem_rsp_ready).
  //   Normative source for ROB sequence-alias guard and stale load validation.
  // =========================================================================

  typedef struct packed {
    logic     valid;
    rob_tag_t rob_tag;
    logic     lq_valid;
    lq_tag_t  lq_tag;
    logic     sq_valid;
    sq_tag_t  sq_tag;
  } dmem_pending_t;

  // =========================================================================
  // architecture_spec §29.2  Commit trace record
  //   Emitted for retire_valid OR trap_valid (never both in the same cycle).
  // =========================================================================

  typedef struct packed {
    logic        retire_valid;
    logic        trap_valid;
    logic [63:0] event_order;    // monotonically increasing counter
    logic [31:0] pc;
    logic [31:0] insn;
    // Integer destination
    logic        int_dst_valid;
    arch_reg_t   int_dst_arch;
    logic [31:0] int_dst_data;
    // FP destination
    logic        fp_dst_valid;
    arch_reg_t   fp_dst_arch;
    logic [31:0] fp_dst_data;
    // Memory access
    logic        mem_valid;
    logic [31:0] mem_addr;
    logic [3:0]  mem_byte_mask;
    logic [31:0] mem_wdata;
    // Trap
    logic [31:0] trap_cause;
    logic [31:0] trap_tval;
    // Architectural fflags after this instruction
    fp_flags_t   fflags;
  } commit_trace_t;

  // =========================================================================
  // architecture_spec §11 / PLAN §15.3  Core global state
  // =========================================================================

  typedef enum logic [2:0] {
    CORE_RUN         = 3'd0,
    BRANCH_ROLLBACK  = 3'd1,
    TRAP_RECOVERY    = 3'd2,
    MRET_RECOVERY    = 3'd3,
    RESET_INITIALIZE = 3'd4
  } core_state_e;

endpackage
