# ROB-space-constrained LSU arbitration

Authorized 2026-11-16 (UTC): follow the recommended ROB-space guard from the completed
[read-only diagnosis](../../docs/LSU_ARBITRATION_DIAGNOSIS.md). Parent is bounded
arbitration v1 at `3715907`; the original AP5B baseline remains frozen.

One independent policy change: allow an eligible load ahead of the first marked
head store only when registered ROB occupancy is at most 14/16. An offered load
under backpressure retains ownership even if the ROB later fills. Uncontended
loads remain eligible at every occupancy; existing marked-store priority applies
after the initial opportunity. Do not add an age, FP-only or PC-specific filter.

Approved RTL scope is exactly LSU, ROB and core wiring. ROB exports a Boolean
comparison of its existing registered count; the new signal does not depend on
current allocation/retirement ready and adds no state. Only the LSU's first-head
branch uses this signal. Existing store forwarding, unresolved/partial hazards,
precise faults, flush and single external outstanding remain unchanged.

The manifest freezes every RTL/simulation/physical input and the unchanged
10,000 ps clock/memory comparison. The simulator, ELF bytes, numerical tolerances,
two-family scoring and ≥1.20× / ≤1.10× planning targets remain unchanged.

Gates 1–3 pass at clean source `3c87e71`; all five pipeline stages exited 0.
At nominal 100 MHz, Embench/FP32 are **1.076286× / 1.109010×** original baseline,
or **1.002181× / 1.019078×** A+B. PID gains are retained, FFT now improves over
A+B, and statemate's regression shrinks from 7.325% to 0.526%. Three cases regress
against arbitration v1, so the full denominator and tradeoffs remain visible in
[the completed review](../../docs/LSU_ROB_ROOM_REVIEW.md). Physical gate 4 is unmeasured.

Validation gates:

1. Actual arbitration-v1 parent and candidate each run 344 pin cases: original
   140 plus 192 pressure competition cases (14/15/16 entries, INT/FP, response
   handoff, tag wrap, backpressure and load/store errors), actual ROB allocation/
   retirement threshold sweep, simultaneous events, changing pressure during
   offered requests, uncontended loads and recovery. Six actual-RTL negative
   controls cover parent mislabeling, both off-by-one thresholds, revoking a held
   load at high pressure, unbounded priority and missing request hold.
2. Clean normal/assert builds; 18 directed, 18 Spike, 48 interface, 58 memory and
   3,400 finite FMA checks. Four contract and nine provenance controls also pass.
3. All frozen 27 workloads, 3,629 numerical values, identical per-PC retired work,
   complete exclusive cycle accounting. Compare separately to original baseline,
   A+B and arbitration v1. The earlier observer coverage is not a prediction.
4. A retained candidate needs fresh common-flow ASAP7 TT/SS/FF global-route PPA.
   Current A+B critical-path reports cannot establish this candidate's timing.

`scripts/check_lsu_rob_room.py` runs in pinned `rv32ooo-fp:p1` (Verilator 4.038,
GCC 11.4). Its adapter instantiates a real ROB driven only by allocation and
completion pins; it observes occupancy without forcing internal state. The
retained safety fixture runs with an empty independent ROB. The parent adapter
omits the new LSU input but uses the same ROB occupancy source for fair pin tests.
Legacy standalone LSU adapters tie the new permission high to retain their prior
test scope; full-core tests use actual ROB wiring.

After unit checks and a clean commit, run:

```sh
python3 experiments/lsu-rob-room-v1/run_functional.py
```

Fresh `build/experiments/lsu-rob-room-v1` outputs preserve every actual exit status,
input identity and failure. The first unit-generation attempt rejected an adapter
filename/module-name mismatch; the checker now copies it under the matching name
without disabling lint. The original failed receipt and checker are retained.

After environment resume, the independently recomputed complete comparison is
byte-identical; unit inputs/binaries/logs/traces and all pipeline receipts also
revalidate. [Public evidence](../../docs/evidence/2026-11-18/lsu-rob-room-functional/README.md)
retains those checks. Neither the baseline nor the planning goals are promoted or changed.

Physical gate 4 uses an isolated `ROOM` variant under the accepted A+B flow:
fresh native core synthesis, the exact proved shared FPU, TT global-route
construction, hold40 repair, uniform ready guard, and independent TT/SS/FF STA.
Mapping/construction periods remain 5,500/14,000 ps; acceptance uses the same
100 ps grid, complete setup/hold/electrical checks, and original area denominator.
The initial sweep is 9,000–10,000 ps, extended if it does not bracket a pass/fail
boundary. A physical limit below 10,000 ps requires separate workload timing
with memory service still fixed at 10,000 ps before any system-speed claim.

The adapters retain the prior native commands and reviewers. Only candidate
identities, paths, and durable-storage preparation differ: `rv32-room-native`
starts with a direct host bind, without a private tmpfs or extra mount privileges.
Unused directories are removed only from its disposable writable layer, with
all 204 pinned physical files checked before and after. Each completed physical
stage gets a verified durable checkpoint and the observed process exit is saved.

After lowering, preparing the pinned runtime, and committing these adapters:

1. Run `run_synthesis.py --output /workspace/build/experiments/lsu-rob-room-v1/mapping-v1 --variants ROOM` inside the native runtime.
2. Run `link_shared.py --core build/experiments/lsu-rob-room-v1/mapping-v1/ROOM --output build/experiments/lsu-rob-room-v1/shared-linked-v1` on the host.
3. Run `prepare_physical_contracts.py`, then commit the resulting contracts.
4. Run `complete_physical.py` on the host; inspect every exit and independent review.

Until those stages complete, this procedure is preparation, not measured PPA.
