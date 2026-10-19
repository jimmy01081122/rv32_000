# RV32 OoO architecture: implementation and requirements

Version 0.5 — 2026-10-19. Status: AP5B baseline frozen; isolated LSU A experiment under qualification.

This document distinguishes observed RTL structure from required architectural
behavior. Describing an implementation does not certify its correctness.
The [project plan](PLAN.md) governs scope and change decisions;
[current status](docs/STATUS.md) records evidence and gaps.
The [G0 contract](docs/archive/g0/architecture_spec.md) retains earlier design
intent and section numbers used in legacy RTL comments.

## Architectural scope

- Target: RV32IMF + Zicsr, little endian, bare metal, machine-mode subset.
- One-wide fetch, decode, rename, dispatch and retirement; scalar out-of-order issue.
- Integer and FP execution may overlap; retirement IPC is bounded by one.
- 32 integer and 32 FP architectural registers; integer x0 reads zero.
- Synchronous active-high reset; reset PC `0x80000000`.
- No implemented compressed/atomic/vector ISA, MMU, cache hierarchy, external
  interrupt interface or debug module is claimed by this inventory.
- `FENCE.I` decode and retirement redirect logic exist and the ACT4 configuration
  includes Zifencei. Full profile reconciliation remains open; its presence does
  not establish complete machine-mode or advertised-extension conformance.

