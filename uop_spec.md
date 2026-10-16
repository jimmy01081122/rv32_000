# RV32 OoO micro-operation reference

Version 0.3 — 2026-10-16. Status: reference to the implemented AP5B schema.

The authoritative packed declarations are in
[rv32_ooo_types.sv](rtl/pkg/rv32_ooo_types.sv), with widths imported from
[rv32_ooo_params.sv](rtl/pkg/rv32_ooo_params.sv). The package names are
`rv32_ooo_types` and `rv32_ooo_params`.
The [archived G0 proposal](docs/archive/g0/uop_spec.md) retains its original
semantic tables and the section numbers used in legacy source comments.

## Identity and operands

| Type | Implemented representation |
| --- | --- |
| `arch_reg_t` | 5-bit architectural register index |
| `phys_reg_t` | 6-bit physical index; domain is carried separately |
| `rob_tag_t` | 12-bit `seq`, 4-bit `idx` |
| `lq_tag_t`, `sq_tag_t` | 4-bit generation + 4-bit index fields; see usage limitations below |
| `fetch_meta_t` | 4-bit epoch, predicted direction and target |
| `decoded_src_t` | Source kind and architectural index |
| `renamed_src_t` | Source kind, physical index and readiness |
| `decoded_dst_t` | Valid, register domain and architectural index |
| `renamed_dst_t` | Destination metadata plus new/old physical ownership |

Source kinds include integer/FP registers, PC, immediate, zero, CSR immediate and
no source. Integer x0 suppresses destination allocation; FP f0 is an ordinary
architectural destination. A physical index alone does not identify a register
without its domain.

## Pipeline packets

| Packet | Contents and consumers |
| --- | --- |
| `decoded_uop_t` | PC/instruction/fetch metadata, opcode/FU class, three sources, destination, immediate, memory/branch/CSR/FP controls, scheduling bits and exception |
| `renamed_uop_t` | Decoded identity/control with ROB tag, renamed sources/destination and LQ/SQ fields |
| `issue_entry_t` | Valid bit and renamed uop |
| `exec_req_t` | Renamed uop and three 32-bit operand values |
| `completion_t` | Full ROB tag, optional register result, exception, FP flags, branch result and memory association |
| `rob_entry_t` | Valid/completed identity, destination metadata, `result_data`, operation classifications, exception/FP/branch state and store state |
| `dmem_pending_t` | Valid, ROB identity and memory association fields for outstanding or buffered LSU work |
| `commit_trace_t` | Retire/trap event, order, PC/instruction, register results, store payload, trap fields and FP flags |

Opcode and FU enums describe routing. `UOP_FENCE_I` exists in addition to the
original G0 enumeration. Classification as `FU_FP_*` does not imply a particular
latency or a dedicated instance for every enum value; consult the execution
cluster and core completion arbitration.

Control families:

- `mem_ctrl_t`: load/store, FP data domain, byte/half/word size and sign extension.
- `branch_ctrl_t`: branch kind and link-write intent.
- `csr_ctrl_t`: command, address, immediate selection, read/write enables.
- `fp_ctrl_t`: FP validity, rounding-mode use and flag-update intent.
- `exception_t`: validity, cause and `tval`.

## Declared fields versus implemented structures

`alloc_lq`, `lq_valid`, `lq_tag_t` and `lq_entry_t` remain in the schema. The current
LSU does not allocate an `lq_entry_t` array. Rename assigns zero LQ/SQ tags;
the LSU's actual 16-entry store array uses its local `sq_slot_t`, not the package's
proposed `sq_entry_t`. Do not infer a working generational LSQ allocator or
multiple outstanding loads from the presence of these declarations.

AP5B extends the lifetime represented by `dmem_pending.valid` through response
buffer consumption. The old description that it always clears at external
response handshake is obsolete. Any future overlap of requests and completions
must revisit the single-record ROB alias guard.

The ROB stores `result_data` for retirement trace construction. Its trace emits
store memory payloads; a general load-memory trace is not currently populated.
The trace's `fflags` field is assigned the retiring entry's flags, so it must not
be described as a verified snapshot of the complete architectural accrued flags.
The Python differential parser leaves trap cause/tval unset. Packet fields alone
do not establish end-to-end comparison coverage.

## Requirements for changes

Changes must preserve register-domain ownership, full ROB identity, result and
exception association, ordering and recovery behavior. Reserved fields must not
be treated as implemented mechanisms without allocation/use/flush tests.

For any packet change, review all producers, consumers, completion arbitration,
SV/C++ trace extraction and reference comparison. In particular, the C++ harness
extracts the packed trace using layout assumptions; a type edit can invalidate
verification even when RTL elaboration passes. Use the review process in
[PLAN.md](PLAN.md), and record unmet obligations in [STATUS.md](docs/STATUS.md).
