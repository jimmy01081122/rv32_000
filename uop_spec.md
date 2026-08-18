# RV32 OoO Core Micro-Operation Specification

| Item | Value |
|---|---|
| Document | `uop_spec.md` |
| Version | 0.2.2 |
| Status | G0 Frozen — 2026-08-08 |
| Parent specification | [`architecture_spec.md`](./architecture_spec.md) |
| ISA target | RV32IMF + Zicsr |
| Decode policy | One architectural instruction maps to one ROB uop |

## 1. Purpose

This document defines the normative micro-operation representation used between decode, rename, dispatch, issue, execution, writeback, and retirement.

The main objectives are:

- one unambiguous decode representation for every supported instruction;
- explicit integer and floating-point register domains;
- no implicit source or destination inference after decode;
- stable physical tags after rename;
- complete exception, rounding, memory, branch, and CSR metadata;
- sufficient identity information to reject stale completions;
- synthesizable, parameterized SystemVerilog types.

The uop specification is a hardware interface contract. A field may not be repurposed without updating this document and every producer/consumer assertion.

## 2. Design Principles

### 2.1 One Instruction, One ROB Entry

Every baseline architectural instruction creates exactly one ROB entry and one renamed uop.

Long-latency operations such as divide, square root, and FMA remain one uop. They are not split into independently retiring internal uops.

### 2.2 Decode and Rename Types Are Separate

The design shall use distinct types for:

1. decoded uop — architectural register identifiers;
2. renamed uop — physical tags and source readiness;
3. execution request — resolved operands and operation metadata;
4. completion packet — result and side effects returned to writeback/ROB.

This prevents accidental mixing of architectural and physical register namespaces.

### 2.3 Domains Are Explicit

Every register source and destination explicitly identifies one of:

- integer register domain;
- floating-point register domain;
- no register domain.

A single `is_fp` bit is insufficient because conversion, move, load, and store instructions cross domains.

### 2.4 Control Is Decoded Once

Execution units shall not re-decode the original 32-bit instruction except for assertions or debug checks. Operation, source selection, immediate, memory size, branch type, CSR command, and rounding mode are explicit uop fields.

### 2.5 No Undefined Payload Use

Consumers shall use payload fields only when their associated valid/control field is asserted. Producers shall assign deterministic values to unused fields to avoid X-dependent simulation behavior.

## 3. Package and Parameter Conventions

Recommended package:

```systemverilog
package rv32_uop_pkg;
```

Normative baseline parameters:

```systemverilog
parameter int XLEN            = 32;
parameter int FLEN            = 32;
parameter int ARCH_REGS       = 32;
parameter int INT_PRF_ENTRIES = 48;
parameter int FP_PRF_ENTRIES  = 48;
parameter int ROB_ENTRIES     = 16;
parameter int ROB_SEQ_WIDTH   = 12;
parameter int LQ_ENTRIES      = 4;
parameter int SQ_ENTRIES      = 4;

localparam int ARCH_REG_W = 5;
localparam int INT_PHYS_W = $clog2(INT_PRF_ENTRIES);
localparam int FP_PHYS_W  = $clog2(FP_PRF_ENTRIES);
localparam int PHYS_W     = (INT_PHYS_W > FP_PHYS_W) ? INT_PHYS_W : FP_PHYS_W;
localparam int ROB_IDX_W  = $clog2(ROB_ENTRIES);
localparam int LQ_IDX_W   = $clog2(LQ_ENTRIES);
localparam int SQ_IDX_W   = $clog2(SQ_ENTRIES);
```

Configuration elaboration shall fail when:

- PRF entries are fewer than architectural registers;
- ROB, LQ, or SQ depth is less than two;
- a field width cannot encode the configured entries;
- ROB sequence space is too small for the defined age comparison and maximum-live bound.

## 4. Basic Types

### 4.1 Architectural and Physical Register Identifiers

```systemverilog
typedef logic [ARCH_REG_W-1:0] arch_reg_t;
typedef logic [PHYS_W-1:0]     phys_reg_t;

typedef enum logic [1:0] {
    REG_NONE = 2'b00,
    REG_INT  = 2'b01,
    REG_FP   = 2'b10
} reg_domain_e;
```

Rules:

- `REG_NONE` means the source/destination has no physical-register ownership.
- Integer and FP physical indexes share a packed field width but belong to separate namespaces.
- A domain-tag pair is required to identify a physical register.
- Integer physical register 0 is reserved for architectural `x0`.

### 4.2 ROB Tag

```systemverilog
typedef struct packed {
    logic [ROB_SEQ_WIDTH-1:0] seq;
    logic [ROB_IDX_W-1:0]     idx;
} rob_tag_t;
```

Equality requires all bits to match.

Age comparison shall use sequence arithmetic, not raw index comparison.

### 4.3 LSQ Tags

```systemverilog
parameter int LSQ_GEN_W = 4;

typedef struct packed {
    logic [LSQ_GEN_W-1:0] gen;
    logic [LQ_IDX_W-1:0]  idx;
} lq_tag_t;

typedef struct packed {
    logic [LSQ_GEN_W-1:0] gen;
    logic [SQ_IDX_W-1:0]  idx;
} sq_tag_t;
```

LQ/SQ tag generation increments when a physical slot is reused. A stale memory response must match both the ROB tag and the LQ tag.

### 4.4 Fetch Metadata

