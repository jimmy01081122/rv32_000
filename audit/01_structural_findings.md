### [1] Instruction Queue Entries Parameter Discrepancy
- **Severity**: LOW
- **Category**: Parameter
- **Location**: PLAN.md §4 vs architecture_spec.md §6
- **Finding**: PLAN.md specifies a range for the instruction queue (4-8 entries), while architecture_spec.md fixes it to exactly 8.
- **Evidence**:
  - PLAN.md: `Instruction Queue | 4–8 entries`
  - architecture_spec.md: `INSTR_QUEUE_ENTRIES = 8`
- **Proposed Correction**: Update PLAN.md to specify `8 entries` to perfectly align with the normative baseline configuration in architecture_spec.md.

### [2] Uop Opcode Enum Naming Discrepancy
- **Severity**: MEDIUM
- **Category**: Type / Naming
- **Location**: PLAN.md §6.2 vs uop_spec.md §5
- **Finding**: PLAN.md uses `uop_opcode_e` and `opcode` in the `decoded_uop_t` struct, whereas uop_spec.md defines and uses `uop_op_e` and `op`.
- **Evidence**:
  - PLAN.md: `uop_opcode_e opcode;`
  - uop_spec.md: `typedef enum logic [7:0] { ... } uop_op_e;` and `uop_op_e op;`
- **Proposed Correction**: Standardize on `uop_op_e` and rename `opcode` to `op` in PLAN.md to match uop_spec.md.

### [3] Physical Register Tag Type Naming
- **Severity**: MEDIUM
- **Category**: Type / Naming
- **Location**: PLAN.md §8.1 vs uop_spec.md §4.1
- **Finding**: PLAN.md uses `phys_tag_t` across multiple structs, but uop_spec.md explicitly defines and uses `phys_reg_t`.
- **Evidence**:
  - PLAN.md: `phys_tag_t new_phys_rd;`
  - uop_spec.md: `typedef logic [PHYS_W-1:0] phys_reg_t;`
- **Proposed Correction**: Replace all instances of `phys_tag_t` with `phys_reg_t` in PLAN.md.

### [4] `rob_entry_t` Struct Divergence
- **Severity**: HIGH
- **Category**: Type
- **Location**: PLAN.md §8.1 vs uop_spec.md §20
- **Finding**: The `rob_entry_t` definition differs significantly. PLAN.md uses flattened fields (`arch_rd`, `new_phys_rd`, `exception_valid`), while uop_spec.md encapsulates these into nested structs (`renamed_dst_t dst`, `exception_t exception`, `fp_flags_t fp_flags`). Furthermore, uop_spec.md adds fields missing from PLAN.md such as `op`, `serializing`, `store_req_sent`, and uses `lq_tag_t`/`sq_tag_t` instead of a flat index.
- **Evidence**:
  - PLAN.md: `logic [4:0] arch_rd; phys_tag_t new_phys_rd;`
  - uop_spec.md: `renamed_dst_t dst;`
- **Proposed Correction**: Replace the `rob_entry_t` struct in PLAN.md with the normative struct defined in uop_spec.md.

### [5] LSQ Index Width vs LSQ Tag Type
- **Severity**: HIGH
- **Category**: Width / Type
- **Location**: PLAN.md §8.1 vs uop_spec.md §4.3
- **Finding**: PLAN.md uses a single `LSQ_W` parameter for `lq_index` and `sq_index`. uop_spec.md uses structured tags (`lq_tag_t` and `sq_tag_t`) containing both a generation bit and a separate index (`LQ_IDX_W`/`SQ_IDX_W`).
- **Evidence**:
  - PLAN.md: `logic [LSQ_W-1:0] lq_index;`
  - uop_spec.md: `logic lq_valid; lq_tag_t lq_tag;`
- **Proposed Correction**: Remove references to `LSQ_W` from PLAN.md and adopt the `lq_tag_t`/`sq_tag_t` types from uop_spec.md.

### [6] `decoded_uop_t` Struct Divergence
- **Severity**: HIGH
- **Category**: Type
- **Location**: PLAN.md §6.2 vs uop_spec.md §15
- **Finding**: The `decoded_uop_t` structure in PLAN.md is completely flat and uses 1-based indexing for architectural sources (`rs1`, `rs2`, `rs3`, `rd`). uop_spec.md uses 0-based packed structs (`src0`, `src1`, `src2`, `dst`) and encapsulates control signals into `mem_ctrl_t`, `branch_ctrl_t`, `csr_ctrl_t`, and `fp_ctrl_t`.
- **Evidence**:
  - PLAN.md: `logic [4:0] arch_rs1; ... logic [2:0] rounding_mode;`
  - uop_spec.md: `decoded_src_t src0; ... fp_ctrl_t fp;`
- **Proposed Correction**: Replace the `decoded_uop_t` block in PLAN.md with the normative version from uop_spec.md.

### [7] Issue Queue Entry Struct Discrepancy
- **Severity**: MEDIUM
- **Category**: Type
- **Location**: PLAN.md §10.1 vs uop_spec.md §17
- **Finding**: PLAN.md defines `int_iq_entry_t` containing flattened ready bits and physical tags, alongside an undefined `uop_t`. uop_spec.md defines `issue_entry_t` which contains a single `valid` bit and a `renamed_uop_t` struct (which inherently tracks source tags and ready states).
- **Evidence**:
  - PLAN.md: `phys_tag_t src1_tag; logic src1_ready; uop_t uop;`
  - uop_spec.md: `logic valid; renamed_uop_t uop;`
- **Proposed Correction**: Update PLAN.md to reflect the encapsulated `issue_entry_t` design defined in uop_spec.md.

### [8] Immediate vs Imm Field Naming
- **Severity**: LOW
- **Category**: Naming
- **Location**: PLAN.md §6.2 vs uop_spec.md §15
- **Finding**: PLAN.md names the immediate field `immediate`, while uop_spec.md consistently uses `imm`.
- **Evidence**:
  - PLAN.md: `logic [31:0] immediate;`
  - uop_spec.md: `logic [31:0] imm;`
- **Proposed Correction**: Change `immediate` to `imm` in PLAN.md for consistency across the codebase.

### [9] Synthesizability Issue: SystemVerilog `inside` Operator
- **Severity**: HIGH
- **Category**: Synth
- **Location**: uop_spec.md Appendix A (Line 1488)
- **Finding**: The `inside` operator is used to check `src.kind` against a set of values. While part of SystemVerilog, `inside` can cause synthesis failures or unexpected behavior in some open-source ASIC synthesis flows (like Yosys).
- **Evidence**:
  - uop_spec.md: `return (src.kind inside {SRC_NONE, SRC_PC, SRC_IMM, SRC_ZERO, SRC_CSR_ZIMM})`
- **Proposed Correction**: Replace `inside` with an explicit logical OR (`==` chains) or a standard `case` statement to ensure Yosys compatibility.

### [10] Synthesizability Issue: SystemVerilog `unique case` Operator
- **Severity**: HIGH
- **Category**: Synth
- **Location**: uop_spec.md Appendix A (Line 1492)
- **Finding**: The `unique case` keyword is used. Open-source tools like Yosys may have partial or buggy support for `unique case`, potentially leading to synthesis failures.
- **Evidence**:
  - uop_spec.md: `unique case (kind)`
- **Proposed Correction**: Use a standard `case` statement without the `unique` qualifier, or use a synthesis pragma if uniqueness is strictly required for optimization.
