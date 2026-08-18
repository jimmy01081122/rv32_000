# Interface and Observability Audit Findings

## Audit Scope Review

### 1. Differential Testing Interface
- **Order, PC, Instruction**: Available in the ROB entry.
- **Integer & FP Dst Register**: Available in `rob_entry_t` via `renamed_dst_t`.
- **Integer & FP Dst Value**: The specs (PLAN.md §8.2 and architecture_spec §15.5) correctly state that PRF holds the values and the ROB avoids storing them. To generate the commit trace, the monitor shadows the PRF writeback values by `rob_tag`. This approach is architecturally sound and completely specified.
- **Memory Address, Mask, Data**: Store address, data, and byte mask are captured in the `sq_entry_t`. However, there is an ambiguity for load data (see Finding 1).
- **Trap, Cause, Tval**: Available in the `exception_t` struct in the ROB.
- **FFlags**: Available in the ROB entry and architecturally updated.

### 2. ACT4 Architectural Test Support
- ELF loading, signature dumping, and pass/fail detection are defined in PLAN.md §Appendix B.
- Timeout mechanisms (max cycles, max instret, no-retire watchdog) are adequately defined.
- Failure artifact collection comprehensively covers ROB, RAT, IQ, LSQ, and more.
- **Gap**: The ACT4 signature region memory map is not explicitly allocated (see Finding 3).

### 3. CoreMark Support
- `mcycle`/`mcycleh` and `minstret`/`minstreth` are properly mapped in CSR space (architecture_spec §18.2).
- The 64-bit high-low-high read sequence is supported.
- Compiler flags and environment requirements are well-defined.
- Memory map correctly places `RESET_PC` at `0x8000_0000` (Program/Data RAM).

### 4. Performance Counters
- Mandatory internal counters (cycles, retired insns, branches, mispredictions, etc.) are comprehensively listed.
- **Gap**: The memory map for exposing synthesis-optional MMIO counters is missing (see Finding 5).

### 5. Assertion Coverage
- Core invariants for renaming, ROB, memory ordering, and exceptions are explicitly covered in `architecture_spec §29.3` and `uop_spec.md §29`.

### 6. Reset and Initialization
- Reset states for RAT, PRF, ROB, free lists, CSRs, and `mstatus` are defined.
- **Gap**: `fetch_epoch` reset is omitted (see Finding 4).

---

## Detailed Findings

### [INTF-01] Commit Trace Data Availability for Loads
- **Severity**: MEDIUM
- **Category**: CommitTrace
- **Location**: architecture_spec §29.2, uop_spec.md §21
- **Finding**: The commit trace specifies inclusion of "memory access address, mask, and data, if any". For stores, `sq_entry_t` contains the address, mask, and data. For loads, `lq_entry_t` contains the address and size, but not the read data or mask. While load data goes to the PRF writeback (which the monitor shadows), it is ambiguous if the monitor must reconstruct a memory-read payload for the trace or if the LSU is expected to broadcast load data specifically for the trace.
- **Proposed Correction**: Clarify in architecture_spec §29.2 whether "memory data" in the trace applies only to stores, or if it also applies to loads. If it applies to loads, specify that the testbench monitor shall infer the loaded memory data from the shadowed PRF writeback value.

### [INTF-02] ACT4 Signature Region in Memory Map
- **Severity**: LOW
- **Category**: ACT4 / MemMap
- **Location**: PLAN.md §17.1
- **Finding**: The memory map defines Program/Data RAM at `0x8000_0000` to `0x800F_FFFF` and MMIO at `0x1000_0000`, but does not explicitly identify a signature region address range used by ACT4.
- **Proposed Correction**: Explicitly state in PLAN.md §17.1 that the ACT4 signature region is dynamically allocated within the Data RAM space by the linker script, or define a dedicated debug memory region if ACT4 requires fixed boundaries.

### [INTF-03] Fetch Epoch Reset State Omitted
- **Severity**: MEDIUM
- **Category**: Reset
- **Location**: architecture_spec §9.3
- **Finding**: The document exhaustively lists the reset states for queues, pointers, free lists, and PRFs. However, it fails to specify the reset state of the `fetch_epoch`. If the epoch does not initialize to a known value, the first instruction fetch could be spuriously rejected.
- **Proposed Correction**: Add "fetch epoch resets to 0" to the Reset State requirements in architecture_spec §9.3.

### [INTF-04] Performance Counter MMIO Range Undefined
- **Severity**: LOW
- **Category**: PerfCounter / MemMap
- **Location**: architecture_spec §27, PLAN.md §17.1
- **Finding**: architecture_spec §27 states that research performance counters may be "synthesis-optional MMIO/debug outputs". However, the baseline memory map in PLAN.md §17.1 defines no MMIO range for these counters.
- **Proposed Correction**: Define an explicit `SIM_PERF_COUNTERS` MMIO address block in PLAN.md §17.1, or explicitly dictate that they are accessed only via backdoor simulator hierarchical paths rather than MMIO loads.

### [INTF-05] Exception Valid Flag Enforcement
- **Severity**: LOW
- **Category**: Assertion
- **Location**: uop_spec.md §20, §29.4
- **Finding**: While `exception_t` contains a `valid` bit, the completion assertions do not explicitly mandate that a normal (non-excepting) completion must explicitly drive `exception.valid == 0`. This could lead to X-propagation or garbage exception metadata if left unassigned by functional units.
- **Proposed Correction**: Add a completion assertion in uop_spec.md §29.4: "exception.valid is 0 for all normal, successful non-excepting completions".
