`ifndef RV32_OOO_DEFS_VH
`define RV32_OOO_DEFS_VH

// rv32_ooo_defs.vh — Yosys-compatible flat defines
// Mirrors rv32_ooo_params.sv + rv32_ooo_types.sv for Yosys 0.9.
// Yosys 0.9 does not support SystemVerilog packages (typedef/enum in packages).
// This file is NOT used by Verilator flows — use the proper SV packages instead.

// ---- Parameters ----
`define XLEN          32
`define FLEN          32
`define ARCH_REG_W    5
`define PHYS_W        6
`define ROB_SEQ_WIDTH 12
`define ROB_IDX_W     4
`define LQ_IDX_W      2
`define SQ_IDX_W      2
`define LSQ_GEN_W     4
`define FETCH_EPOCH_W 4
`define ROB_ENTRIES   16
`define INT_PRF_ENTRIES 48
`define FP_PRF_ENTRIES  48

`endif // RV32_OOO_DEFS_VH