```systemverilog
parameter int FETCH_EPOCH_W = 4;

typedef struct packed {
    logic [FETCH_EPOCH_W-1:0] epoch;
    logic                     predicted_taken;
    logic [31:0]              predicted_target;
} fetch_meta_t;
```

The baseline static predictor normally produces `predicted_taken=0` for conditional branches. JAL decode redirect may set the prediction metadata after fetch.

## 5. Operation Enumeration

`uop_op_e` shall have a fixed width large enough for all baseline operations and reserved expansion.

```systemverilog
typedef enum logic [7:0] {
    UOP_INVALID = 8'h00,

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

    // Internal exception-only representation
    UOP_EXCEPTION
} uop_op_e;
```

Rules:

- Enum numeric values shall be generated from one package and must not be duplicated in multiple RTL files.
- `UOP_INVALID` may never enter rename.
- `UOP_EXCEPTION` represents a fetch/decode exception and carries no execution side effect.
- Reserved enum values shall decode as invalid in assertions.

## 6. Functional-Unit Classification

```systemverilog
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
```

`fu_class` is a dispatch and scheduling hint. `op` remains the authoritative semantic operation.

Mapping requirements:

| FU class | Operations |
|---|---|
| `FU_INT_ALU` | integer ALU, LUI, AUIPC |
| `FU_BRANCH` | JAL, JALR, conditional branches |
| `FU_INT_MUL` | MUL family |
| `FU_INT_DIV` | DIV/REM family |
| `FU_LSU_AGU` | integer/FP loads and stores |
| `FU_FP_ADD` | FADD.S, FSUB.S |
| `FU_FP_MUL` | FMUL.S |
| `FU_FP_FMA` | fused multiply-add family |
| `FU_FP_DIVSQRT` | FDIV.S, FSQRT.S |
| `FU_FP_MISC` | sign injection, min/max, compare, classify, moves where implemented in misc datapath |
| `FU_FP_CONV` | integer/FP conversions |
| `FU_CSR_SERIAL` | CSR, FENCE, ECALL, EBREAK, MRET |
| `FU_EXCEPTION` | fetch/decode exception-only uop |

## 7. Source Representation

### 7.1 Source Kind

```systemverilog
typedef enum logic [2:0] {
    SRC_NONE,
    SRC_INT_REG,
    SRC_FP_REG,
    SRC_PC,
    SRC_IMM,
    SRC_ZERO,
    SRC_CSR_ZIMM
} src_kind_e;
```

Semantics:

- register source kinds require rename;
- `SRC_PC` returns the uop PC;
- `SRC_IMM` returns the decoded 32-bit immediate;
- `SRC_ZERO` returns 32'b0;
- `SRC_CSR_ZIMM` returns zero-extended instruction bits `[19:15]`;
- non-register sources are always ready.

### 7.2 Decoded Source

```systemverilog
typedef struct packed {
    src_kind_e kind;
    arch_reg_t arch;
} decoded_src_t;
```

`arch` is meaningful only for integer or FP register source kinds.

### 7.3 Renamed Source

```systemverilog
typedef struct packed {
    src_kind_e  kind;
    phys_reg_t  phys;
    logic       ready;
} renamed_src_t;
```

Rules:

- integer and FP kind determines the physical namespace;
- `ready` for non-register sources shall be 1;
- issue-queue wakeup may only modify sources with register kinds;
- physical tag is immutable after rename.

### 7.4 Source Slot Convention

The three source slots have semantic conventions:

| Slot | General use |
|---|---|
| `src0` | primary operand or address base |
| `src1` | secondary operand or store data |
| `src2` | third FMA operand |

The execution unit shall still use `kind`; slot convention does not override explicit control.

## 8. Destination Representation

### 8.1 Decoded Destination

```systemverilog
typedef struct packed {
    logic        valid;
    reg_domain_e domain;
    arch_reg_t   arch;
} decoded_dst_t;
```

### 8.2 Renamed Destination

```systemverilog
typedef struct packed {
    logic        valid;
    reg_domain_e domain;
    arch_reg_t   arch;
    phys_reg_t   new_phys;
    phys_reg_t   old_phys;
} renamed_dst_t;
```

Rules:

- integer `rd=x0` is converted to `valid=0` before free-list allocation;
- FP `f0` remains valid;
- `old_phys` is returned to the free list only at successful retirement;
- `new_phys` ready bit is cleared atomically with allocation;
- destination fields are immutable after allocation.

## 9. Immediate Types

```systemverilog
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
```

Immediate generation:

```text
I: sign_extend(insn[31:20])
S: sign_extend({insn[31:25], insn[11:7]})
B: sign_extend({insn[31], insn[7], insn[30:25], insn[11:8], 1'b0})
U: {insn[31:12], 12'b0}
J: sign_extend({insn[31], insn[19:12], insn[20], insn[30:21], 1'b0})
SHAMT: zero_extend(insn[24:20])
CSR_ZIMM: zero_extend(insn[19:15])
```

RV32 shift immediate legality shall validate the high encoding bits rather than treating all I-immediate encodings as legal shifts.

## 10. Memory Control

### 10.1 Memory Size and Extension

```systemverilog
typedef enum logic [1:0] {
    MEM_BYTE = 2'b00,
    MEM_HALF = 2'b01,
    MEM_WORD = 2'b10
} mem_size_e;

typedef enum logic {
    LOAD_SIGNED,
    LOAD_UNSIGNED
} load_ext_e;
```

