# Behavioral Completeness Audit Findings

### [FINDING-1] Free-List Exhaustion Behavior Not Specified
- **Severity**: HIGH
- **Category**: Rename
- **Location**: `architecture_spec.md` §14.3, `uop_spec.md` §16.1
- **Finding**: The documents do not specify the pipeline behavior when the free list is empty. While it implies allocation cannot proceed, it does not explicitly define that the frontend/rename stage must stall until a physical register becomes available.
- **Scenario**: A burst of destination-writing instructions exhausts the physical register file before older instructions retire. The free list becomes empty. The rename stage attempts to allocate `new_phys_dst`.
- **Proposed Correction**: Add to `architecture_spec.md` §14.3: "If the required domain free list is empty, the Rename stage shall stall and block younger instruction decode/fetch until a physical register is freed by retirement."

### [FINDING-2] Ambiguity in Same-Cycle Retirement-to-Allocation Bypass
- **Severity**: MEDIUM
- **Category**: Rename
- **Location**: `uop_spec.md` §28.2
- **Finding**: The spec states a freed register "may be allocated in the same cycle if the free-list implementation defines deterministic bypass... The choice shall be consistent and asserted." This explicitly leaves an architectural behavior as an open choice, violating the "unambiguous" and "implementable without guessing" requirements.
- **Scenario**: Cycle N: Instruction A retires, freeing `p5`. Instruction B is at Rename, needing an integer register, and the free list was previously empty. Does B rename in Cycle N or Cycle N+1?
- **Proposed Correction**: Remove the optionality. Force a specific baseline rule, e.g., "The baseline shall implement same-cycle retirement-to-allocation bypass to prevent false stalls when the free list is empty."

### [FINDING-3] Free-List Corruption on Rollback of Non-Allocating Uops
- **Severity**: CRITICAL
- **Category**: Flush
- **Location**: `architecture_spec.md` §20.3
- **Finding**: Step 8 of branch misprediction recovery unconditionally dictates "return each `new_phys_dst` to the appropriate free list". However, uops like branches, stores, and writes to `x0` do not allocate a physical register. If their dummy `new_phys_dst` is returned to the free list, it will corrupt the free list with duplicates or `p0`.
- **Scenario**: A mispredicted branch is followed by a `SW` instruction. The `SW` is rolled back. It has no valid `new_phys_dst`. If the rollback unconditionally pushes its `new_phys_dst` field to the free list, an invalid or duplicate physical register enters the free list.
- **Proposed Correction**: Update Step 8 to read: "return each `new_phys_dst` to the appropriate free list only if the uop explicitly allocated a valid physical register during rename."

### [FINDING-4] Ambiguous Free-List Rebuild Algorithm on Trap
- **Severity**: HIGH
- **Category**: Trap
- **Location**: `architecture_spec.md` §25.3
- **Finding**: For trap entry, the spec says to "rebuild free lists from committed/live ownership or use a defined reclamation walk. The implementation choice shall preserve the free-list invariants." This fails the strict implementable requirement as it leaves the exact recovery algorithm up to the designer.
- **Scenario**: An ECALL reaches the ROB head. The architectural RAT is restored. The RTL designer must implement free-list recovery but has no normative algorithm to follow, leading to potential discrepancies in recovery latency or free-list ordering.
- **Proposed Correction**: Mandate a specific algorithm. For example: "The free list shall be rebuilt by walking all physical registers and adding any register not currently present in the Integer or FP RRAT (excluding `p0`) to the respective free list."

### [FINDING-5] Unspecified State Transition for Trap during Branch Rollback
- **Severity**: HIGH
- **Category**: Trap
- **Location**: `architecture_spec.md` §20.4, `uop_spec.md` §28.5
- **Finding**: The specs state "Only one recovery state may be active" and "A ROB-head precise trap has priority over a younger branch misprediction." However, it does not explain how the FSM transitions if a trap reaches the ROB head *while* the FSM is already in the `BRANCH_ROLLBACK` state (walking backwards).
- **Scenario**: Cycle 10: Branch mispredict detected; FSM enters `BRANCH_ROLLBACK`. Cycle 12: Before rollback finishes, the older instruction at ROB head (e.g., an ECALL or faulting load) triggers a precise trap. 
- **Proposed Correction**: Explicitly define: "If a precise trap occurs at the ROB head while the core is in `BRANCH_ROLLBACK`, the core shall immediately abort the entry-by-entry rollback, transition to `TRAP_RECOVERY`, flush the entire ROB, and restore state directly from the RRAT."

