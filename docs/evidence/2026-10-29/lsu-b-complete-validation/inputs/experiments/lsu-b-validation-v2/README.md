# B completion validation, shared FPU flow v2

The user requested complete B-line verification on 2026-10-28. This experiment
retains the B RTL and frozen 27-workload contract, completes the FPU sequential
proof from reset, and requalifies physical timing with a same-flow baseline/B
comparison. It does not promote a new baseline or combine A+B.

`contract.json` pins the common mapped FPU, each linked core, the original source
identities and acceptance limits. The first construction trial uses TT 45% slew
repair and a 100 ps TT hold repair target on both cores. Independent TT/SS/FF
setup and hold limits remain zero; clock uncertainty, I/O budgets, load, fixed
10 ns memory, clock grid and area/performance targets remain unchanged. Any
further construction trial must be separately versioned and compared consistently.

The FPU proof relates the original 156 state bits to the mapped 100 FFs using
only registered output connectivity and the actual Liberty FF polarity. It
proves both reset-to-zero obligations, then all next-state/visible-output
functions for arbitrary inputs and related state. There are no internal
arithmetic cutpoints or assumptions about opcodes, handshake or operands. The
initial condition is one synchronous reset rising edge. This establishes
implementation equivalence; IEEE-754 specification conformance remains a
separate question. Positive and intentionally corrupted cases are retained.

Physical work uses the common mapped netlists at commit 30158fe, fresh native
ORFS placement/CTS/global routing, a fresh TT repair and full-route recheck,
then independent corner processes with the existing strict timing reviewer.
The original v1 failure remains in its archive. System-time scores require a
qualified measured period and the complete frozen workload set. Verification
completion and achieving both 1.20x performance goals are reported separately.

The [completed review](../../docs/LSU_B_COMPLETE_VALIDATION.md) and
[raw evidence](../../docs/evidence/2026-10-29/lsu-b-complete-validation/README.md)
record final admission. Both complete workload points pass; the performance
targets remain unmet. The construction history below preserves failed attempts.

The first 100 ps B ECO was stopped after more than 9,130 hold-repair iterations
and 25,958 inserted buffers: its TT WNS had plateaued around 47 ps. The native
failure, stop reason and completed incoming GRT are preserved. The pre-ECO
100 MHz diagnosis passes setup at all three corners, but has FF hold -0.724 ps
and SS slew violations, so it is rejected for admission.

`contract-hold40.json` is the separate follow-up construction policy. It reuses
each core's identical completed GRT under the original contract, then applies a
fresh TT 45% slew / 40 ps hold ECO and complete global-route recheck. The 40 ps
target is below the observed nonconvergent plateau; it is not an acceptance
threshold. `repair.py` bounds an ECO attempt at 3,600 seconds and preserves a
failed run instead of silently accepting it. Both cores use the same policy.
`analyze_physical.py` collects independent native corners, and `review.py` binds
FPU proof, actual passing clock trials, original functional/build provenance,
all 27 workloads, 3,629 outputs and per-PC work to the explicit new flow.

Both hold40 constructions completed. B passed all corners down to an actual
9,600 ps point (9,500 ps SS setup fails), but the same-flow baseline has FF hold
-1.237 ps on `dmem_req_ready` to LSU in-flight address storage. Its failure is
retained; the original zero-hold threshold is not waived.

`contract-ready-guard.json` defines the next common construction step: one
`BUFx2_ASAP7_75t_R` on `dmem_req_ready` in each already completed hold40 database.
The native Liberty model proves this cell is the wire function Y=A. The guard
script verifies every original cell master, pin and boundary terminal after
legalization and full rerouting; removing that one buffer recovers the original
connectivity. Both variants use the identical insertion rule and unchanged
independent TT/SS/FF acceptance. `ready_guard.py` preserves its predecessor and
records the native execution, complete connectivity check and final database.