### 10.2 Memory Control Structure

```systemverilog
typedef struct packed {
    logic       is_load;
    logic       is_store;
    logic       is_fp;
    mem_size_e  size;
    load_ext_e  load_ext;
} mem_ctrl_t;
```

Requirements:

- exactly one of `is_load` and `is_store` may be set;
- `is_fp` identifies FLW/FSW data domain, not address domain;
- all addresses use integer source `src0` plus `imm`;
- store data is `src1`;
- no memory control field is active for a non-memory operation.

### 10.3 Byte Strobes

For an aligned effective address:

| Operation | `wstrb` before lane shift |
|---|---|
| SB | `0001` |
| SH | `0011` |
| SW/FSW | `1111` |

The LSU shifts byte strobes and write data according to address bits `[1:0]`. Misaligned accesses raise an exception before request issue.

## 11. Branch Control

```systemverilog
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
```

Branch target rules:

- JAL: `pc + imm`;
- JALR: `(src0 + imm) & 32'hffff_fffe`, followed by IALIGN validation;
- conditional: `pc + imm` when condition true;
- fall-through: `pc + 4`.

Link value is `pc + 4`.

Branch completion returns actual taken and target. Misprediction comparison uses explicit prediction metadata.

## 12. CSR Control

```systemverilog
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
```

Decode-time semantic requirements:

- CSRRW/CSRRWI always attempt a write; read may be suppressed when `rd=x0` as defined by Zicsr;
- CSRRS/CSRRC with `rs1=x0` do not write the CSR;
- CSRRSI/CSRRCI with `zimm=0` do not write the CSR;
- access privilege and read-only checks occur even when normal datapath write data is zero, according to the pinned specification;
- illegal CSR access produces a precise illegal-instruction exception;
- all CSR uops are serializing and require ROB-head execution.

## 13. Floating-Point Control

### 13.1 Rounding Mode

```systemverilog
typedef enum logic [2:0] {
    RM_RNE = 3'b000,
    RM_RTZ = 3'b001,
    RM_RDN = 3'b010,
    RM_RUP = 3'b011,
    RM_RMM = 3'b100
} fp_rm_e;
```

Instruction `rm` encodings `101` and `110` are illegal. Encoding `111` requests dynamic rounding and must be resolved from architectural `frm` before dispatch.

The renamed uop always carries a resolved `fp_rm_e`; it never carries dynamic `111` into an arithmetic FU.

### 13.2 FP Control Structure

```systemverilog
typedef struct packed {
    logic   valid;
    logic   uses_rm;
    fp_rm_e rm;
    logic   may_set_flags;
} fp_ctrl_t;
```

`may_set_flags` shall be set for any operation that can architecturally update accrued FP flags, including relevant compare and min/max cases.

### 13.3 FP Flags

```systemverilog
typedef struct packed {
    logic nv;
    logic dz;
    logic of;
    logic uf;
    logic nx;
} fp_flags_t;
```

Bit packing for CSR interaction shall follow `fflags[4:0] = {NV,DZ,OF,UF,NX}`.

## 14. Exception Metadata

```systemverilog
typedef enum logic [4:0] {
    EXC_INST_ADDR_MISALIGNED = 5'd0,
    EXC_INST_ACCESS_FAULT    = 5'd1,
    EXC_ILLEGAL_INSTRUCTION  = 5'd2,
    EXC_BREAKPOINT           = 5'd3,
    EXC_LOAD_ADDR_MISALIGNED = 5'd4,
    EXC_LOAD_ACCESS_FAULT    = 5'd5,
    EXC_STORE_ADDR_MISALIGNED= 5'd6,
    EXC_STORE_ACCESS_FAULT   = 5'd7,
    EXC_ECALL_M              = 5'd11
} exception_cause_e;

typedef struct packed {
    logic             valid;
    exception_cause_e cause;
    logic [31:0]      tval;
} exception_t;
```

Exception payload is valid only when `valid=1`.

Typical `tval` values:

- illegal instruction: instruction bits where required by implementation policy;
- instruction address fault/misalignment: target or fetch address;
- load/store address fault/misalignment: effective address;
- ECALL/EBREAK: zero unless the pinned privileged specification requires otherwise.

## 15. Decoded Uop Structure

```systemverilog
typedef struct packed {
    // Identity
    logic [31:0] pc;
    logic [31:0] insn;
    fetch_meta_t fetch;

    // Operation
    uop_op_e     op;
    fu_class_e   fu_class;

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
```

### 15.1 Decoded Uop Invariants

For every valid decoded uop:

- `op != UOP_INVALID`;
- `fu_class` matches `op`;
- source kinds match the instruction semantic table;
- destination validity and domain match the table;
- memory controls are active only for memory operations;
- exactly one of `alloc_lq`, `alloc_sq`, or neither is set;
- all CSR/system operations are serializing;
- exception-only uops use `FU_EXCEPTION`, have no destination, and require no IQ/LSQ allocation;
- unused fields have deterministic zero/default values.

## 16. Renamed Uop Structure

```systemverilog
typedef struct packed {
    // Identity
    logic [31:0] pc;
    logic [31:0] insn;
    fetch_meta_t fetch;
    rob_tag_t    rob_tag;

    // Operation
    uop_op_e     op;
    fu_class_e   fu_class;

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
    logic         lq_valid;
    lq_tag_t      lq_tag;
    logic         sq_valid;
    sq_tag_t      sq_tag;

    // Scheduling and ordering
    logic serializing;
    logic requires_rob_head;

    // Pre-execution exception
    exception_t exception;
} renamed_uop_t;
```

