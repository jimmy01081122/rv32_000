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

Work is in progress. Results and the final scope/coverage review will be linked
here when the native checks and evidence review finish.

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