The first guard attempts (`physical-*-v3`) stopped at the strict cell-name check:
OpenROAD treats `-buffer_name` as a prefix and adds a numeric suffix. A native
in-memory probe confirmed the requested BUFx2 cell was inserted. The revised
check identifies the unique added instance immediately, validates its master
and prefix, then audits all original cells/pins after routing. The failed logs
and exact commit `33d566a` source are retained; fresh attempts use `*-v4` outputs.

## Final result and replay

Final `*-v4` guards pass both variants, with zero routing/placement/antenna
violations. The actual adjacent timing boundary is baseline 9,400 ps fail /
9,500 ps pass, B 9,500 ps fail / 9,600 ps pass; 10,000 ps passes both.
`review_guard.py` admits the complete contract at common 100 MHz and the B
fastest tested 104.17 MHz point, while reporting both performance goals unmet.
It checks original native graph-audit counts against the raw log, in addition
to full stage identities, route/timing proof and workload provenance.

Restore archived build inputs into a scratch checkout using the archive copy
inventories; retained B v1 functional and FPU mapping dependencies are linked
from the final archive. Losslessly compacted formal JSON can be read by the
reviewer as `.json.gz`; native Yosys replay requires decompression first.
Recreate the two baseline/B `physical-*-v2/grt` aliases with relative targets
`../physical-baseline-v1/grt` and `../physical-B-v1/grt`, respectively. The archived
`normalize_route_alias.py` was used only to convert already-existing absolute
native aliases; it is not a fresh-restore command.
Do not rerun an archived worker in place: use fresh outputs and record commands
and any path adaptation, preserving the original attempt and hashes.

With the restored dependencies, the host-only final reviews are:

```sh
python3 experiments/lsu-b-validation-v2/review_guard.py \
  --b-analysis build/experiments/lsu-b-validation-v2/physical-B-v4/guard/independent-boundary-v1 \
  --baseline-analysis build/experiments/lsu-b-validation-v2/physical-baseline-v4/guard/independent-boundary-v1 \
  --measurement build/experiments/lsu-b-validation-v2/measurement-10000ps-v1 \
  --build-summary build/experiments/lsu-b-v1/build-clean-v1/summary.json \
  --qualification-summary build/experiments/lsu-b-v1/qualification-clean-v1/summary.json \
  --comparison common-clock --output build/B-common-replay.json
python3 experiments/lsu-b-validation-v2/review_guard.py \
  --b-analysis build/experiments/lsu-b-validation-v2/physical-B-v4/guard/independent-boundary-v1 \
  --baseline-analysis build/experiments/lsu-b-validation-v2/physical-baseline-v4/guard/independent-boundary-v1 \
  --measurement build/experiments/lsu-b-validation-v2/measurement-9600ps-v1 \
  --build-summary build/experiments/lsu-b-v1/build-clean-v1/summary.json \
  --qualification-summary build/experiments/lsu-b-v1/qualification-clean-v1/summary.json \
  --comparison fastest --output build/B-fastest-replay.json
python3 experiments/lsu-b-validation-v2/check_guard_admission.py \
  --analysis build/experiments/lsu-b-validation-v2/physical-B-v4/guard/independent-boundary-v1 \
  --output build/B-admission-controls-replay
```

Native proof replay uses the archived `prepare.ys`, `models/*.json`, lowering
scripts and ABC commands in `fpu-state-relation-v1/proof-summary.json`.
The independent frontend replay, actual RTL mutants, definedness and physical
binding reviews are separate retained evidence. Native physical replay uses
`physical.py`, `repair.py`, `ready_guard.py` and `analyze_guard.py` in that order,
with each versioned contract and clean input checkpoint; the original 100 ps
attempt intentionally fails. Successful stage sources must remain unchanged
because job input hashes bind them. Record a new version for construction changes.
The pinned image and 204 tool/platform files remain the tool boundary. Global
routing uses nominal wire RC; detailed-route/OCV/ISA/IEEE-754 signoff is outside
this completion contract.