### 16.1 Rename Transform

The rename stage shall:

1. copy identity and semantic control fields unchanged;
2. replace register source architectural IDs with RAT physical tags;
3. capture ready bits, including same-cycle accepted writeback bypass;
4. allocate and record destination `new_phys` and `old_phys`;
5. allocate ROB tag;
6. allocate LQ/SQ tag when required;
7. suppress integer x0 destination allocation;
8. resolve dynamic FP rounding mode;
9. perform allocation atomically.

### 16.2 Immutability

After rename, the following may not change:

- ROB tag;
- operation;
- source physical tags;
- destination new/old physical tags;
- register domains;
- immediate;
- CSR address and command;
- resolved rounding mode;
- LQ/SQ tag.

Only source `ready` state may change while resident in an issue queue.

## 17. Issue-Queue Entry

```systemverilog
typedef struct packed {
    logic         valid;
    renamed_uop_t uop;
} issue_entry_t;
```

An implementation may physically remove fields not required after dispatch, but the logical content shall remain equivalent.

### 17.1 Readiness

```systemverilog
function automatic logic src_is_ready(renamed_src_t src);
    return (src.kind == SRC_NONE)
        || (src.kind == SRC_PC)
        || (src.kind == SRC_IMM)
        || (src.kind == SRC_ZERO)
        || (src.kind == SRC_CSR_ZIMM)
        || src.ready;
endfunction
```

A uop is operand-ready when all required sources are ready.

### 17.2 Wakeup Match

A writeback matches a source when:

- writeback is valid and accepted;
- domains match;
- physical tags match;
- source kind is a matching register kind;
- writeback ROB tag itself passed stale-completion validation.

Wakeup shall not use an unvalidated producer packet. Issue queues must monitor both Integer and FP writeback broadcast buses to match physical tags for all register source operands according to `src.kind` (e.g., FP IQ snoops the Integer writeback bus for `SRC_INT_REG` sources).

## 18. Operand Read Packet

At issue, the PRF/operand-read stage forms:

```systemverilog
typedef struct packed {
    renamed_uop_t uop;
    logic [31:0]  operand0;
    logic [31:0]  operand1;
    logic [31:0]  operand2;
} exec_req_t;
```

Operand selection:

| Source kind | Value |
|---|---|
| `SRC_INT_REG` | integer PRF data |
| `SRC_FP_REG` | FP PRF bit pattern |
| `SRC_PC` | uop PC |
| `SRC_IMM` | uop immediate |
| `SRC_ZERO` | zero |
| `SRC_CSR_ZIMM` | zero-extended zimm |
| `SRC_NONE` | zero; consumer must ignore |

PRF data may be bypassed from an accepted same-cycle writeback if the implementation requires it to avoid a read-after-write timing hole.

## 19. Completion Packet

```systemverilog
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
    logic        lq_valid;
    lq_tag_t     lq_tag;
    logic        sq_valid;
    sq_tag_t     sq_tag;
} completion_t;
```

### 19.1 Completion Acceptance

A completion is accepted only when:

- producer `valid` and arbiter grant are asserted;
- ROB entry full tag matches;
- operation is not killed;
- destination fields match the ROB entry when `result_valid`;
- queue tag matches when memory-associated;
- entry has not already accepted completion.

On failed validation, the packet is discarded without side effects.

### 19.2 Atomic Actions

For a valid register result, the following occur atomically on acceptance:

- PRF write;
- ready-table update;
- wakeup broadcast;
- ROB completion update;
- exception/FP flag/branch metadata update.

For result-less operations, completion updates only the relevant ROB metadata.

## 20. ROB Entry Format

```systemverilog
typedef struct packed {
    logic        valid;
    logic        completed;
    rob_tag_t    tag;

    logic [31:0] pc;
    logic [31:0] insn;
    uop_op_e     op;

    // Destination ownership
    renamed_dst_t dst;

    // Classification
    logic is_branch;
    logic is_load;
    logic is_store;
    logic is_csr;
    logic serializing;

    // Exception state
    exception_t exception;

    // FP accrued flags from this instruction
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
```

### 20.1 ROB Completion by Operation Class

| Operation type | `completed` condition |
|---|---|
| integer/FP register result | accepted writeback |
| conditional branch | accepted branch resolution |
| JAL/JALR with link | accepted link writeback and branch resolution |
| load | accepted load writeback |
| store | address and data ready, no pre-request exception |
| CSR | accepted CSR result/write at ROB head |
| FENCE | memory drained at ROB head |
| ECALL/EBREAK | exception metadata installed |
| MRET | eligible at ROB head; redirect handled by retirement controller |
| exception-only uop | exception metadata installed at allocation or dispatch |

A store being `completed` does not mean it may retire; successful store response is additionally required.

## 21. Load Queue Entry

```systemverilog
typedef struct packed {
    logic        valid;
    lq_tag_t     tag;
    rob_tag_t    rob_tag;

    logic        addr_valid;
    logic [31:0] addr;
    mem_size_e   size;
    load_ext_e   load_ext;
    logic        is_fp;

    reg_domain_e dst_domain;
    phys_reg_t   dst_phys;

    logic request_sent;
    logic response_done;
    exception_t exception;
} lq_entry_t;
```

