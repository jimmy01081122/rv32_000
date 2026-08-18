# 03 Coverage Findings

## Section 1: Instruction Coverage Matrix

| instruction | uop_op_e | semantic_table | fu_class | src0 | src1 | src2 | dst | imm | mem | branch | csr | fp | serial | rob_head | lq | sq | STATUS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LUI | UOP_LUI | §23.1 | INT_ALU | IMM | — | — | I | U | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| AUIPC | UOP_AUIPC | §23.1 | INT_ALU | PC | IMM | — | I | U | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| JAL | UOP_JAL | §23.1 | BRANCH | PC | IMM | — | I | J | — | JAL | — | — | 0 | 0 | 0 | 0 | ✓ |
| JALR | UOP_JALR | §23.1 | BRANCH | I | IMM | — | I | I | — | JALR | — | — | 0 | 0 | 0 | 0 | ✓ |
| BEQ | UOP_BEQ | §23.1 | BRANCH | I | I | — | — | B | — | EQ | — | — | 0 | 0 | 0 | 0 | ⚠ |
| BNE | UOP_BNE | §23.1 | BRANCH | I | I | — | — | B | — | NE | — | — | 0 | 0 | 0 | 0 | ⚠ |
| BLT | UOP_BLT | §23.1 | BRANCH | I | I | — | — | B | — | LT | — | — | 0 | 0 | 0 | 0 | ⚠ |
| BGE | UOP_BGE | §23.1 | BRANCH | I | I | — | — | B | — | GE | — | — | 0 | 0 | 0 | 0 | ⚠ |
| BLTU | UOP_BLTU | §23.1 | BRANCH | I | I | — | — | B | — | LTU | — | — | 0 | 0 | 0 | 0 | ⚠ |
| BGEU | UOP_BGEU | §23.1 | BRANCH | I | I | — | — | B | — | GEU | — | — | 0 | 0 | 0 | 0 | ⚠ |
| LB | UOP_LB | §23.2 | LSU_AGU | I | — | — | I | I | byte,s | — | — | — | 0 | 0 | 1 | 0 | ✓ |
| LH | UOP_LH | §23.2 | LSU_AGU | I | — | — | I | I | half,s | — | — | — | 0 | 0 | 1 | 0 | ✓ |
| LW | UOP_LW | §23.2 | LSU_AGU | I | — | — | I | I | word,s | — | — | — | 0 | 0 | 1 | 0 | ✓ |
| LBU | UOP_LBU | §23.2 | LSU_AGU | I | — | — | I | I | byte,u | — | — | — | 0 | 0 | 1 | 0 | ✓ |
| LHU | UOP_LHU | §23.2 | LSU_AGU | I | — | — | I | I | half,u | — | — | — | 0 | 0 | 1 | 0 | ✓ |
| SB | UOP_SB | §23.2 | LSU_AGU | I | I | — | — | S | byte | — | — | — | 0 | 0 | 0 | 1 | ✓ |
| SH | UOP_SH | §23.2 | LSU_AGU | I | I | — | — | S | half | — | — | — | 0 | 0 | 0 | 1 | ✓ |
| SW | UOP_SW | §23.2 | LSU_AGU | I | I | — | — | S | word | — | — | — | 0 | 0 | 0 | 1 | ✓ |
| ADDI | UOP_ADDI | §23.3 | INT_ALU | I | IMM | — | I | I | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| SLTI | UOP_SLTI | §23.3 | INT_ALU | I | IMM | — | I | I | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| SLTIU | UOP_SLTIU | §23.3 | INT_ALU | I | IMM | — | I | I | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| XORI | UOP_XORI | §23.3 | INT_ALU | I | IMM | — | I | I | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| ORI | UOP_ORI | §23.3 | INT_ALU | I | IMM | — | I | I | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| ANDI | UOP_ANDI | §23.3 | INT_ALU | I | IMM | — | I | I | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| SLLI | UOP_SLLI | §23.3 | INT_ALU | I | IMM | — | I | SHAMT | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| SRLI | UOP_SRLI | §23.3 | INT_ALU | I | IMM | — | I | SHAMT | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| SRAI | UOP_SRAI | §23.3 | INT_ALU | I | IMM | — | I | SHAMT | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| ADD | UOP_ADD | §23.4 | INT_ALU | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| SUB | UOP_SUB | §23.4 | INT_ALU | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| SLL | UOP_SLL | §23.4 | INT_ALU | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| SLT | UOP_SLT | §23.4 | INT_ALU | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| SLTU | UOP_SLTU | §23.4 | INT_ALU | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| XOR | UOP_XOR | §23.4 | INT_ALU | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| SRL | UOP_SRL | §23.4 | INT_ALU | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| SRA | UOP_SRA | §23.4 | INT_ALU | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| OR | UOP_OR | §23.4 | INT_ALU | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| AND | UOP_AND | §23.4 | INT_ALU | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| FENCE | UOP_FENCE | §23.5 | CSR_SERIAL | — | — | — | — | — | — | — | — | — | 1 | 1 | 0 | 0 | ✓ |
| ECALL | UOP_ECALL | §23.5 | CSR_SERIAL | — | — | — | — | — | — | — | — | — | 1 | 1 | 0 | 0 | ✓ |
| EBREAK | UOP_EBREAK | §23.5 | CSR_SERIAL | — | — | — | — | — | — | — | — | — | 1 | 1 | 0 | 0 | ✓ |
| MRET | UOP_MRET | §23.5 | CSR_SERIAL | — | — | — | — | — | — | — | — | — | 1 | 1 | 0 | 0 | ✓ |
| CSRRW | UOP_CSRRW | §23.6 | CSR_SERIAL | I | — | — | I | — | — | — | WRITE | — | 1 | 1 | 0 | 0 | ✓ |
| CSRRS | UOP_CSRRS | §23.6 | CSR_SERIAL | I | — | — | I | — | — | — | SET | — | 1 | 1 | 0 | 0 | ✓ |
| CSRRC | UOP_CSRRC | §23.6 | CSR_SERIAL | I | — | — | I | — | — | — | CLEAR | — | 1 | 1 | 0 | 0 | ✓ |
| CSRRWI | UOP_CSRRWI | §23.6 | CSR_SERIAL | Z | — | — | I | ZIMM | — | — | WRITE | — | 1 | 1 | 0 | 0 | ✓ |
| CSRRSI | UOP_CSRRSI | §23.6 | CSR_SERIAL | Z | — | — | I | ZIMM | — | — | SET | — | 1 | 1 | 0 | 0 | ✓ |
| CSRRCI | UOP_CSRRCI | §23.6 | CSR_SERIAL | Z | — | — | I | ZIMM | — | — | CLEAR | — | 1 | 1 | 0 | 0 | ✓ |
| MUL | UOP_MUL | §23.7 | INT_MUL | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| MULH | UOP_MULH | §23.7 | INT_MUL | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| MULHSU | UOP_MULHSU | §23.7 | INT_MUL | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| MULHU | UOP_MULHU | §23.7 | INT_MUL | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| DIV | UOP_DIV | §23.7 | INT_DIV | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| DIVU | UOP_DIVU | §23.7 | INT_DIV | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| REM | UOP_REM | §23.7 | INT_DIV | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| REMU | UOP_REMU | §23.7 | INT_DIV | I | I | — | I | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| FLW | UOP_FLW | §23.8 | LSU_AGU | I | — | — | F | I | word,fp | — | — | — | 0 | 0 | 1 | 0 | ✗ |
| FSW | UOP_FSW | §23.8 | LSU_AGU | I | F | — | — | S | word,fp | — | — | — | 0 | 0 | 0 | 1 | ✗ |
| FMADD.S | UOP_FMADD_S | §23.9 | FP_FMA | F | F | F | F | — | — | — | — | RM,flags | 0 | 0 | 0 | 0 | ✓ |
| FMSUB.S | UOP_FMSUB_S | §23.9 | FP_FMA | F | F | F | F | — | — | — | — | RM,flags | 0 | 0 | 0 | 0 | ✓ |
| FNMSUB.S | UOP_FNMSUB_S | §23.9 | FP_FMA | F | F | F | F | — | — | — | — | RM,flags | 0 | 0 | 0 | 0 | ✓ |
| FNMADD.S | UOP_FNMADD_S | §23.9 | FP_FMA | F | F | F | F | — | — | — | — | RM,flags | 0 | 0 | 0 | 0 | ✓ |
| FADD.S | UOP_FADD_S | §23.10 | FP_ADD | F | F | — | F | — | — | — | — | RM,flags | 0 | 0 | 0 | 0 | ✓ |
| FSUB.S | UOP_FSUB_S | §23.10 | FP_ADD | F | F | — | F | — | — | — | — | RM,flags | 0 | 0 | 0 | 0 | ✓ |
| FMUL.S | UOP_FMUL_S | §23.10 | FP_MUL | F | F | — | F | — | — | — | — | RM,flags | 0 | 0 | 0 | 0 | ✓ |
| FDIV.S | UOP_FDIV_S | §23.10 | FP_DIVSQRT | F | F | — | F | — | — | — | — | RM,flags | 0 | 0 | 0 | 0 | ✓ |
| FSQRT.S | UOP_FSQRT_S | §23.10 | FP_DIVSQRT | F | — | — | F | — | — | — | — | RM,flags | 0 | 0 | 0 | 0 | ✓ |
| FSGNJ.S | UOP_FSGNJ_S | §23.11 | FP_MISC | F | F | — | F | — | — | — | — | no | 0 | 0 | 0 | 0 | ✓ |
| FSGNJN.S | UOP_FSGNJN_S | §23.11 | FP_MISC | F | F | — | F | — | — | — | — | no | 0 | 0 | 0 | 0 | ✓ |
| FSGNJX.S | UOP_FSGNJX_S | §23.11 | FP_MISC | F | F | — | F | — | — | — | — | no | 0 | 0 | 0 | 0 | ✓ |
| FMIN.S | UOP_FMIN_S | §23.11 | FP_MISC | F | F | — | F | — | — | — | — | flags | 0 | 0 | 0 | 0 | ✓ |
| FMAX.S | UOP_FMAX_S | §23.11 | FP_MISC | F | F | — | F | — | — | — | — | flags | 0 | 0 | 0 | 0 | ✓ |
| FCVT.W.S | UOP_FCVT_W_S | §23.12 | FP_CONV | F | — | — | I | — | — | — | — | RM,flags | 0 | 0 | 0 | 0 | ✓ |
| FCVT.WU.S | UOP_FCVT_WU_S | §23.12 | FP_CONV | F | — | — | I | — | — | — | — | RM,flags | 0 | 0 | 0 | 0 | ✓ |
| FMV.X.W | UOP_FMV_X_W | §23.12 | FP_MISC | F | — | — | I | — | — | — | — | no | 0 | 0 | 0 | 0 | ✓ |
| FEQ.S | UOP_FEQ_S | §23.12 | FP_MISC | F | F | — | I | — | — | — | — | flags | 0 | 0 | 0 | 0 | ✓ |
| FLT.S | UOP_FLT_S | §23.12 | FP_MISC | F | F | — | I | — | — | — | — | flags | 0 | 0 | 0 | 0 | ✓ |
| FLE.S | UOP_FLE_S | §23.12 | FP_MISC | F | F | — | I | — | — | — | — | flags | 0 | 0 | 0 | 0 | ✓ |
| FCLASS.S | UOP_FCLASS_S | §23.12 | FP_MISC | F | — | — | I | — | — | — | — | no | 0 | 0 | 0 | 0 | ✓ |
| FCVT.S.W | UOP_FCVT_S_W | §23.13 | FP_CONV | I | — | — | F | — | — | — | — | RM,flags | 0 | 0 | 0 | 0 | ✓ |
| FCVT.S.WU | UOP_FCVT_S_WU | §23.13 | FP_CONV | I | — | — | F | — | — | — | — | RM,flags | 0 | 0 | 0 | 0 | ✓ |
| FMV.W.X | UOP_FMV_W_X | §23.13 | FP_MISC | I | — | — | F | — | — | — | — | no | 0 | 0 | 0 | 0 | ✓ |
| UOP_INVALID | UOP_INVALID | §5, §24 | — | — | — | — | — | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |
| UOP_EXCEPTION | UOP_EXCEPTION | §5, §24 | FU_EXCEPTION | — | — | — | — | — | — | — | — | — | 0 | 0 | 0 | 0 | ✓ |

