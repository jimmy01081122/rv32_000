# RV32 OoO Core Architecture Specification

| Item | Value |
|---|---|
| Document | `architecture_spec.md` |
| Version | 0.2.2 |
| Status | G0 Frozen — 2026-08-08 |
| Core name | `rv32_ooo_core` |
| ISA target | RV32IMF + Zicsr |
| Execution environment | Bare-metal, Machine mode subset |
| Implementation target | Synthesizable SystemVerilog, ASIC PPA research |
| Physical-design targets | Nangate45 exploration; SKY130HD baseline |
| FPGA target | Out of scope |

## 1. Purpose

This document defines the architectural and microarchitectural contract for a scalar out-of-order RV32 processor core with integer multiply/divide and single-precision floating-point support.

The document is normative for:

- RTL module boundaries;
- pipeline and queue behavior;
- architectural-state visibility;
- speculative-state recovery;
- exception and retirement semantics;
- memory-interface ordering;
- floating-point state handling;
- verification and ASIC signoff criteria.

The detailed micro-operation format is specified in [`uop_spec.md`](./uop_spec.md).

## 2. Design Objectives

The core shall provide:

1. RV32I base integer execution.
2. Complete RV32M integer multiply/divide execution.
3. Complete RV32F single-precision floating-point execution before the design is labeled RV32IMF-compliant.
4. Zicsr CSR instructions.
5. Register renaming with separate integer and floating-point physical-register domains.
6. Out-of-order issue and completion.
7. In-order, one-instruction-per-cycle retirement.
8. Precise synchronous exceptions.
9. Conservative memory ordering with store-to-load forwarding.
10. Deterministic branch-misprediction recovery.
11. Commit-level differential testing against an ISA reference model.
12. Reproducible synthesis, timing, place-and-route, and PPA analysis.

## 3. Non-Goals

The baseline shall not implement or claim support for:

- RV32C compressed instructions;
- RV32A atomics;
- Zifencei;
- Supervisor or User privilege execution;
- virtual memory, MMU, or TLB;
- Linux boot;
- asynchronous interrupts;
- cache coherence;
- non-blocking caches;
- multiple outstanding data-memory transactions;
- speculative loads past unresolved older stores;
- memory-dependence prediction;
- dual-wide rename, dispatch, or retirement;
- FPGA-specific memories, clocking, or board interfaces;
- JTAG or RISC-V Debug Module.

## 4. Normative References

The design shall be checked against the ratified RISC-V specifications pinned by repository commit or release tag. The initial reference set is:

- RISC-V Unprivileged ISA, official release 20260120: <https://docs.riscv.org/reference/isa/v20260120/unpriv/unpriv-index.html>
- RV32I base integer ISA: <https://docs.riscv.org/reference/isa/v20260120/unpriv/rv32.html>
- M extension: <https://docs.riscv.org/reference/isa/v20260120/unpriv/m-st-ext.html>
- F extension: <https://docs.riscv.org/reference/isa/v20260120/unpriv/f-st-ext.html>
- Zicsr extension: <https://docs.riscv.org/reference/isa/v20260120/unpriv/zicsr.html>
- Machine-level ISA: <https://docs.riscv.org/reference/isa/v20260120/priv/machine.html>

If a future specification revision changes behavior, the repository shall retain the pinned version used for signoff. A specification upgrade is a controlled design change, not an implicit update.

## 5. Architectural Profile

### 5.1 ISA String

The advertised baseline ISA string is:

```text
rv32imf_zicsr
```

The design shall not advertise `F` until all mandatory F-extension operations, rounding modes, exception flags, and corner cases have passed the defined acceptance tests.

### 5.2 Architectural Registers

| Register class | Count | Width | Notes |
|---|---:|---:|---|
| Integer `x0`–`x31` | 32 | 32 | `x0` is hardwired to zero |
| Floating-point `f0`–`f31` | 32 | 32 | `f0` is an ordinary register |
| Program counter | 1 | 32 | `IALIGN=32` |
| CSRs | subset | 32 | Defined in Section 18 |

### 5.3 Instruction Alignment

Because RV32C is not implemented:

- all instructions are 32 bits;
- instruction addresses shall be 4-byte aligned;
- taken branch or jump targets that are not 4-byte aligned shall raise an instruction-address-misaligned exception on the control-transfer instruction.

### 5.4 Endianness

The baseline execution environment is little-endian.

### 5.5 Counter Access

CoreMark shall read Machine-mode counters `mcycle/mcycleh` and, when required, `minstret/minstreth`. The design does not advertise Zicntr in the baseline ISA string.

## 6. Baseline Configuration

```text
XLEN                = 32
FLEN                = 32
FETCH_WIDTH         = 1
DECODE_WIDTH        = 1
RENAME_WIDTH        = 1
DISPATCH_WIDTH      = 1
RETIRE_WIDTH        = 1
ROB_ENTRIES         = 16
ROB_SEQ_WIDTH       = 12
INT_PRF_ENTRIES     = 48
FP_PRF_ENTRIES      = 48
INT_IQ_ENTRIES      = 8
FP_IQ_ENTRIES       = 4
LQ_ENTRIES          = 4
SQ_ENTRIES          = 4
INSTR_QUEUE_ENTRIES = 8
INT_PRF_READ_PORTS  = 3
INT_PRF_WRITE_PORTS = 1
FP_PRF_READ_PORTS   = 4
FP_PRF_WRITE_PORTS  = 1
MAX_DMEM_OUTSTANDING= 1
```

Queue depths shall be parameters where practical, but the baseline configuration above is the signoff configuration.