The LQ entry does not own the destination physical register; ownership remains represented by RAT/ROB. It records the destination for validated response routing.

## 22. Store Queue Entry

```systemverilog
typedef struct packed {
    logic        valid;
    sq_tag_t     tag;
    rob_tag_t    rob_tag;

    logic        addr_valid;
    logic [31:0] addr;

    reg_domain_e data_domain;
    phys_reg_t   data_phys;
    logic        data_valid;
    logic [31:0] data;

    logic [3:0]  byte_mask;
    mem_size_e   size;
    logic        is_fp;

    logic request_sent;
    logic response_done;
    exception_t exception;
} sq_entry_t;
```

Store address and data may become ready independently.

Normative SQ store-data capture rules:

- SQ allocation always captures renamed `src1` domain (`data_domain`) and physical tag (`data_phys`). `data_valid` is set to `1` only when the SQ has physically captured the store-data bits — not merely when `src1.ready` is asserted.
- On allocation, if `src1.ready == 1`, the SQ reads store data immediately via the dedicated SQ PRF read port. Because rename width is 1 (at most one store allocated per cycle), the dedicated port is never contested; the read is always granted and `data_valid` is set in the allocation cycle.
- If `src1.ready == 0` at allocation, `data_valid` remains `0`. The SQ snoops both Integer and FP accepted writeback buses each cycle for a tag/domain match on `data_phys`/`data_domain`, captures `data`, and sets `data_valid` on the matching accepted writeback.
- Store address generation issues out of Int IQ on `src0`-only readiness. At rename, the IQ entry for a store marks `src1` as `SRC_NONE` in the IQ copy; the AGU does not read `src1`.
- The SQ entry remains allocated until successful store retirement or recovery flush.

## 23. Instruction Semantic Tables

Legend:

- `I` = integer register source/destination;
- `F` = FP register source/destination;
- `PC` = PC source;
- `IMM` = decoded immediate;
- `Z` = CSR zimm;
- `—` = no source/destination;
- `S` = serializing;
- `H` = requires ROB head.

### 23.1 RV32I Upper Immediate and Control Flow

| Operation | FU | src0 | src1 | src2 | dst | Immediate | Special |
|---|---|---|---|---|---|---|---|
| LUI | INT_ALU | IMM | — | — | I | U | result=`imm` |
| AUIPC | INT_ALU | PC | IMM | — | I | U | result=`pc+imm` |
| JAL | BRANCH | PC | IMM | — | I | J | link=`pc+4`; target=`pc+imm` |
| JALR | BRANCH | I | IMM | — | I | I | link=`pc+4`; indirect target |
| BEQ | BRANCH | I | I | — | — | B | signedness not applicable |
| BNE | BRANCH | I | I | — | — | B | signedness not applicable |
| BLT | BRANCH | I | I | — | — | B | signed compare |
| BGE | BRANCH | I | I | — | — | B | signed compare |
| BLTU | BRANCH | I | I | — | — | B | unsigned compare |
| BGEU | BRANCH | I | I | — | — | B | unsigned compare |

Normative packed-source mapping:

- JAL: `src0=SRC_PC`, `src1=SRC_IMM`, `src2=SRC_NONE`;
- JALR: `src0=SRC_INT_REG`, `src1=SRC_IMM`, `src2=SRC_NONE`;
- conditional branch: `src0=SRC_INT_REG`, `src1=SRC_INT_REG`, `src2=SRC_NONE`, target immediate in `imm`.

### 23.2 RV32I Loads and Stores

| Operation | FU | src0 | src1 | dst | Size | Extension | LQ/SQ |
|---|---|---|---|---|---|---|---|
| LB | LSU_AGU | I base | — | I | byte | signed | LQ |
| LH | LSU_AGU | I base | — | I | half | signed | LQ |
| LW | LSU_AGU | I base | — | I | word | signed | LQ |
| LBU | LSU_AGU | I base | — | I | byte | unsigned | LQ |
| LHU | LSU_AGU | I base | — | I | half | unsigned | LQ |
| SB | LSU_AGU | I base | I data | — | byte | — | SQ |
| SH | LSU_AGU | I base | I data | — | half | — | SQ |
| SW | LSU_AGU | I base | I data | — | word | — | SQ |

All use I- or S-type signed immediate in `imm`.

### 23.3 RV32I Immediate ALU

| Operation | FU | src0 | src1 | dst | Immediate |
|---|---|---|---|---|---|
| ADDI | INT_ALU | I | IMM | I | I |
| SLTI | INT_ALU | I | IMM | I | I |
| SLTIU | INT_ALU | I | IMM | I | I |
| XORI | INT_ALU | I | IMM | I | I |
| ORI | INT_ALU | I | IMM | I | I |
| ANDI | INT_ALU | I | IMM | I | I |
| SLLI | INT_ALU | I | IMM | I | SHAMT |
| SRLI | INT_ALU | I | IMM | I | SHAMT |
| SRAI | INT_ALU | I | IMM | I | SHAMT |

Packed mapping uses `src0=SRC_INT_REG`, `src1=SRC_IMM`.

### 23.4 RV32I Register ALU