### [FINDING-6] Missing Tag Definition for LSQ Age Comparison
- **Severity**: MEDIUM
- **Category**: Wraparound
- **Location**: `architecture_spec.md` §22.4
- **Finding**: The spec dictates forwarding from the "youngest matching older store". However, it does not specify whether this age comparison is performed using the `sq_tag` generation counter or the `rob_tag` sequence logic.
- **Scenario**: A load at ROB index 5 needs to check older stores in the SQ at SQ indices 1 and 2. To determine which is the "youngest matching older store", the logic must compare their ages.
- **Proposed Correction**: Add to §22.4: "Age comparisons to determine 'older' stores and the 'youngest' matching store shall use the stores' and load's associated `rob_tag` using standard ROB sequence arithmetic, not the SQ indices or tags."

### [FINDING-7] Missing Cross-Domain PRF Read Port for FSW Data
- **Severity**: CRITICAL
- **Category**: LSU
- **Location**: `architecture_spec.md` §6, §17.1, §22.2; `uop_spec.md` §18
- **Finding**: FSW instructions are dispatched to the Integer Issue Queue and execute in the `LSU_AGU`. FSW requires reading an integer register for the address base and an FP register for the store data. However, the Integer PRF has 2 read ports and the FP PRF has 3 read ports (theoretically dedicated to the FP Issue Queue for FMA). There is no defined datapath or read port arbitration allowing the Integer Issue Queue to read the FP PRF.
- **Scenario**: FSW is selected for issue from the Integer IQ. Simultaneously, an FMA is selected from the FP IQ. The FMA requires 3 FP PRF read ports. The FSW requires 1 FP PRF read port. The FP PRF only has 3 read ports. The select policy does not check for cross-domain read port availability.
- **Proposed Correction**: Either (1) Add a 4th FP PRF read port dedicated to the Integer IQ for FSW, or (2) Implement cross-queue read-port arbitration, or (3) Decouple FSW store data reading such that it happens in the SQ rather than at Issue.

### [FINDING-8] Missing Cross-Domain Wakeup Snooping Rule
- **Severity**: CRITICAL
- **Category**: Wakeup
- **Location**: `uop_spec.md` §17.2, `architecture_spec.md` §24.1
- **Finding**: The issue queues are partitioned by domain (Integer vs. FP), but instructions like `FCVT.S.W` (Int-to-FP) sit in the FP Issue Queue while depending on an Integer source register. The spec does not explicitly mandate that an Issue Queue must snoop the writeback/wakeup bus of the opposite domain.
- **Scenario**: `FCVT.S.W` is waiting in the FP Issue Queue for `src0` (an integer physical register). The Integer ALU completes the producer instruction and broadcasts the integer physical tag on the Integer writeback bus. If the FP Issue Queue only snoops the FP writeback bus, `FCVT.S.W` will deadlock.
- **Proposed Correction**: Add to `uop_spec.md` §17.2: "Issue queues must monitor all writeback broadcast buses, including cross-domain writeback buses, to wake up sources belonging to those domains (e.g., FP IQ must snoop the Integer writeback bus for `SRC_INT_REG` operands)."

### [FINDING-9] Missing Datapath Description for Dynamic Rounding Mode in Decode
- **Severity**: MEDIUM
- **Category**: FP
- **Location**: `architecture_spec.md` §8, §23.3; `uop_spec.md` §24
- **Finding**: Decode is required to generate a `UOP_EXCEPTION` if dynamic rounding is requested while the architectural `frm` CSR contains a reserved value. This means Decode/Rename must have a direct combinatorial read path from the `frm` CSR. While functionally sound (due to serialization of CSR writes), this datapath is omitted from the top-level block diagram and not explicitly stated.
- **Scenario**: `FADD.S` with `rm=111` (dynamic) is decoded. The `frm` CSR currently holds `101` (reserved). Decode must immediately flag this as an illegal instruction.
- **Proposed Correction**: Update the Block Diagram in `architecture_spec.md` §8 to show an `frm` state path from the CSR block back to the Decode/Rename stages, and explicitly document this asynchronous read path.
