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