| Operation | FU | src0 | src1 | dst |
|---|---|---|---|---|
| ADD | INT_ALU | I | I | I |
| SUB | INT_ALU | I | I | I |
| SLL | INT_ALU | I | I | I |
| SLT | INT_ALU | I | I | I |
| SLTU | INT_ALU | I | I | I |
| XOR | INT_ALU | I | I | I |
| SRL | INT_ALU | I | I | I |
| SRA | INT_ALU | I | I | I |
| OR | INT_ALU | I | I | I |
| AND | INT_ALU | I | I | I |

Shift amount uses source bits `[4:0]`.

### 23.5 Ordering and System

| Operation | FU | Sources | dst | S/H | Behavior |
|---|---|---|---|---|---|
| FENCE | CSR_SERIAL | — | — | S,H | drain memory interface |
| ECALL | CSR_SERIAL | — | — | S,H | install M-mode ECALL exception |
| EBREAK | CSR_SERIAL | — | — | S,H | install breakpoint exception |
| MRET | CSR_SERIAL | — | — | S,H | retirement redirect to `mepc` |

FENCE predecessor/successor fields may be retained for trace/debug but do not alter the baseline one-outstanding drain behavior.

### 23.6 Zicsr

| Operation | FU | src0 | dst | CSR command | S/H |
|---|---|---|---|---|---|
| CSRRW | CSR_SERIAL | I | I | WRITE | S,H |
| CSRRS | CSR_SERIAL | I | I | SET | S,H |
| CSRRC | CSR_SERIAL | I | I | CLEAR | S,H |
| CSRRWI | CSR_SERIAL | Z | I | WRITE | S,H |
| CSRRSI | CSR_SERIAL | Z | I | SET | S,H |
| CSRRCI | CSR_SERIAL | Z | I | CLEAR | S,H |

Note: `Z` in `src0` refers to `src_kind_e = SRC_CSR_ZIMM` (zero-extended instruction bits `[19:15]`). `imm_kind` may concurrently be set to `IMM_CSR_ZIMM`. Integer `rd=x0` suppresses destination allocation. Source zero semantics determine CSR write-enable as specified in Section 12.

### 23.7 RV32M

| Operation | FU | src0 | src1 | dst |
|---|---|---|---|---|
| MUL | INT_MUL | I | I | I |
| MULH | INT_MUL | I | I | I |
| MULHSU | INT_MUL | I | I | I |
| MULHU | INT_MUL | I | I | I |
| DIV | INT_DIV | I | I | I |
| DIVU | INT_DIV | I | I | I |
| REM | INT_DIV | I | I | I |
| REMU | INT_DIV | I | I | I |

### 23.8 RV32F Loads and Stores

| Operation | FU | src0 | src1 | dst | Memory | LQ/SQ | Domain Flag |
|---|---|---|---|---|---|---|---|
| FLW | LSU_AGU | I base | — | F | word load | LQ (`alloc_lq=1`) | `mem_ctrl.is_fp=1` |
| FSW | LSU_AGU | I base | F data | — | word store | SQ (`alloc_sq=1`) | `mem_ctrl.is_fp=1` |

Address calculation remains integer-domain. `FSW` store data (`src1`) is FP-domain.

### 23.9 RV32F Fused Arithmetic

| Operation | FU | src0 | src1 | src2 | dst | Uses RM | Flags |
|---|---|---|---|---|---|---|---|
| FMADD.S | FP_FMA | F | F | F | F | yes | yes |
| FMSUB.S | FP_FMA | F | F | F | F | yes | yes |
| FNMSUB.S | FP_FMA | F | F | F | F | yes | yes |
| FNMADD.S | FP_FMA | F | F | F | F | yes | yes |

All fused operations use one final rounding.

### 23.10 RV32F Arithmetic

| Operation | FU | src0 | src1 | dst | Uses RM | Flags |
|---|---|---|---|---|---|---|
| FADD.S | FP_ADD | F | F | F | yes | yes |
| FSUB.S | FP_ADD | F | F | F | yes | yes |
| FMUL.S | FP_MUL | F | F | F | yes | yes |
| FDIV.S | FP_DIVSQRT | F | F | F | yes | yes |
| FSQRT.S | FP_DIVSQRT | F | — | F | yes | yes |

### 23.11 RV32F Sign, Min, and Max

| Operation | FU | src0 | src1 | dst | Uses RM | May set flags |
|---|---|---|---|---|---|---|
| FSGNJ.S | FP_MISC | F | F | F | no | no |
| FSGNJN.S | FP_MISC | F | F | F | no | no |
| FSGNJX.S | FP_MISC | F | F | F | no | no |
| FMIN.S | FP_MISC | F | F | F | no | yes |
| FMAX.S | FP_MISC | F | F | F | no | yes |

### 23.12 RV32F FP-to-Integer, Compare, and Classify

| Operation | FU | src0 | src1 | dst | Uses RM | May set flags |
|---|---|---|---|---|---|---|
| FCVT.W.S | FP_CONV | F | — | I | yes | yes |
| FCVT.WU.S | FP_CONV | F | — | I | yes | yes |
| FMV.X.W | FP_MISC | F | — | I | no | no |
| FEQ.S | FP_MISC | F | F | I | no | yes |
| FLT.S | FP_MISC | F | F | I | no | yes |
| FLE.S | FP_MISC | F | F | I | no | yes |
| FCLASS.S | FP_MISC | F | — | I | no | no |

### 23.13 RV32F Integer-to-FP and Move