- `INT_PRF_READ_PORTS = 3`: 2 ports for the Integer IQ (two-source ALU/branch ops) + 1 port dedicated exclusively to SQ integer store-data (`SB`/`SH`/`SW`) capture. With rename width 1, at most one store can be allocated per cycle, so the dedicated SQ port is never contested; it always services the SQ capture that cycle.
- `FP_PRF_READ_PORTS = 4`: 3 ports for the FP IQ (three-source FMA ops) + 1 port dedicated exclusively to SQ FP store-data (`FSW`) capture, with the same no-contention guarantee.

## 7. Core Classification

The baseline is a **scalar out-of-order processor**:

- one instruction can be decoded, renamed, dispatched, and retired per cycle;
- integer/memory and floating-point execution may overlap;
- at most one integer-or-memory uop and one floating-point uop may be selected in the same cycle, subject to operand-port and writeback constraints;
- sustained architectural IPC cannot exceed 1 because retirement width is 1.

The design shall not be described as a two-wide superscalar core.

## 8. Top-Level Block Diagram

```text
                        +----------------------+
                        | PC / Redirect Control|
                        +----------+-----------+
                                   |
                                   v
+--------+   +---------+   +-------+------+   +------------------+
| I-MEM  |-->| Fetch   |-->| Instruction  |-->| Decode / Uop Gen |
+--------+   +---------+   | Queue         |   +---------+--------+
                           +--------------+             |
                                                        v
                                            +-----------+-----------+
                                            | Rename / Allocate     |
                                            | RAT, Free List, ROB   |
                                            +------+----------+-----+
                                                   |          |
                                  +----------------+          +----------------+
                                  v                                            v
                         +--------+---------+                         +---------+-------+
                         | Integer Issue Q |                         | FP Issue Q      |
                         +---+----------+---+                         +----+---------+---+
                             |          |                                  |         |
                             v          v                                  v         v
                          ALU/BR      MUL/DIV                         FP Add/Mul   FP Div/Sqrt
                             |          |                                  |         |
                             +-----+----+                                  +----+----+
                                   |                                            |
                                   v                                            v
                         +---------+---------+                        +---------+---------+
                         | Integer WB Arbiter|                        | FP WB Arbiter     |
                         +---------+---------+                        +---------+---------+
                                   |                                            |
                                   v                                            v
                              Integer PRF                                    FP PRF
                                   \                                            /
                                    \                                          /
                                     +----------------+-----------------------+
                                                      |
                                                      v
                                             +--------+---------+
                                             | ROB / Retirement|
                                             +----+--------+----+
                                                  |        |
                                                  v        v
                                                CSRs      LSU / D-MEM
```

## 9. Clock, Reset, and Synthesis Boundary

### 9.1 Clock

- The core uses one rising-edge clock, `clk`.
- The baseline contains no internally generated clocks.
- Clock gating is out of scope for the functional baseline; state updates use explicit clock enables.
- Any later integrated clock-gating study shall preserve the same architectural behavior and be separately measured.

### 9.2 Reset

- The top-level reset input is synchronous active-high `rst`.
- The external ASIC wrapper is responsible for reset synchronization.
- Reset has higher priority than every redirect, flush, writeback, and retirement event.
- `RESET_PC` is a parameter; the baseline value is `32'h8000_0000`.

### 9.3 Reset State

On reset:

- frontend queues are empty;
- ROB, issue queues, LQ, and SQ are empty;
- integer RAT and retirement map point `xN` to integer physical register `pN`;
- floating-point RAT and retirement map point `fN` to FP physical register `fpN`;
- integer physical registers `p32`–`p47` are free;
- FP physical registers `fp32`–`fp47` are free;
- integer physical register `p0` is reserved for `x0` and never enters the free list;
- architectural source mappings are marked ready;
- only `p0` is required to contain a defined value, zero;
- other PRF contents are architecturally unspecified unless the simulation-only deterministic-reset option is enabled;
- `mstatus.FS` resets to Off (2'b00);
- `fetch_epoch` resets to 0;
- `mcycle`, `minstret`, and all supported CSRs reset to their defined implementation values.

### 9.4 Synthesis Boundary

PPA synthesis shall include only:

- `rv32_ooo_core`;
- its clock/reset wrapper;
- instruction- and data-memory interface pins;
- architecturally required counters and CSRs.

The following shall not be included in core PPA:

- simulation RAM;
- ELF loader;
- MMIO console model;
- Spike interface;
- commit-trace shadow storage;
- assertions or debug arrays not required by the architectural design.

## 10. Top-Level Interfaces

### 10.1 Instruction Memory Interface

The instruction interface supports one outstanding request.

```systemverilog
logic        imem_req_valid;
logic        imem_req_ready;
logic [31:0] imem_req_addr;

logic        imem_rsp_valid;
logic        imem_rsp_ready;
logic [31:0] imem_rsp_data;
logic        imem_rsp_error;
```

Contract:

1. A request is accepted when `imem_req_valid && imem_req_ready`.
2. Exactly one response shall eventually be returned for each accepted request.
3. Requests and responses are ordered.
4. A redirect does not cancel an accepted request.
5. The frontend attaches an internal fetch epoch to each request and discards a response whose epoch is stale.
6. `imem_rsp_error` becomes an instruction access fault associated with the fetched PC.

### 10.2 Data Memory Interface

The data interface supports one outstanding load or store request.

```systemverilog
typedef enum logic {DMEM_LOAD, DMEM_STORE} dmem_cmd_e;

logic        dmem_req_valid;
logic        dmem_req_ready;
dmem_cmd_e   dmem_req_cmd;
logic [31:0] dmem_req_addr;
logic [31:0] dmem_req_wdata;
logic [3:0]  dmem_req_wstrb;

logic        dmem_rsp_valid;
logic        dmem_rsp_ready;
logic [31:0] dmem_rsp_rdata;
logic        dmem_rsp_error;
```

Contract:

1. A request is accepted on `dmem_req_valid && dmem_req_ready`.
2. Every accepted load or store receives exactly one response.
3. The core keeps `dmem_rsp_ready` asserted whenever a request is outstanding.
4. A store becomes externally committed only when its successful response is accepted.
5. `dmem_rsp_error` causes a precise load or store access fault.
6. Accepted requests cannot be canceled; stale load responses are discarded using the pending ROB tag and load-queue tag.
7. The memory system shall not reorder requests because only one request may be outstanding.

## 11. Pipeline and Stage Contracts

### 11.1 Logical Stages

```text
F0  PC selection and request generation
F1  instruction request outstanding
F2  instruction response and enqueue
D0  decode and immediate generation
R0  rename, ROB allocation, LSQ allocation
D1  dispatch to issue queue / LSQ
IS  wakeup and select
EX  functional-unit execution
WB  result arbitration and writeback
RT  in-order retirement
```

These are logical stages. Variable-latency units remain outside a fixed-latency pipeline after issue.

### 11.2 Valid/Ready Rule

Every decoupled stage boundary shall obey:

- producer holds `valid` and payload stable until accepted;
- consumer asserts `ready` only when it can accept the payload;
- transfer occurs on `valid && ready`;
- flush invalidates unaccepted younger payloads;
- no stage may emit a one-cycle event that can be lost under backpressure.

### 11.3 Global Control Priority

The priority order for redirect arbitration is:

1. reset;
2. retirement redirect caused by precise trap or MRET;
3. valid branch or JALR misprediction;
4. JAL decode redirect;
5. frontend response discard or fetch retry;
6. normal pipeline flow.

When redirects at two or more priority levels occur in the same cycle, only the highest-priority redirect takes effect. Exactly one `fetch_epoch` increment shall be generated per cycle regardless of how many redirect sources are active. A lower-priority action shall not partially update state when a higher-priority action is taken.

## 12. Frontend

### 12.1 Baseline Prediction

- Conditional branches predict not taken.
- JAL redirects when decoded because its target is PC-relative and immediate.
- JALR resolves in the branch execution unit.
- No BTB, BHT, or RAS is present in the baseline.

### 12.2 Fetch Epoch

The frontend maintains `fetch_epoch`:

- increment on every frontend redirect that invalidates accepted or in-flight instruction fetches:
  1. JAL decode redirect;
  2. branch or JALR misprediction redirect;
  3. precise trap redirect;
  4. MRET redirect;
- record the current `fetch_epoch` with each accepted instruction request (`imem_req_addr`);
- enqueue a response into the instruction queue only if its recorded epoch equals the current `fetch_epoch`;
- drop stale responses without creating an architectural event.

### 12.3 Instruction Queue

The instruction queue stores:

- PC;
- instruction bits;
- fetch exception metadata;
- prediction metadata;
- fetch epoch.

The queue is flushed on any architectural redirect.

## 13. Decode

Decode shall:

- recognize every implemented instruction encoding;
- reject reserved encodings;
- generate exactly one micro-operation per baseline instruction;
- extract immediates;
- identify source and destination register domains;
- identify rounding-mode requirements;
- mark serializing operations;
- mark operations that may allocate LQ or SQ entries;
- generate an illegal-instruction exception uop instead of allowing undefined control behavior.

The baseline does not crack an instruction into multiple ROB entries. Long-latency operations remain one uop with one ROB entry.

## 14. Rename Architecture

### 14.1 Register Domains

The core uses independent rename state for integer and floating-point registers.

```text
Integer: INT_RAT, INT_RRAT, INT_FREE_LIST, INT_READY, INT_PRF
FP:      FP_RAT,  FP_RRAT,  FP_FREE_LIST,  FP_READY,  FP_PRF
```

### 14.2 Source Rename

For each register source:

1. read the appropriate speculative RAT;
2. copy the physical tag into the renamed uop;
3. read the corresponding ready-table bit;
4. never read the free list for a source.

### 14.3 Destination Rename

For a destination register other than integer `x0`:

1. read the current RAT mapping as `old_phys_dst`;
2. allocate `new_phys_dst` from the matching domain free list;
3. update the speculative RAT to `new_phys_dst`;
4. clear the new destination ready bit;
5. store architectural destination, old mapping, new mapping, and domain in the ROB.

If the required domain free list is empty (`INT_FREE_LIST` empty for integer destination, `FP_FREE_LIST` empty for FP destination), the Rename stage shall assert backpressure (`ready = 0`) and stall dispatch until a physical register is freed by instruction retirement.

For writes to integer `x0`:

- no physical register is allocated;
- no RAT entry changes;
- no PRF writeback occurs;
- the instruction may still create a ROB entry for exceptions or control effects.

### 14.4 Retirement Map

The retirement maps represent committed architectural register state.

On successful retirement of a destination-writing instruction:

1. update the matching retirement-map entry to `new_phys_dst`;
2. return `old_phys_dst` to the matching free list;
3. never free `p0`;
4. preserve the new physical register as the committed mapping.

### 14.5 Free-List Invariants

At all times:

- no physical register may appear twice in a free list;
- a free physical register may not be referenced by RAT or RRAT;
- a live ROB destination may not be free;
- `p0` may not be free;
- an FP physical register may not enter the integer free list and vice versa.

## 15. Reorder Buffer

### 15.1 Purpose

The ROB provides:

- program order;
- in-order retirement;
- precise exceptions;
- speculative destination bookkeeping;
- branch recovery metadata;
- FP flag retirement;
- LSQ association;
- stale-completion rejection.

### 15.2 ROB Tag

A ROB tag contains:

```systemverilog
typedef struct packed {
    logic [ROB_SEQ_WIDTH-1:0] seq;
    logic [$clog2(ROB_ENTRIES)-1:0] idx;
} rob_tag_t;
```

`seq` increments for each allocated instruction. The implementation shall guarantee that no accepted functional-unit or memory transaction can remain pending across a complete sequence-number wrap.

The baseline `ROB_SEQ_WIDTH=12` gives a 4096-allocation wrap interval. Because `dmem_req_valid` tracks the request channel, not the in-flight response, the ROB sequence alias guard uses an internal **pending-transaction record** that becomes valid on request acceptance (`dmem_req_valid && dmem_req_ready`) and clears on response acceptance (`dmem_rsp_valid && dmem_rsp_ready`). The normative pending-transaction type is:

```systemverilog
typedef struct packed {
    logic      valid;     // transaction accepted, awaiting response
    rob_tag_t  rob_tag;  // tag of the load or store that issued this request
    logic      lq_valid;
    lq_tag_t   lq_tag;
    logic      sq_valid;
    sq_tag_t   sq_tag;
} dmem_pending_t;
```

Rename/allocation shall stall if incrementing the sequence counter would equal `dmem_pending.rob_tag.seq` while `dmem_pending.valid` is asserted. This same `dmem_pending` record is the normative source for stale load-response validation (§22.6).

### 15.3 Age Comparison

Given two valid tags `a` and `b`, `a` is younger than `b` when the modular sequence difference is positive and less than half the sequence space. The maximum number of simultaneously live instructions shall remain below half the sequence space.

Direct unsigned comparison of circular ROB indices is forbidden.

### 15.4 ROB Entry

The normative entry fields are defined in `uop_spec.md`. At minimum each entry records:

- tag, PC, instruction;
- completion state;
- destination rename metadata;
- branch metadata;
- exception metadata;
- FP exception flags;
- LQ/SQ association;
- serializing classification.

### 15.5 Result Storage

Architectural and speculative register results reside in the PRFs, not in a synthesized 32-bit result array in the ROB. A verification-only monitor may shadow writeback values by ROB tag.

### 15.6 Allocation

A uop may allocate when all required resources are available in the same cycle:

- ROB entry;
- destination physical register, if required;
- issue-queue slot or serializing slot;
- LQ or SQ entry, if required.

Allocation is atomic. Partial allocation is forbidden.

### 15.7 Completion

A completion may set a ROB entry complete only after:

- its result has been accepted by the correct PRF write port, if a register result exists;
- any generated exception metadata has been recorded;
- FP flags have been recorded;
- branch outcome metadata has been recorded;
- the supplied ROB tag exactly matches the current valid entry.

Stores use a separate readiness rule described in Section 22.

### 15.8 Retirement

At most one instruction retires per cycle.

A normal instruction may retire when:

- it is at ROB head;
- it is valid and complete;
- it has no synchronous exception;
- it is not waiting for store acknowledgment;
- no higher-priority redirect is active.

Retirement performs all architectural updates atomically.

## 16. Late Completion and Slot-Reuse Protection

Every execution request shall carry:

- full ROB tag;
- destination physical tag and domain, when applicable;
- LQ/SQ tag, when applicable.

Before a result is accepted, the backend shall verify:

1. the addressed ROB entry is valid;
2. the full sequence and index match;
3. the operation has not been killed by recovery;
4. the destination tag and domain match the ROB metadata;
5. the entry has not already completed.

A failed validation causes the completion to be discarded without:

- PRF write;
- ready-bit update;
- wakeup broadcast;
- FP flag update;
- exception update;
- branch redirect.

This rule applies to ALU, multiplier, divider, FPU, and load responses.

## 17. Issue Queues and Wakeup/Select

### 17.1 Queue Partitioning

The baseline contains:

- integer issue queue for integer ALU, branch, multiply/divide, and address-generation uops;
- floating-point issue queue for FP arithmetic, conversion, compare, and misc uops;
- LQ/SQ for memory-order tracking.

Memory uops use the integer issue queue for address generation and retain their LQ/SQ association.

### 17.2 Wakeup

A physical destination is broadcast ready only when its PRF writeback is accepted. An FU-local completion indication before writeback grant shall not wake dependents.

### 17.3 Select

Selection policy is oldest-ready-first within each queue.

An entry is selectable when:

- valid;
- every required source is ready (see store exception below);
- target FU is ready;
- required PRF read ports are available;
- no serialization or recovery condition blocks it;
- for memory operations, LSU ordering conditions permit address or memory execution.

**Store AGU issue exception:** For a store uop in the Integer IQ, AGU select readiness depends on `src0` (address source) only. `src1` (store data) ownership transfers to the SQ at rename; the SQ tracks data readiness independently via `data_domain`/`data_phys`. The IQ entry for a store treats `src1` as `SRC_NONE` for issue-readiness purposes. The AGU does not read `src1`.

### 17.4 Same-Cycle Dispatch and Wakeup

The implementation shall define and verify whether a newly dispatched uop may observe a same-cycle writeback. The baseline requirement is:

- ready-table read includes accepted same-cycle writeback bypass;
- issue-queue insertion marks a source ready if its tag matches an accepted writeback tag;
- no source may remain falsely not-ready after the only broadcast for its producer.

## 18. CSR and Machine-Mode Subset

### 18.1 Supported CSR Instructions

- CSRRW
- CSRRS
- CSRRC
- CSRRWI
- CSRRSI
- CSRRCI

### 18.2 Supported CSRs

| CSR | Address | Baseline behavior |
|---|---:|---|
| `fflags` | `0x001` | FP accrued flags alias |
| `frm` | `0x002` | FP rounding mode alias |
| `fcsr` | `0x003` | combined `frm` and `fflags` |
| `mvendorid` | `0xF11` | read-only implementation value; zero is permitted |
| `marchid` | `0xF12` | read-only implementation value; zero is permitted |
| `mimpid` | `0xF13` | read-only implementation value |
| `mhartid` | `0xF14` | read-only zero for the single hart |
| `mstatus` | `0x300` | MIE, MPIE, MPP, FS subset |
| `misa` | `0x301` | fixed WARL value `32'h4000_1120` (XLEN=32, I, M, F extensions active) |
| `mie` | `0x304` | read-only zero because asynchronous interrupts are not implemented |
| `mtvec` | `0x305` | direct mode only |
| `mscratch` | `0x340` | read/write |
| `mepc` | `0x341` | 4-byte aligned |
| `mcause` | `0x342` | synchronous exception causes |
| `mtval` | `0x343` | exception value |
| `mip` | `0x344` | read-only zero because asynchronous interrupts are not implemented |
| `mcycle` | `0xB00` | read/write low 32 bits |
| `minstret` | `0xB02` | read/write low 32 bits |
| `mcycleh` | `0xB80` | read/write high 32 bits |
| `minstreth` | `0xB82` | read/write high 32 bits |

Unimplemented CSR addresses raise illegal instruction on attempted access. Writes to fixed or read-only CSR fields follow the implemented WARL/read-only behavior and shall not silently create unsupported architectural state.

### 18.3 CSR Serialization

All CSR instructions are serializing in the baseline:

1. once decoded, younger rename/dispatch is blocked;
2. the CSR uop waits until it reaches ROB head;
3. the source integer operand must be ready;
4. CSR read-modify-write executes at head;
5. the old CSR value is written to integer PRF if `rd != x0` (requesting the Integer writeback port without contention, as all older instructions have retired and no younger instructions exist);
6. the instruction retires after writeback acceptance;
7. frontend/backend serialization is released.

This avoids speculative CSR state and resolves dependencies on `frm`, `fflags`, counters, and trap-control CSRs.

### 18.4 Floating-Point State Enable

- `mstatus.FS=Off` (2'b00) makes all FP instructions and FP CSR accesses (`fflags`, `frm`, `fcsr`) illegal, causing Decode/Rename to generate a `UOP_EXCEPTION` with cause `EXC_ILLEGAL_INSTRUCTION`.
- An instruction that modifies FP architectural register state or `fcsr` causes FS to become Dirty at retirement.
- The bare-metal startup code shall set FS before executing FP instructions.

### 18.5 MRET

MRET is supported as a serializing retirement redirect:

- execute only at ROB head;
- restore `mstatus.MIE` from `MPIE`;
- set `MPIE` to 1;
- set `MPP` to the implemented Machine-mode value;
- redirect PC to `mepc`;
- flush all speculative younger state.

## 19. Serializing Instructions

The baseline treats the following as serializing:

- all CSR instructions;
- FENCE;
- ECALL;
- EBREAK;
- MRET.

Serialization rule:

- once the instruction is accepted into rename, no younger instruction may rename until it retires or traps;
- the serializing instruction may execute only at ROB head;
- outstanding older memory transactions must finish before FENCE retires;
- no younger uop may issue around the instruction.

FENCE is architecturally implemented as a drain operation for the strongly ordered, one-outstanding memory interface. FENCE.I is not implemented.

## 20. Branch Execution and Recovery

### 20.1 Resolution

The branch unit produces:

- actual taken/not-taken;
- actual target;
- misprediction indication;
- instruction-address-misaligned exception when applicable.

The branch unit may resolve only a uop whose ROB tag remains valid.

### 20.2 Correct Prediction

For the static baseline:

- an untaken conditional branch completes normally;
- a taken conditional branch mispredicts;
- JAL is redirected at decode and later verified;
- JALR normally redirects at execution.

### 20.3 Misprediction Recovery

On a valid misprediction:

1. record the branch tag and correct target;
2. increment fetch epoch and flush frontend queues;
3. immediately invalidate younger IQ and LSQ entries by ROB age;
4. reject all younger completions;
5. enter `BRANCH_ROLLBACK`;
6. walk the ROB from tail toward the branch, one younger entry per cycle;
7. restore each destination RAT mapping to `old_phys_dst`;
8. return each `new_phys_dst` to the appropriate free list only if the uop explicitly allocated a valid physical register (`dst.valid == 1`);
9. clear each rolled-back ROB entry;
10. set ROB tail to the entry after the branch;
11. redirect fetch and resume only after rollback completes.

Retirement is frozen during rollback. Older valid execution may finish; its completion remains acceptable.

### 20.4 Recovery State

```text
CORE_RUN
BRANCH_ROLLBACK
TRAP_RECOVERY
MRET_RECOVERY
RESET_INITIALIZE
```

Only one recovery state may be active at a time. If an older instruction at the ROB head triggers a precise trap while the core is in `BRANCH_ROLLBACK`, the core shall immediately abort the multi-cycle branch rollback, transition directly to `TRAP_RECOVERY`, clear all ROB entries, and restore RATs from RRATs.

## 21. Integer Execution

### 21.1 Integer ALU

The ALU supports:

- add/subtract;
- logical operations;
- shifts;
- signed and unsigned comparisons;
- branch comparison;
- PC-relative address calculation.

Nominal latency is one cycle.

### 21.2 Multiply

The multiplier supports:

- MUL;
- MULH;
- MULHSU;
- MULHU.

The implementation may be parameterized as iterative or pipelined. The baseline signoff configuration and latency shall be recorded in generated reports.

### 21.3 Divide

The divider supports:

- DIV;
- DIVU;
- REM;
- REMU;
- architectural divide-by-zero results;
- signed overflow special case.

The baseline divider is iterative and non-pipelined. It shall hold its completion until writeback grant.

## 22. Load/Store Architecture

### 22.1 Supported Operations

Integer:

- LB, LH, LW, LBU, LHU;
- SB, SH, SW.

Floating-point:

- FLW;
- FSW.

### 22.2 Allocation

- A load atomically allocates ROB, destination physical register, integer IQ entry for address generation, and LQ entry.
- A store atomically allocates ROB, integer IQ entry for address generation, and SQ entry.
- FSW has an integer address source (`src0_domain = REG_INT`) and an FP data source (`src1_domain = REG_FP`).
- Store data readiness is tracked independently from address readiness: `FSW` issues to LSU_AGU for address generation out of the Integer IQ; the SQ entry stores `data_domain`, `data_phys`, `data_valid`, and `data`. The SQ snoops both Integer and FP writeback buses for `data_phys` matches when `data_valid == 0`, and reads the FP PRF via a dedicated/shared read port if `src1` is ready at allocation.

### 22.3 Address Generation

Effective address is computed as integer base plus sign-extended immediate.

Misaligned accesses raise precise exceptions:

- halfword address bit 0 must be zero;
- word address bits `[1:0]` must be zero;
- misaligned accesses are not split into multiple requests.

### 22.4 Conservative Load Ordering

A load may issue to memory only when:

1. every older store has a known address;
2. no older matching store has unavailable data;
3. no data-memory request is already outstanding;
4. the load remains valid and not killed.

If one or more older stores match, forwarding selects the youngest matching older store. Age comparisons between loads and stores in the LSQ shall use their assigned `rob_tag` sequence arithmetic (`rob_is_younger()`), not raw queue indices.

### 22.5 Store-to-Load Forwarding

Forwarding shall support byte masks. A load may be fully forwarded only when the selected store provides every byte required by the load. Partial merge between store data and memory data is not supported in the baseline; a load matching an older store with partial byte overlap stalls in the LQ and shall not issue to memory until all older matching stores have retired (committed to memory).

### 22.6 Load Completion

A load response is accepted only if:

- pending ROB tag still matches;
- pending LQ tag still matches;
- operation was not killed;
- destination tag matches ROB metadata.

The LSU performs byte extraction and sign/zero extension before writeback. When a load response is accepted for `mem_ctrl.is_fp == 1` (`FLW`), the LSU routes the completion packet to the FP writeback arbiter (`result_domain = REG_FP`). For integer loads (`mem_ctrl.is_fp == 0`), it routes to the Integer writeback arbiter (`result_domain = REG_INT`).

### 22.7 Store Retirement

A store becomes eligible to start its memory request when:

- it is ROB head;
- its address and data are ready;
- it has no exception;
- no data request is outstanding.

Retirement sequence:

1. issue store request;
2. wait for store response;
3. on success, retire the store and increment `minstret`;
4. on error, take precise store access fault without retiring the store.

A speculative store shall never update external memory.

### 22.8 Memory-Port Priority

When a ready store is at ROB head, its request has priority over speculative loads. This prevents a committed store from being indefinitely blocked.

## 23. Floating-Point Architecture

### 23.1 Register Domain

- 32 architectural 32-bit FP registers;
- independent FP RAT, RRAT, free list, ready table, and PRF;
- four FP PRF read ports total: three for FP IQ/FMA (three-source ops), one dedicated to SQ FSW store-data capture;
- one FP PRF write port.

### 23.2 Required Operations

Before RV32F compliance is claimed, the design shall implement:

- FLW, FSW;
- FMADD.S, FMSUB.S, FNMSUB.S, FNMADD.S;
- FADD.S, FSUB.S, FMUL.S, FDIV.S, FSQRT.S;
- FSGNJ.S, FSGNJN.S, FSGNJX.S;
- FMIN.S, FMAX.S;
- FCVT.W.S, FCVT.WU.S, FCVT.S.W, FCVT.S.WU;
- FMV.X.W, FMV.W.X;
- FEQ.S, FLT.S, FLE.S;
- FCLASS.S;
- all required rounding modes and exception flags.

### 23.3 Rounding Modes

The implementation supports:

- RNE;
- RTZ;
- RDN;
- RUP;
- RMM;
- dynamic mode through `frm`.

Reserved rounding encodings raise illegal instruction.

Dynamic mode is resolved before dispatch and stored as an explicit resolved rounding mode in the uop (`fp_ctrl.rm`). The CSR module exposes `frm[2:0]` combinationally to the Rename stage. Because CSR instructions are serializing, `frm` is guaranteed stable during rename. If `rm == 3'b111`, rename resolves `fp_ctrl.rm = frm`. If `frm` contains an illegal value (3'b101, 3'b110, 3'b111) when dynamic mode is requested, rename converts the uop to `UOP_EXCEPTION` with `EXC_ILLEGAL_INSTRUCTION`.

### 23.4 FP Exception Flags

Each FP operation may produce:

```text
NV  invalid operation
DZ  divide by zero
OF  overflow
UF  underflow
NX  inexact
```

Flags are speculative until retirement:

- completion stores flags in the ROB entry;
- wrong-path flags are discarded;
- successful retirement ORs flags into architectural `fflags`;
- an FP operation shall not update `fflags` directly from the FU.

### 23.5 FMA Requirement

Fused operations shall retain full intermediate product precision and perform one final rounding. A rounded multiply result followed by a separate add is not compliant.

### 23.6 Special Values

Unit and integration tests shall cover:

- positive and negative zero;
- normal and subnormal values;
- infinity;
- quiet and signaling NaN;
- canonical NaN behavior required by the pinned ISA version;
- overflow, underflow, and exact/inexact boundaries;
- cancellation and tie-breaking cases.

## 24. Writeback Architecture

### 24.1 Domains

The baseline has:

- one integer writeback port;
- one FP writeback port.

Cross-domain operations use the destination domain writeback port.

Examples:

- FCVT.W.S writes integer PRF;
- FCVT.S.W writes FP PRF;
- FMV.X.W writes integer PRF;
- FMV.W.X writes FP PRF;
- FLW writes FP PRF.

### 24.2 Holding Registers

Every variable-latency or independently completing producer shall hold:

- valid;
- ROB tag;
- destination tag/domain;
- result;
- exception metadata;
- FP flags;
- auxiliary branch or memory metadata;

until granted by the appropriate writeback arbiter.

### 24.3 Arbitration

Arbitration shall be deterministic and starvation-free. A round-robin policy is preferred for producers of the same domain.

A result is complete only after:

- PRF write accepted;
- ready bit set;
- wakeup broadcast generated;
- ROB completion accepted.

These actions shall be atomic for a valid result.

## 25. Precise Exceptions and Traps

### 25.1 Supported Synchronous Exceptions

- instruction address misaligned;
- instruction access fault;
- illegal instruction;
- breakpoint;
- load address misaligned;
- load access fault;
- store/AMO address misaligned;
- store/AMO access fault;
- environment call from M-mode.

AMO instructions are not implemented; the standard store/AMO cause codes are used for stores.

### 25.2 Exception Recording

An exception discovered before retirement is recorded in the associated ROB entry with cause and `tval`.

The instruction may become ROB-complete without producing a register result. It cannot retire normally.

### 25.3 Trap Entry

When an excepting instruction reaches ROB head:

1. the instruction does not retire;
2. all older instructions have already retired;
3. younger execution is killed;
4. all younger queues are flushed;
5. speculative RATs are restored from retirement maps;
6. speculative new physical registers are reclaimed;
7. `mepc` receives faulting PC;
8. `mcause` receives cause;
9. `mtval` receives exception-specific value;
10. `mstatus` trap-entry fields update: `MPIE_next = MIE_current`, `MIE_next = 0`, `MPP_next = 2'b11` (Machine mode);
11. PC redirects to direct-mode `mtvec`;
12. `minstret` does not increment for the faulting instruction.

On trap recovery, the core shall restore Integer and FP RATs from RRATs in a single cycle transition. The free lists shall be rebuilt using **single-cycle combinational membership-mask rebuild**: for each physical register `p` (other than integer `p0`), `free_mask[p] = !rrat_contains(p)`, computed in parallel across all registers in the same cycle as the RRAT restore. If a CSR write to `mstatus` occurs at ROB head in the same cycle as a trap, the trap entry state updates take priority.

### 25.4 Exception Priority Within an Instruction

When multiple conditions are detected for one instruction, the implementation shall follow the pinned RISC-V exception-priority rules. Decode-generated illegal instruction and fetch-generated access/alignment exceptions shall be carried explicitly so that priority is not inferred from incidental pipeline timing.

## 26. Retirement and Architectural Side Effects

Retirement is the only point at which the following become architectural:

- integer destination mapping;
- FP destination mapping;
- old physical-register reclamation;
- FP accrued flags;
- CSR writes;
- store completion;
- `minstret` increment;
- trap entry;
- MRET redirect.

`mcycle` increments every non-reset cycle independently of retirement.

No wrong-path instruction may:

- change RRAT;
- free a committed physical register;
- update CSR state;
- update `fflags`;
- update external memory;
- increment `minstret`.

## 27. Performance Counters

Mandatory internal counters for research builds:

- cycles;
- retired instructions;
- conditional branches;
- branch mispredictions;
- rollback cycles;
- ROB full cycles;
- integer IQ full cycles;
- FP IQ full cycles;
- integer free-list empty cycles;
- FP free-list empty cycles;
- load blocked by unresolved store cycles;
- store-forwarded loads;
- integer writeback conflicts;
- FP writeback conflicts;
- FU busy/utilization cycles.

Only architecturally defined counters need be exposed as CSRs in the baseline. Research counters may be synthesis-optional MMIO/debug outputs but must be measured consistently across PPA experiments.

## 28. ASIC Implementation Rules

### 28.1 RTL Rules

Synthesizable RTL shall:

- use `always_ff` and `always_comb` consistently;
- assign every combinational output on every path;
- infer no unintended latches;
- use parameters for widths and queue depths;
- avoid simulation-only dynamic arrays, classes, queues, and delays;
- avoid `X` as functional state;
- isolate assertions with synthesis guards where necessary;
- avoid asynchronous combinational loops between ready/valid interfaces.

### 28.2 Storage Implementation

Baseline PRFs, ROB, IQ, LQ, and SQ may be flip-flop and mux based. Reports shall explicitly state that standard-cell storage does not represent a production SRAM-compiler implementation.

### 28.3 Critical Paths to Monitor

Expected candidates:

- issue-queue tag compare and oldest-ready select;
- PRF read mux to ALU/FPU input;
- branch compare to redirect;
- free-list allocation and rename update;
- ROB age comparison and flush mask;
- FP normalization and rounding;
- store-to-load address comparison.

Each synthesis report shall classify the worst path by microarchitectural function.

## 29. Verification Requirements

### 29.1 Required Verification Layers

1. module-level directed tests;
2. module assertions;
3. subsystem integration tests;
4. directed microarchitecture hazards;
5. RISC-V architectural tests;
6. commit-level differential testing;
7. long randomized instruction streams;
8. bare-metal application tests;
9. CoreMark correctness and performance runs;
10. formal invariant checking for bounded configurations.

### 29.2 Commit Trace

The simulation environment shall emit one trace event record for either:
1. a successfully retired instruction (`retire_valid = 1`); or
2. a precise trap taken for the ROB-head instruction (`trap_valid = 1`).

Each record contains:
- monotonically increasing `event_order` (increments on both retired instructions and taken traps);
- `retire_valid` and `trap_valid` flags;
- PC;
- instruction;
- integer destination and value, if any;
- FP destination and value, if any;
- memory access address, mask, and data, if any (testbench commit monitor reconstructs load data by shadowing PRF writebacks indexed by `rob_tag`);
- trap, cause, and `tval`, if taking a trap;
- architectural `fflags` after retirement or trap update.

`minstret` increments only on `retire_valid == 1`. FP data comparisons are bit-exact.

### 29.3 Mandatory Assertions

At minimum:

- `x0` always reads zero;
- ROB occupancy never overflows or underflows;
- an invalid or incomplete ROB head never retires;
- a physical register is never allocated twice;
- free-list and live mappings are disjoint;
- stale completions never write PRF;
- wrong-path uops never retire;
- stores never become visible before retirement;
- unresolved older stores block a load memory request;
- forwarding selects the youngest matching older store;
- FP flags change only at retirement or CSR write;
- no serializing instruction has a younger renamed instruction.

## 30. Architecture Signoff Gates

### 30.1 Gate A — Integer Architectural Baseline

Required:

- RV32I directed tests;
- branch and exception tests;
- architectural tests for implemented I instructions;
- Spike differential regression;
- no known rename, ROB, or store-order failures.

### 30.2 Gate B — RV32IM

Required:

- all M operations and corner cases;
- M architectural tests;
- random multiply/divide differential tests;
- long-latency flush and slot-reuse tests.

### 30.3 Gate C — RV32IMF Candidate

Required:

- complete F instruction set listed in Section 23;
- every rounding mode;
- accrued flags;
- FP architectural tests;
- bit-exact random FP differential tests;
- wrong-path FP flag tests;
- FMA single-rounding tests.

### 30.4 Gate D — Application Acceptance

Required:

- bare-metal C smoke suite;
- CoreMark validation CRC pass;
- CoreMark run metadata captured;
- no-retirement watchdog clean;
- final architectural state consistent with reference execution where applicable.

### 30.5 Gate E — ASIC Baseline

Required:

- lint clean under agreed waiver list;
- synthesis complete;
- no unintended latches;
- pre- and post-route STA reports;
- DRC/LVS status recorded;
- tool, PDK, constraints, and RTL commit pinned;
- PPA result reproducible from clean checkout.

## Appendix A. CoreMark Architectural Acceptance

CoreMark is a primary application-level acceptance workload for the integer core and bare-metal environment. It does not validate the FPU.

Required configuration metadata:

- CoreMark repository commit;
- compiler version;
- `-march=rv32im_zicsr`;
- `-mabi=ilp32`;
- optimization flags;
- iteration count;
- clock-frequency declaration;
- memory latency configuration;
- validation CRC output;
- measured `mcycle` and `minstret` deltas.

Required results:

- validation seeds pass;
- no unexpected trap;
- program exits through simulation MMIO;
- cycles per iteration;
- instructions per iteration;
- iterations per cycle;
- CoreMark/MHz-equivalent value, clearly labeled as internal research unless every official run rule is satisfied.

## Appendix B. RISC-V Architectural-Test Acceptance

The project shall use the current official `riscv-arch-test` ACT4 flow pinned by commit.

Execution order:

1. RV32I;
2. M;
3. Zicsr and implemented machine-mode behavior;
4. F load/store and miscellaneous operations;
5. F arithmetic, conversion, fused operations, divide, and square root;
6. full advertised ISA regression.

For each failure the harness shall retain:

- ELF;
- disassembly;
- signature difference;
- last commit-trace window;
- ROB, RAT, free-list, IQ, LSQ, and pending-completion snapshots;
- tool versions and test commit;
- exact reproduction command.

Passing architectural tests is necessary but not sufficient for OoO correctness; random differential and formal verification remain mandatory.

## Appendix C. Baseline Microarchitectural Decisions (Frozen)

The following baseline choices are frozen for the G0 signoff baseline:

1. **Multiplier**: Pipelined baseline multiplier with fixed 3-cycle latency.
2. **FP Stage Counts**: FP Add (4 cycles), FP Mul (4 cycles), FP FMA (4 cycles), FP Div/Sqrt (iterative non-pipelined).
3. **Branch Predictor**: Static predict-not-taken baseline.
4. **Int PRF Read Ports**: 3 Integer PRF read ports: 2 for two-source IQ issue, 1 dedicated exclusively for SQ integer store-data capture. With rename width 1, the SQ port is never contested.
5. **FP PRF Read Ports**: 4 FP PRF read ports: 3 for three-source FP IQ/FMA, 1 dedicated exclusively for SQ FP store-data (`FSW`) capture. Same no-contention guarantee.
6. **Branch Recovery**: Multi-cycle entry-by-entry ROB reverse walk (`BRANCH_ROLLBACK`).
7. **Trap Recovery**: Single-cycle RRAT-to-RAT map restore + **single-cycle combinational membership-mask free-list rebuild** (not sequential scan). `free_mask[p] = (p != p0) && !rrat_contains(p)` computed in parallel across all physical registers in a single cycle.
8. **Power Estimation Flow**: Activity-annotated post-route power estimation using switching activity dumps.

## Appendix D. Change-Control Rule

Any change affecting one of the following requires an architecture review and document version increment:

- advertised ISA;
- micro-op semantics;
- retirement side effects;
- exception priority;
- memory ordering;
- register-renaming ownership;
- ROB tag width or stale-completion rule;
- serializing instruction policy;
- top-level memory protocol;
- PPA synthesis boundary.