The reference ISA revision retained from G0 is
[RISC-V 20260120](https://docs.riscv.org/reference/isa/v20260120/unpriv/unpriv-index.html).
Instruction semantics, exception priority, FP rounding and flags must be checked
against the pinned specifications. Existing RTL behavior that disagrees with
them is a qualification issue, not an implicit specification change.

## Implemented structures

| Structure | Observed configuration | Source |
| --- | --- | --- |
| ROB | 16 slots; 12-bit sequence + 4-bit index | [parameters](rtl/pkg/rv32_ooo_params.sv), [ROB](rtl/rob/rv32_ooo_rob.sv) |
| Integer / FP PRF | 48 × 32 bits each | [integer PRF](rtl/rename/rv32_ooo_int_prf.sv), [FP PRF](rtl/rename/rv32_ooo_fp_prf.sv) |
| Actual PRF port interfaces | Integer 4R/3W; FP 4R/2W | PRF modules and [core wiring](rtl/core/rv32_ooo_core.sv) |
| Integer / FP IQ | 8 / 4 slots | [integer IQ](rtl/issue/rv32_ooo_int_iq.sv), [FP IQ](rtl/issue/rv32_ooo_fp_iq.sv) |
| Instruction FIFO / request tracking | 8 / 4 entries | [frontend](rtl/frontend/rv32_ooo_frontend.sv) |
| Predictor | 64-entry direct-mapped BTB, 64-entry two-bit BHT; no RAS storage | frontend |
| Store queue | 16 `sq_slot_t` slots | [LSU](rtl/lsu/rv32_ooo_lsu.sv) |
| Load tracking | One in-flight record and one AP5B response buffer | LSU |
| External data transactions | `MAX_DMEM_OUTSTANDING=1` | parameters and LSU |

Important parameter/implementation differences:

- `LQ_ENTRIES=16` and `lq_entry_t` exist, but no 16-entry load queue is instantiated.
  Rename's LQ/SQ tag fields are zeroed; the LSU tracks stores using its local slots
  and ROB identities. These fields are not evidence of working generation-tagged queues.
- `INT_PRF_READ_PORTS=3`, `INT_PRF_WRITE_PORTS=1` and
  `FP_PRF_WRITE_PORTS=1` are legacy constants; the modules expose the ports above.
  Changing those constants alone will not reconfigure the PRFs.
- `rob_entry_t` contains `result_data`, used for commit trace output. The old
  statement that the ROB contains no result data does not describe this RTL.

## Execution and recovery

Integer issue passes through the core's elastic EX0 register. The integer execution
cluster dispatches ALU/branch/CSR, pipelined multiply, iterative divide and LSU
address generation. The FP cluster has separate simple, arithmetic and iterative
divide/square-root units, with completion arbitration in the core.

Branch outcomes are recorded in the ROB. The current recovery request is generated
when a mispredicted branch reaches retirement, and the ROB clears speculative
entries. It does not implement the G0 proposal of immediate execution-stage
redirect followed by a reverse ROB walk. Core redirect priority is trap, then
MRET/FENCE.I, then retired branch misprediction, beneath reset.

Register-renaming ownership, full ROB tag matching, stale-completion rejection,
precise retirement and wrong-path isolation remain required behaviors. Each
must have directed/random/assertion evidence before architectural qualification.

## Memory interface and ordering

Actual ports are defined by [rv32_ooo_core](rtl/core/rv32_ooo_core.sv):

| Channel | Payload |
| --- | --- |
| Instruction request | `imem_req_addr` |
| Instruction response | `imem_rsp_rdata`, `imem_rsp_error` |
| Data request | `dmem_req_addr`, `dmem_req_wdata`, `dmem_req_byte_en`, `dmem_req_wen` |
| Data response | `dmem_rsp_rdata`, `dmem_rsp_error` |

Each channel has valid/ready handshaking. The environment contract is one ordered
response per accepted request; redirects do not cancel accepted bus transactions.
The frontend tracks up to four instruction requests. The data side admits one
external transaction. The frozen AP5B baseline blocks new data requests while a
response buffer is valid. Experiment A permits a new request on the same edge
that a successful registered response is consumed, only with no external
in-flight transaction and no flush. Faulting or unconsumed responses continue
to block requests. This does not bypass the external response register or
accept a second external outstanding transaction. `dmem_pending.valid` covers
the old buffered response before the handoff edge and the new in-flight request
after it, with the corresponding tag. SQ marking remains the baseline protocol.

The LSU checks older stores, forwards from a fully covering older store, and
stalls on unresolved or partial-overlap dependencies. Stores require ROB-head
authorization. External loads advance upstream only on a data request handshake;
internal forwarding/misalignment uses its own buffered acceptance path. Successful
stores acknowledge retirement on the response handshake. A store error suppresses
that acknowledgement and transfers tag/address ownership to the AP5B response
buffer for a cause-7 exception completion before ROB trap entry; it writes no PRF
result. Load errors retain cause 5. `mtval` preserves the original byte address.

The default simulation model updates memory on accepted stores. Optional ready
throttling and one-shot address-selected load/store faults support the
[interface checks](docs/LSU_INTERFACE_FIX.md); injected failed writes do not update
RAM. The historical write-before-error harness is replayed separately. The CPU
does not undo an externally completed write. Data latency parameters describe the
C++ model, not a measured SRAM or interconnect.

## CSR and floating-point qualification

The [CSR module](rtl/csr/rv32_ooo_csr.sv) currently decodes:

- `fflags`, `frm`, `fcsr`;
- `mstatus`, `misa`, `mtvec`, `mscratch`, `mepc`, `mcause`, `mtval`;
- `mcycle/mcycleh`, `minstret/minstreth` and the corresponding cycle/instret aliases.

The broader G0 CSR table is not an implemented-support list. CSR access legality,
WARL/read-only behavior, FP enable/dirty-state handling and counter aliases require
profile reconciliation and verification. Target requirements include all RV32F
operations, rounding modes, exceptional values, accrued flags and single-rounding
FMA behavior. Existing FP smoke programs and the non-F ACT4 set do not establish
those requirements.

## Verification and measurement requirements

- Architectural tests, commit-trace comparison, hazard tests, assertions and
  focused formal properties have complementary roles; workload scores do not
  replace functional verification.
- No wrong-path instruction may retire or commit memory/CSR/FP side effects.
- Results must preserve integer x0, register-domain ownership, ROB identity and
  memory ordering, including redirects and delayed responses.
- General embedded and FP32 performance are separate, equally important goals;
  candidate workloads and targets are in [WORKLOADS.md](docs/WORKLOADS.md).
- The source SHA, tool versions, memory model, compiler and measurement interval
  accompany every performance result. Generic synthesis cell counts are not
  technology-mapped area or physical timing results.
- Physical research results must state library/corner, constraints, implementation
  stage, parasitic model, timing groups, storage and debug boundaries. See
  [the ASAP7 status](physical/asap7/README.md).

ISA/profile, retirement, exception, memory-ordering, rename ownership, tag/flush,
protocol and PPA-boundary changes require a reviewed proposal under the project
plan. This documentation update does not modify any of those RTL behaviors.