| Operation | FU | src0 | dst | Uses RM | Flags |
|---|---|---|---|---|---|
| FCVT.S.W | FP_CONV | I | F | yes | yes |
| FCVT.S.WU | FP_CONV | I | F | yes | yes |
| FMV.W.X | FP_MISC | I | F | no | no |

## 24. Decode Legality Rules

Decode shall generate `UOP_EXCEPTION` with illegal-instruction cause when any of the following applies:

- opcode/funct fields do not match an implemented instruction;
- RV32-only reserved shift encoding is used;
- unsupported extension instruction is encountered;
- F instruction executes while `mstatus.FS=Off`;
- FP rounding encoding is reserved;
- dynamic rounding is requested while `frm` contains a reserved value;
- unimplemented CSR is accessed;
- CSR privilege or read-only rule is violated;
- FENCE.I, WFI, SRET, URET, or unsupported privileged instruction is encountered;
- malformed FMA format or unsupported FP format field is used.

A decode exception uop shall:

- preserve PC and instruction;
- allocate a ROB entry;
- allocate no destination physical register;
- allocate no IQ/LQ/SQ entry;
- be marked completed with exception metadata;
- trap only when it reaches ROB head.

## 25. Operation-Specific Result Rules

### 25.1 Integer x0

Any integer result with architectural destination `x0`:

- has no renamed destination;
- produces no writeback request;
- may still produce exception, branch, CSR, or memory side effects according to the instruction;
- completes without waiting for an integer write port unless another architectural side effect requires it.

### 25.2 JAL/JALR Link

When `rd != x0`, JAL/JALR completion contains:

- integer result `pc+4`;
- branch resolution metadata;
- both accepted atomically by the branch/output path.

When `rd=x0`, no result is produced, but branch resolution remains required.

### 25.3 CSR Result

A CSR instruction writes the pre-modification CSR value to integer destination when `rd != x0`.

CSR state update and destination writeback shall be coordinated so the instruction cannot partially retire. If integer writeback is blocked, the CSR serial engine holds the computed old/new values without architecturally updating the CSR until acceptance/retirement.

### 25.4 Store

A store has no register destination. Address and data readiness are recorded in SQ. The associated ROB entry becomes execution-complete when both are available or an exception has been recorded.

### 25.5 FP Flags Without Register Destination

FP compare and conversion instructions that write integer results may also produce FP flags. Their completion uses integer writeback domain while carrying FP flags to the ROB.

## 26. Writeback Producer Classes

### 26.1 Integer Writeback Producers

Potential producers:

- integer ALU;
- branch link result;
- multiplier;
- divider;
- integer load;
- FP-to-integer conversion;
- FP compare/classify/move-to-integer;
- CSR old value.

### 26.2 FP Writeback Producers

Potential producers:

- FP load;
- FP add/sub;
- FP multiply;
- FP fused unit;
- FP divide/sqrt;
- integer-to-FP conversion;
- move-to-FP;
- FP misc result.

### 26.3 Producer Holding Rule

Every producer shall retain its completion packet until:

- granted by its destination-domain arbiter; or
- explicitly killed and proven stale by recovery.

A producer shall not emit an unretained one-cycle `done` pulse.

## 27. Serialization Semantics in Uop Form

For a serializing uop:

```text
serializing       = 1
requires_rob_head = 1
```

Rename control behavior:

- allocate the serializing uop normally;
- set a global `serialize_pending` latch;
- block all younger rename until the uop retires or traps.

Issue behavior:

- source operands may wake normally;
- select only when `uop.rob_tag == rob_head_tag`;
- apply operation-specific conditions such as memory drain for FENCE.

Recovery behavior:

- if the serializing uop is younger than a mispredicted branch, flush it and clear `serialize_pending`;
- if it traps, trap recovery clears the latch;
- no younger uop should exist by construction, but assertions shall verify this.

## 28. Same-Cycle Ordering Rules

The following same-cycle cases shall be explicitly supported and tested.

### 28.1 Writeback and Rename

If rename reads a source whose current RAT mapping matches an accepted same-cycle writeback:

- physical tag remains unchanged;
- source ready captured as 1.

### 28.2 Retirement and Allocation

A physical register freed by retirement shall be made available for allocation in the same cycle via deterministic free-list bypass (`retirement-to-allocation bypass`). This prevents false rename stalls when free list entry count is zero.

### 28.3 Issue Wakeup and Select

Baseline policy:

- accepted writeback updates readiness for the next cycle;
- an already resident dependent uop is not required to wake and issue in the same cycle as producer writeback;
- newly dispatched uop must capture the writeback bypass to avoid a lost wakeup.

This gives a one-cycle wakeup-to-issue delay and simplifies timing.

### 28.4 Branch Mispredict and Completion

When a valid branch mispredict is accepted:

- younger completions in the same cycle are rejected;
- older completions may be accepted;
- branch completion itself is accepted;
- no younger instruction retires.

### 28.5 Trap and Branch Mispredict

A ROB-head precise trap has priority over a younger branch misprediction. The branch completion may be discarded as part of trap recovery.

## 29. Assertions for Uop Correctness

### 29.1 Decode Assertions

- every legal instruction maps to exactly one expected `uop_op_e`;
- every illegal instruction maps to `UOP_EXCEPTION`;
- register source/destination domains match the semantic table;
- `uses_rm` only appears on allowed FP operations;
- reserved RM values cannot enter rename;
- memory allocation flags match memory operation;
- serializing flag matches the serializing operation list.