## Section 2: Findings

### [F-01] Missing LQ/SQ Allocation for FP Memory Operations
- **Severity**: HIGH
- **Category**: Allocation
- **Location**: `uop_spec.md` §23.8
- **Finding**: The semantic table for RV32F Loads and Stores (Table 23.8) omits the LQ/SQ allocation requirements. The `decoded_uop_t` invariants (§15.1) explicitly require that exactly one of `alloc_lq` or `alloc_sq` is set for memory operations, but this mapping is missing for FLW and FSW.
- **Proposed Correction**: Add an `LQ/SQ` column to Table 23.8, specifying "LQ" for `FLW` and "SQ" for `FSW`.

### [F-02] Ambiguous `src2` Representation for Conditional Branches
- **Severity**: LOW
- **Category**: Coverage
- **Location**: `uop_spec.md` §23.1
- **Finding**: Table 23.1 visually places `IMM` in the `src2` column for conditional branches (BEQ, BNE, etc.). Although the text below the table clarifies this is only conceptual and that normative mapping sets `src2=SRC_NONE` while using the `imm` field, the table itself is contradictory to the formal uop structure.
- **Proposed Correction**: Update Table 23.1 to show `—` in the `src2` column for all conditional branches, relying solely on the `Immediate` column for the B-type immediate.