### 29.2 Rename Assertions

- every register source gets a valid RAT physical tag;
- non-register sources are ready;
- integer x0 never allocates;
- FP f0 may allocate;
- destination new physical tag was free before allocation;
- new and old physical tags differ unless explicitly allowed by a no-allocation case;
- dynamic RM is resolved;
- allocation is all-or-nothing.

### 29.3 Issue Assertions

- issued uop is valid and operand-ready;
- FU class supports operation;
- source domain matches selected PRF port;
- stale or flushed uop never issues;
- serializing uop issues only at ROB head;
- memory uop carries matching LQ/SQ tag.

### 29.4 Completion Assertions

- accepted result domain matches destination domain;
- accepted destination physical tag matches ROB;
- full ROB tag matches;
- accepted completion occurs at most once per ROB entry;
- FP flags are zero/invalid for operations that cannot set flags;
- branch metadata only appears for branch operations;
- stale completion causes no state update;
- `exception.valid` is 0 for all normal, successful non-excepting completions.

## 30. Decoder Test Matrix

The decoder unit test shall cover at least:

1. every supported instruction with minimum and maximum register indices;
2. every immediate sign boundary;
3. every branch and jump immediate bit position;
4. legal and illegal shift encodings;
5. `rd=x0`, `rs1=x0`, and `rs2=x0` cases;
6. every CSR instruction with zero and nonzero source/zimm;
7. legal, dynamic, and reserved FP rounding modes;
8. every FP instruction format and register field;
9. unsupported opcode/funct combinations;
10. F instruction when FS is Off;
11. unsupported privileged instructions;
12. fetch/decode exception injection.

A generated decode test should compare the complete `decoded_uop_t` payload, not only `op`.

## 31. Trace and Debug Representation

The uop enum and key metadata may be converted to human-readable strings in simulation-only code.

Recommended trace fields:

```text
cycle
rob_seq:rob_idx
pc
insn
uop_name
src0 kind/tag/ready
src1 kind/tag/ready
src2 kind/tag/ready
dst domain/arch/new/old
lq/sq tag
issue_cycle
complete_cycle
retire_cycle
exception
fp_flags
```

String conversion, large debug tables, and historical trace arrays shall not be synthesized into the PPA core.

## 32. Versioning and Compatibility

A uop-spec major version increment is required when:

- operation semantics change;
- a source slot changes meaning;
- a destination domain changes;
- a new architectural instruction requires a different retirement model;
- completion validation changes;
- ROB tag or queue tag format changes;
- an instruction begins mapping to more than one internal uop.

A minor version increment is sufficient for:

- adding a reserved enum value;
- adding debug-only metadata;
- clarifying an invariant without changing hardware behavior.

## Appendix A. Recommended SystemVerilog Skeleton

```systemverilog
package rv32_uop_pkg;

  parameter int XLEN            = 32;
  parameter int FLEN            = 32;
  parameter int INT_PRF_ENTRIES = 48;
  parameter int FP_PRF_ENTRIES  = 48;
  parameter int ROB_ENTRIES     = 16;
  parameter int ROB_SEQ_WIDTH   = 12;
  parameter int LQ_ENTRIES      = 4;
  parameter int SQ_ENTRIES      = 4;

  // Widths and base types
  // Enums
  // decoded_src_t / renamed_src_t
  // decoded_dst_t / renamed_dst_t
  // decoded_uop_t / renamed_uop_t
  // completion_t / rob_entry_t
  // LQ/SQ entries

  function automatic logic rob_tag_equal(rob_tag_t a, rob_tag_t b);
    return a == b;
  endfunction

  function automatic logic rob_is_younger(rob_tag_t a, rob_tag_t b);
    logic [ROB_SEQ_WIDTH-1:0] delta;
    delta = a.seq - b.seq;
    return (delta != '0) && !delta[ROB_SEQ_WIDTH-1];
  endfunction

  function automatic logic src_is_register(src_kind_e kind);
    return (kind == SRC_INT_REG) || (kind == SRC_FP_REG);
  endfunction

  function automatic reg_domain_e src_domain(src_kind_e kind);
    case (kind)
      SRC_INT_REG: return REG_INT;
      SRC_FP_REG:  return REG_FP;
      default:     return REG_NONE;
    endcase
  endfunction

endpackage
```

The exact age-comparison implementation shall be formally checked under the configured sequence-space and maximum-live assumptions.

## Appendix B. Decode Review Checklist

- [ ] All RV32I operations are present.
- [ ] All RV32M operations are present.
- [ ] All mandatory RV32F operations are present.
- [ ] All six Zicsr operations are present.
- [ ] FENCE is implemented; FENCE.I is rejected.
- [ ] MRET is implemented; unsupported return instructions are rejected.
- [ ] Integer x0 destination suppression is explicit.
- [ ] FP f0 is treated as an ordinary destination.
- [ ] FMA has three FP sources.
- [ ] FSW has integer address source and FP data source.
- [ ] Cross-domain conversions and moves have correct destination domains.
- [ ] FP compare result is integer-domain.
- [ ] Dynamic RM is resolved before issue.
- [ ] Fetch and decode faults can create exception-only uops.
- [ ] All serializing instructions are marked consistently.

## Appendix C. Baseline Microarchitectural Decisions (Frozen)

The baseline microarchitectural decisions listed in `architecture_spec.md` Appendix C are frozen for the G0 signoff baseline.