### [F-03] Missing `is_fp` Definition in FP Memory Table
- **Severity**: MEDIUM
- **Category**: Domain
- **Location**: `uop_spec.md` §23.8
- **Finding**: Section 10.2 defines `is_fp` to identify the FLW/FSW data domain. However, Table 23.8 does not explicitly specify that the `mem_ctrl_t.is_fp` flag must be asserted. Without this in the normative semantic table, decode implementations might omit the flag.
- **Proposed Correction**: Add a "Memory Control" or "Domain" column to Table 23.8 that explicitly assigns `is_fp = 1` for `FLW` and `FSW`.

### [F-04] Audit Scope Instruction Count Discrepancy
- **Severity**: LOW
- **Category**: Coverage
- **Location**: Audit Prompt / Scope Definition
- **Finding**: The audit scope mentions "RV32I (47 instructions)" and "Total: 88 instructions", but only explicitly lists exactly 40 RV32I instructions, yielding a total of 81 specified instructions (plus `UOP_INVALID` and `UOP_EXCEPTION`). The `uop_op_e` enum correctly contains exactly the 81 instructions listed (totaling 83 enum values).
- **Proposed Correction**: Correct the expected instruction count documentation to reflect the actual 81 supported operations (40 Base + 8 M + 26 F + 6 Zicsr + 1 System).

### [F-05] `CSR` Immediate Source Field Ambiguity
- **Severity**: LOW
- **Category**: Immediate
- **Location**: `uop_spec.md` §23.6
- **Finding**: The Zicsr semantic table uses `Z` in the `src0` column for `CSRRWI`, `CSRRSI`, and `CSRRCI`. Section 7.1 defines `SRC_CSR_ZIMM`, which fits `src0`. However, Section 9 also defines an `IMM_CSR_ZIMM` immediate type. It is slightly ambiguous whether the `zimm` value is routed through `src0` via PRF read bypass or via the `imm` payload field.
- **Proposed Correction**: Add a footnote to Table 23.6 clarifying that `Z` refers to `src_kind_e = SRC_CSR_ZIMM`, and clarify whether `imm_kind_e = IMM_CSR_ZIMM` should also be populated concurrently.
